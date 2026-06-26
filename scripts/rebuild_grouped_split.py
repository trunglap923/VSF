"""
rebuild_grouped_split.py
─────────────────────────────────────────
Rebuild ft_train / ft_val bằng grouped split theo base_combo,
đảm bảo KHÔNG có combo nào xuất hiện ở cả train lẫn val.

Nguyên tắc:
- Mỗi base_combo chỉ được ở train HOẶC val, không cả hai.
- Stratify combo groups theo primary_label để val cân bằng nhãn.
- Router pool vẫn lấy 20% từ train sau khi split (optional).
- Không đụng test_final_original_v1.jsonl.

Output:
  data/splits/ft_train_grouped_v2.jsonl
  data/splits/ft_val_grouped_v2.jsonl
  data/splits/reports/grouped_split_report_v2.json
"""

import json
import random
from pathlib import Path
from collections import Counter, defaultdict

BASE_DIR    = Path(__file__).resolve().parent.parent
MASTER_FILE = BASE_DIR / "data" / "master_train_v3.jsonl"
ROUTER_FILE = BASE_DIR / "data" / "splits" / "router_pool_v3.jsonl"
OUT_DIR     = BASE_DIR / "data" / "splits"
REPORT_DIR  = OUT_DIR / "reports"

OUT_TRAIN   = OUT_DIR / "ft_train_grouped_v3.jsonl"
OUT_VAL     = OUT_DIR / "ft_val_grouped_v3.jsonl"
OUT_REPORT  = REPORT_DIR / "grouped_split_report_v3.json"

RANDOM_SEED   = 42
VAL_RATIO     = 0.125   # ~12.5% samples → val

# ─── helpers ──────────────────────────────────────────────
def get_base_combo(s: dict) -> str:
    return s.get("base_combo_id") or s.get("combo_id", "unknown")

def primary_label(samples: list[dict]) -> str:
    cnt = Counter(s.get("label", "unknown") for s in samples)
    return cnt.most_common(1)[0][0]

def write_jsonl(path: Path, rows: list[dict]):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def get_stats(rows: list[dict]) -> dict:
    return {
        "total":  len(rows),
        "labels": dict(Counter(r.get("label") for r in rows)),
        "combos": len(set(r.get("combo_id") for r in rows)),
        "base_combos": len(set(get_base_combo(r) for r in rows)),
    }

# ─── load ─────────────────────────────────────────────────
print(f"📥 Loading {ROUTER_FILE.name}...")
router_ids = set()
if ROUTER_FILE.exists():
    with open(ROUTER_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                s = json.loads(line)
                router_ids.add(s["sample_id"])
print(f"   {len(router_ids)} router samples loaded.")

print(f"📥 Loading {MASTER_FILE.name}...")
samples: list[dict] = []
with open(MASTER_FILE, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            s = json.loads(line)
            if s["sample_id"] not in router_ids:
                samples.append(s)
print(f"   {len(samples)} samples loaded (excluding router pool).")

# ─── group by base_combo ───────────────────────────────────
groups: dict[str, list[dict]] = defaultdict(list)
for s in samples:
    groups[get_base_combo(s)].append(s)

# ─── determine val target size ────────────────────────────
total_samples = len(samples)
val_target    = int(total_samples * VAL_RATIO)
print(f"\n🎯 Target val samples : ~{val_target}  ({VAL_RATIO*100:.1f}%)")
print(f"   Total base_combos  : {len(groups)}")

# ─── stratified combo-level split ─────────────────────────
# Sort combos by primary label for reproducibility, then shuffle within strata
random.seed(RANDOM_SEED)

label_buckets: dict[str, list[str]] = defaultdict(list)
for bc, slist in groups.items():
    label_buckets[primary_label(slist)].append(bc)

# Shuffle each bucket
for lbl in label_buckets:
    random.shuffle(label_buckets[lbl])

val_combos:   set[str] = set()
train_combos: set[str] = set()

current_val_size = 0

# Round-robin across label buckets to fill val quota
bucket_keys = sorted(label_buckets.keys())
bucket_iters = {k: iter(label_buckets[k]) for k in bucket_keys}

exhausted = set()
while current_val_size < val_target and len(exhausted) < len(bucket_keys):
    for lbl in bucket_keys:
        if lbl in exhausted:
            continue
        try:
            bc = next(bucket_iters[lbl])
        except StopIteration:
            exhausted.add(lbl)
            continue

        group_size = len(groups[bc])
        # Accept if still below target or within 5% overflow
        if current_val_size + group_size <= val_target * 1.15:
            val_combos.add(bc)
            current_val_size += group_size
        else:
            # Too big for val → put in train
            train_combos.add(bc)

# Remaining combos all go to train
for bc in groups:
    if bc not in val_combos:
        train_combos.add(bc)

# ─── build splits ─────────────────────────────────────────
train_samples = [s for bc in train_combos for s in groups[bc]]
val_samples   = [s for bc in val_combos   for s in groups[bc]]

# Shuffle within each split
random.shuffle(train_samples)
random.shuffle(val_samples)

# ─── verify: zero base_combo overlap ──────────────────────
overlap = train_combos & val_combos
assert len(overlap) == 0, f"❌ base_combo overlap found: {overlap}"
print(f"\n✅ base_combo overlap: 0  (clean grouped split)")

# ─── verify: sample-level no overlap ──────────────────────
train_ids = {s["sample_id"] for s in train_samples}
val_ids   = {s["sample_id"] for s in val_samples}
assert len(train_ids & val_ids) == 0, "❌ sample_id overlap between train and val!"
print(f"✅ sample_id overlap  : 0")

# ─── write output ─────────────────────────────────────────
REPORT_DIR.mkdir(parents=True, exist_ok=True)
write_jsonl(OUT_TRAIN, train_samples)
write_jsonl(OUT_VAL,   val_samples)

# ─── report ───────────────────────────────────────────────
report = {
    "random_seed": RANDOM_SEED,
    "val_ratio_target": VAL_RATIO,
    "split_strategy": "grouped_by_base_combo",
    "total_input_samples": total_samples,
    "total_base_combos": len(groups),
    "train_base_combos": sorted(train_combos),
    "val_base_combos": sorted(val_combos),
    "base_combo_overlap": 0,
    "ft_train_grouped_v3": get_stats(train_samples),
    "ft_val_grouped_v3":   get_stats(val_samples),
}

with open(OUT_REPORT, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

# ─── summary ──────────────────────────────────────────────
print(f"\n📊 Split Summary:")
print(f"   Train: {len(train_samples)} samples | {len(train_combos)} base_combos")
print(f"   Val  : {len(val_samples)} samples | {len(val_combos)} base_combos")
print(f"   Val% : {len(val_samples)/total_samples*100:.1f}%")
print(f"\n   Val label dist  : {report['ft_val_grouped_v3']['labels']}")
print(f"   Train label dist: {report['ft_train_grouped_v3']['labels']}")
print(f"\n   Val base_combos : {sorted(val_combos)}")
print(f"\n✅ Output: {OUT_TRAIN.name}, {OUT_VAL.name}")
print(f"📄 Report: {OUT_REPORT.name}")
