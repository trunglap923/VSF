import json
import os
import argparse
from pathlib import Path
from collections import defaultdict, Counter
import hashlib

BASE_DIR = Path(__file__).resolve().parent.parent.parent
INPUT_FILE = BASE_DIR / "data" / "pipeline_merged" / "augmentation_clean_all_v1.jsonl"
OUT_CLEAN_REFINED = BASE_DIR / "data" / "pipeline_merged" / "augmentation_clean_all_v1_refined.jsonl"
OUT_TRAIN_SEL_REFINED = BASE_DIR / "data" / "pipeline_merged" / "augmentation_train_selected_v1_refined.jsonl"
REPORT_FILE = BASE_DIR / "data" / "pipeline_merged" / "reports" / "augmentation_refine_report_v1.json"

OVERSAMPLED_UNSAFE_COMBOS = ["AUG_PI02_U01", "AUG_PI12_U01", "AUG_PI01_U01", "AUG_PI14_U01", "AUG_JB09_U01"]
MAX_PER_COMBO = 80

def get_hash(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def light_rule_validation(sample: dict) -> tuple[bool, str]:
    combo_id = sample.get("combo_id", "")
    msgs = sample.get("messages", [])
    if not msgs:
        return False, "no_messages"
    
    final_user_content = msgs[-1]["content"].lower()
    
    if combo_id in ["AUG_PI02_U01", "AUG_PI01_U01"]:
        # Phải có ý yêu cầu reveal/print/show/copy hidden/system/developer instruction
        leak_keywords = ["in ra", "hiển thị", "tiết lộ", "copy", "xem", "print", "show", "reveal", "display", "extract", "cung cấp", "trích xuất", "share"]
        target_keywords = ["system", "instruction", "prompt", "developer", "ẩn", "hệ thống", "cấu hình", "developer instruction", "system prompt", "nội bộ"]
        
        has_leak = any(k in final_user_content for k in leak_keywords)
        has_target = any(k in final_user_content for k in target_keywords)
        
        if not (has_leak or has_target):
            # Nới lỏng một chút, nếu thiếu hẳn thì báo lỗi
            return False, "missing_leak_request"
            
    elif combo_id == "AUG_PI14_U01":
        # Phải có văn bản trung gian dài + hidden instruction
        full_text = " ".join([m["content"].lower() for m in msgs])
        # Kiểm tra sự xuất hiện của các từ khóa gián tiếp hoặc email/văn bản
        if len(full_text) < 200:
            return False, "context_too_short_for_indirect"
            
    # Có thể thêm các rule nhẹ khác ở đây, nhưng tránh gắt quá drop nhầm
    return True, ""

def main():
    if not INPUT_FILE.exists():
        print(f"❌ File not found: {INPUT_FILE}")
        return
        
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    raw_samples = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                raw_samples.append(json.loads(line))
                
    print(f"📥 Loaded {len(raw_samples)} samples from clean_all.")
    
    stats = {
        "input_clean_all": len(raw_samples),
        "dropped_by_confidence": 0,
        "dropped_by_dedup": 0,
        "dropped_by_rule_validation": 0,
        "selected_after_cap": 0,
        "label_distribution_before": Counter(),
        "label_distribution_after": Counter(),
        "combo_distribution_after": Counter()
    }
    
    refined_samples = []
    seen_dedup = set()
    
    for s in raw_samples:
        label = s.get("label")
        stats["label_distribution_before"][label] += 1
        
        eval_data = s.get("evaluation", {})
        
        # 1. Confidence check
        conf = eval_data.get("confidence", 0)
        if conf < 0.7:
            stats["dropped_by_confidence"] += 1
            continue
            
        # 2. Light Rule Validation
        passed_rule, rule_fail_reason = light_rule_validation(s)
        if not passed_rule:
            stats["dropped_by_rule_validation"] += 1
            # print(f"Dropped by rule ({rule_fail_reason}): {s.get('sample_id')}")
            continue
            
        # 3. Dedup by (combo_id, label, normalized_final_user)
        msgs = s.get("messages", [])
        final_user = msgs[-1]["content"].lower().strip()
        combo_id = s.get("combo_id", "")
        
        dedup_key_str = f"{combo_id}_{label}_{final_user}"
        dedup_h = get_hash(dedup_key_str)
        
        if dedup_h in seen_dedup:
            stats["dropped_by_dedup"] += 1
            continue
        seen_dedup.add(dedup_h)
        
        # 4. PI12 Audit
        if "AUG_PI12" in combo_id and s.get("base_combo_id") != "PI12":
            # Nó đã bị map sang PI11 hoặc PI10
            s.setdefault("audit", {})
            s["audit"].update({
                "base_combo_id_original_inferred": "PI12",
                "base_combo_id_normalized": s.get("base_combo_id"),
                "taxonomy_mapping_reason": f"inferred from combo_id {combo_id} and message keyword scan"
            })
            
        refined_samples.append(s)

    # Export clean refined
    with open(OUT_CLEAN_REFINED, 'w', encoding='utf-8') as f:
        for s in refined_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
            
    # 5. Capping (Downsample Unsafe oversampled combos)
    final_selected = []
    combo_counts = Counter()
    
    # Sort by confidence descending to keep the best ones
    refined_samples.sort(key=lambda x: x.get("evaluation", {}).get("confidence", 0), reverse=True)
    
    for s in refined_samples:
        combo = s.get("combo_id")
        
        if combo in OVERSAMPLED_UNSAFE_COMBOS:
            if combo_counts[combo] < MAX_PER_COMBO:
                combo_counts[combo] += 1
                final_selected.append(s)
        else:
            final_selected.append(s)
            
    # Update stats
    stats["selected_after_cap"] = len(final_selected)
    for s in final_selected:
        lbl = s.get("label")
        stats["label_distribution_after"][lbl] += 1
        stats["combo_distribution_after"][s.get("combo_id")] += 1
        
    # Export train selected refined
    with open(OUT_TRAIN_SEL_REFINED, 'w', encoding='utf-8') as f:
        for s in final_selected:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
            
    # Export report
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=4, ensure_ascii=False)
        
    print(f"\n✅ Đã xuất 3 file Refined:")
    print(f"  1. {OUT_CLEAN_REFINED.name} ({len(refined_samples)} mẫu sau khi refine)")
    print(f"  2. {OUT_TRAIN_SEL_REFINED.name} ({len(final_selected)} mẫu sau khi cap)")
    print(f"  3. {REPORT_FILE.name}")
    print("\n📊 Báo cáo Refine:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
