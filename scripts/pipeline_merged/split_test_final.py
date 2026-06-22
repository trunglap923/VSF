import json
import os
import random
from collections import defaultdict, Counter

def main():
    input_file = "data/pipeline_merged/original_pool_master.jsonl"
    test_out = "data/pipeline_merged/splits/test_final_original_v1.jsonl"
    train_out = "data/pipeline_merged/original_pool_v1.jsonl"
    report_out = "data/pipeline_merged/reports/split_test_final_report.md"

    os.makedirs("data/pipeline_merged/splits", exist_ok=True)
    os.makedirs("data/pipeline_merged/reports", exist_ok=True)

    random.seed(42)

    samples = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            samples.append(json.loads(line))

    # Group by combo_id
    groups = defaultdict(list)
    for s in samples:
        combo_id = s.get("combo_id", "unknown")
        groups[combo_id].append(s)

    # Determine primary label for each group
    group_info = []
    for combo_id, group_samples in groups.items():
        label_counts = Counter(s.get("final_label", "unknown") for s in group_samples)
        primary_label = label_counts.most_common(1)[0][0]
        group_info.append({
            "combo_id": combo_id,
            "primary_label": primary_label,
            "size": len(group_samples),
            "samples": group_samples
        })

    # Global target per label (10%)
    global_label_counts = Counter(s.get("final_label", "unknown") for s in samples)
    test_target_counts = {k: int(v * 0.10) for k, v in global_label_counts.items()}

    test_samples = []
    train_samples = []

    # Shuffle groups to ensure randomness
    random.shuffle(group_info)

    current_test_counts = Counter()

    for g in group_info:
        primary_label = g["primary_label"]
        size = g["size"]
        
        # Check if we can add this group to test set without exceeding target significantly
        # Allow a slight overflow (+5) to accommodate group boundaries
        if current_test_counts[primary_label] + size <= test_target_counts[primary_label] + 5:
            test_samples.extend(g["samples"])
            for s in g["samples"]:
                current_test_counts[s.get("final_label", "unknown")] += 1
        else:
            train_samples.extend(g["samples"])

    # Write output
    with open(test_out, "w", encoding="utf-8") as f:
        for s in test_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
            
    with open(train_out, "w", encoding="utf-8") as f:
        for s in train_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    # Write report
    with open(report_out, "w", encoding="utf-8") as f:
        f.write("# Phase 1: Test Final Separation Report\n\n")
        f.write(f"**Total original samples:** {len(samples)}\n")
        f.write(f"**Test Final:** {len(test_samples)} ({(len(test_samples)/len(samples))*100:.1f}%)\n")
        f.write(f"**Train Pool:** {len(train_samples)} ({(len(train_samples)/len(samples))*100:.1f}%)\n\n")
        
        f.write("## Label Distribution Comparison\n")
        f.write("| Label | Global | Test Final | Train Pool |\n")
        f.write("| --- | --- | --- | --- |\n")
        
        test_counter = Counter(s.get("final_label", "unknown") for s in test_samples)
        train_counter = Counter(s.get("final_label", "unknown") for s in train_samples)
        
        for k in global_label_counts.keys():
            global_pct = (global_label_counts[k]/len(samples))*100
            test_pct = (test_counter[k]/len(test_samples))*100 if len(test_samples) > 0 else 0
            train_pct = (train_counter[k]/len(train_samples))*100 if len(train_samples) > 0 else 0
            
            f.write(f"| {k} | {global_label_counts[k]} ({global_pct:.1f}%) | {test_counter[k]} ({test_pct:.1f}%) | {train_counter[k]} ({train_pct:.1f}%) |\n")
            
        f.write("\n## Leakage Check\n")
        test_combos = set(s.get("combo_id") for s in test_samples)
        train_combos = set(s.get("combo_id") for s in train_samples)
        leakage = test_combos.intersection(train_combos)
        
        if len(leakage) == 0:
            f.write("✅ **SUCCESS**: No combo_id leakage detected between Test and Train pools.\n")
        else:
            f.write(f"❌ **FAILURE**: {len(leakage)} combo_ids found in both sets!\n")

    print(f"Split complete. Test: {len(test_samples)}, Train Pool: {len(train_samples)}")
    print(f"Output saved to {test_out} and {train_out}")
    print(f"Report saved to {report_out}")

if __name__ == "__main__":
    main()
