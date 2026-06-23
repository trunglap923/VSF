import json
import re
import argparse
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent.parent
AUG_FILE = BASE_DIR / "data" / "pipeline_merged" / "augmentation_train_selected_v1_refined.jsonl"
TEST_FILE = BASE_DIR / "data" / "pipeline_merged" / "splits" / "test_final_original_v1.jsonl"

OUT_AUG_CLEAN = BASE_DIR / "data" / "pipeline_merged" / "augmentation_after_leakage_v1.jsonl"
REPORT_FILE = BASE_DIR / "data" / "pipeline_merged" / "reports" / "anti_leakage_report_v1.json"
DROPPED_FILE = BASE_DIR / "data" / "pipeline_merged" / "reports" / "anti_leakage_dropped_examples_v1.jsonl"

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    # Loại bỏ các ký tự đặc biệt, dấu câu, chỉ giữ lại chữ và số
    text = re.sub(r'[^\w\s]', '', text)
    # Loại bỏ khoảng trắng thừa
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_ngrams(text: str, n: int = 10) -> set:
    words = text.split()
    if len(words) < n:
        return {tuple(words)} if words else set()
    return set(tuple(words[i:i+n]) for i in range(len(words) - n + 1))

def main():
    if not AUG_FILE.exists():
        print(f"❌ Không tìm thấy {AUG_FILE}")
        return
    if not TEST_FILE.exists():
        print(f"❌ Không tìm thấy {TEST_FILE}")
        return
        
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Load Test
    test_exact_hashes = set()
    test_final_users = set()
    test_ngrams_all = set()
    
    test_count = 0
    with open(TEST_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            s = json.loads(line)
            test_count += 1
            msgs = s.get("messages", [])
            
            full_text = " ".join(m["content"] for m in msgs)
            norm_full = normalize_text(full_text)
            test_exact_hashes.add(norm_full)
            test_ngrams_all.update(get_ngrams(norm_full, n=10))
            
            if msgs and msgs[-1]["role"] == "user":
                final_user = normalize_text(msgs[-1]["content"])
                test_final_users.add(final_user)
                
    print(f"📥 Đã tải {test_count} mẫu từ Test Set.")
    
    # Check Augmentation
    aug_samples = []
    with open(AUG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                aug_samples.append(json.loads(line))
                
    print(f"📥 Đã tải {len(aug_samples)} mẫu từ Augmentation Set.")
    
    stats = {
        "augmentation_input": len(aug_samples),
        "dropped_by_exact": 0,
        "dropped_by_final_user": 0,
        "dropped_by_ngram": 0,
        "augmentation_after_leakage": 0,
        "label_distribution_before": Counter(),
        "label_distribution_after": Counter()
    }
    
    clean_aug = []
    dropped_samples = []
    
    for s in aug_samples:
        lbl = s.get("label")
        stats["label_distribution_before"][lbl] += 1
        
        msgs = s.get("messages", [])
        full_text = " ".join(m["content"] for m in msgs)
        norm_full = normalize_text(full_text)
        
        final_user = ""
        if msgs and msgs[-1]["role"] == "user":
            final_user = normalize_text(msgs[-1]["content"])
            
        # 1. Exact Match
        if norm_full in test_exact_hashes:
            stats["dropped_by_exact"] += 1
            continue
            
        # 2. Final User Exact Match (vì tập test thường là seed cho tấn công)
        if final_user and final_user in test_final_users:
            stats["dropped_by_final_user"] += 1
            continue
            
        # 3. N-gram overlap
        sample_ngrams = get_ngrams(norm_full, n=10)
        overlap = sample_ngrams.intersection(test_ngrams_all)
        if len(overlap) > 0:
            # Ngưỡng: Nếu trùng lặp >= 1 đoạn 10-gram thì drop
            stats["dropped_by_ngram"] += 1
            
            # Lưu lại mẫu bị drop do n-gram
            overlap_preview = [" ".join(gram) for gram in list(overlap)[:3]] # Lấy 3 đoạn mẫu làm preview
            dropped_samples.append({
                "sample_id": s.get("sample_id"),
                "combo_id": s.get("combo_id"),
                "label": lbl,
                "drop_reason": "ngram_overlap",
                "overlap_preview": overlap_preview,
                "messages": msgs
            })
            continue
            
        clean_aug.append(s)
        
    stats["augmentation_after_leakage"] = len(clean_aug)
    for s in clean_aug:
        stats["label_distribution_after"][s.get("label")] += 1
        
    # Export
    with open(OUT_AUG_CLEAN, 'w', encoding='utf-8') as f:
        for s in clean_aug:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
            
    with open(DROPPED_FILE, 'w', encoding='utf-8') as f:
        for ds in dropped_samples:
            f.write(json.dumps(ds, ensure_ascii=False) + "\n")
            
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=4, ensure_ascii=False)
        
    print(f"\n✅ Kiểm tra rò rỉ hoàn tất!")
    print(f"Báo cáo: {REPORT_FILE.name}")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    print("\nLƯU Ý: Quá trình Merge CHƯA ĐƯỢC THỰC HIỆN. Vui lòng kiểm tra báo cáo trước khi tiến hành Merge.")

if __name__ == "__main__":
    main()
