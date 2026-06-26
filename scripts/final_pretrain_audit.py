import json
import os
from collections import Counter
from pathlib import Path

def load_jsonl(path):
    data = []
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                data.append(json.loads(line))
    return data

def get_stats(samples):
    labels = Counter(s.get('label', 'unknown') for s in samples)
    combos = Counter(s.get('combo_id', 'unknown') for s in samples)
    sample_ids = {s['sample_id'] for s in samples}
    return labels, combos, sample_ids

# 1. Load files
train_v3 = load_jsonl('data/splits/ft_train_grouped_v3.jsonl')
val_v3 = load_jsonl('data/splits/ft_val_grouped_v3.jsonl')
router_v3 = load_jsonl('data/splits/router_pool_v3.jsonl')
judged_wave1 = load_jsonl('data/judged_wave1.jsonl')
gen_wave1 = load_jsonl('data/generated_wave1.jsonl')

train_labels, train_combos, train_ids = get_stats(train_v3)
val_labels, val_combos, val_ids = get_stats(val_v3)
router_labels, router_combos, router_ids = get_stats(router_v3)

# 2. Router Contamination Check
router_train_intersect = router_ids.intersection(train_ids)
router_val_intersect = router_ids.intersection(val_ids)

# 3. Judge Acceptance Rate
gen_labels = Counter(s.get('label', 'unknown') for s in gen_wave1)
judged_kept = [s for s in judged_wave1 if s.get('evaluation', {}).get('clean_status', 'keep') == 'keep']
kept_labels = Counter(s.get('label', 'unknown') for s in judged_kept)

# 4. Generate Report
report = []
report.append("# Pre-Train Audit Report V3\n")

report.append("## 1. Label Distribution")
report.append("### ft_train_grouped_v3")
for k, v in sorted(train_labels.items()): report.append(f"- {k}: {v}")
report.append("### ft_val_grouped_v3")
for k, v in sorted(val_labels.items()): report.append(f"- {k}: {v}")
report.append("### router_pool_v3")
for k, v in sorted(router_labels.items()): report.append(f"- {k}: {v}")

report.append("\n## 2. Router Contamination Check")
report.append(f"- router ∩ train: {len(router_train_intersect)} samples")
report.append(f"- router ∩ val  : {len(router_val_intersect)} samples")

report.append("\n## 3. Judge Acceptance Rate (Wave 1)")
report.append(f"- Total Generated: {len(gen_wave1)}")
report.append(f"- Total Kept: {len(judged_kept)} ({(len(judged_kept)/len(gen_wave1)*100):.1f}%)")
for k in sorted(gen_labels.keys()):
    gen_cnt = gen_labels[k]
    kept_cnt = kept_labels[k]
    rate = (kept_cnt/gen_cnt*100) if gen_cnt > 0 else 0
    report.append(f"- {k}: kept {kept_cnt}/{gen_cnt} ({rate:.1f}%)")

report.append("\n## 4. Combo Distribution (Top 10 Largest Combos across Train+Val+Router)")
all_combos = Counter()
for c in [train_combos, val_combos, router_combos]:
    all_combos.update(c)

for k, v in all_combos.most_common(10):
    report.append(f"- {k}: {v}")
report.append("\n(Total unique combos: {len(all_combos)})")

report_text = "\n".join(report)

with open('data/splits/reports/pretrain_audit_v3.md', 'w', encoding='utf-8') as f:
    f.write(report_text)

print(report_text)
