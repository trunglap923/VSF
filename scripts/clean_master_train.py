import json
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MASTER_FILE = BASE_DIR / "data" / "pipeline_merged" / "master_train_v1.jsonl"
TEST_FILE = BASE_DIR / "data" / "pipeline_merged" / "splits" / "test_final_original_v1.jsonl"

def main():
    if not MASTER_FILE.exists() or not TEST_FILE.exists():
        print("❌ Thiếu file Master hoặc Test.")
        return
        
    test_ids = set()
    with open(TEST_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            test_ids.add(json.loads(line).get("sample_id"))
            
    print(f"📥 Đã tải {len(test_ids)} ID từ Test Set.")
    
    clean_samples = []
    dropped_leakage = 0
    fixed_labels = 0
    
    labels_dist = Counter()
    
    with open(MASTER_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            s = json.loads(line)
            
            # 1. Remove leakage
            if s.get("sample_id") in test_ids:
                dropped_leakage += 1
                continue
                
            # 2. Sync label with final_label
            top_label = s.get("label", "").lower()
            eval_data = s.get("evaluation", {})
            final_label = eval_data.get("final_label_v3") or eval_data.get("final_label") or top_label
            final_label = final_label.lower()
            
            if top_label != final_label:
                fixed_labels += 1
                s["label"] = final_label
                
            labels_dist[final_label] += 1
            clean_samples.append(s)
            
    with open(MASTER_FILE, 'w', encoding='utf-8') as f:
        for s in clean_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
            
    print("✅ Đã làm sạch Master Train.")
    print(f"🗑️ Đã xóa do dính Test Set: {dropped_leakage}")
    print(f"🔧 Đã chuẩn hóa Label: {fixed_labels}")
    print(f"📈 Tổng số dòng sau clean: {len(clean_samples)}")
    print("Phân phối nhãn cuối cùng:")
    for k, v in labels_dist.items():
        print(f"  - {k}: {v}")

if __name__ == "__main__":
    main()
