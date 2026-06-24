import json
import re
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MASTER_FILE = BASE_DIR / "data" / "pipeline_merged" / "master_train_v1.jsonl"
TEST_FILE = BASE_DIR / "data" / "pipeline_merged" / "splits" / "test_final_original_v1.jsonl"

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_ngrams(text: str, n: int = 10) -> set:
    words = text.split()
    if len(words) < n:
        return {tuple(words)} if words else set()
    return set(tuple(words[i:i+n]) for i in range(len(words) - n + 1))

def main():
    print(f"🔍 BẮT ĐẦU SANITY CHECK TRÊN: {MASTER_FILE.name}")
    
    if not MASTER_FILE.exists():
        print("❌ File Master Train không tồn tại.")
        return
        
    # --- 1. Load Test Set để check overlap ---
    test_exact_hashes = set()
    test_ngrams_all = set()
    if TEST_FILE.exists():
        with open(TEST_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                s = json.loads(line)
                msgs = s.get("messages", [])
                full_text = " ".join(m["content"] for m in msgs)
                norm = normalize_text(full_text)
                test_exact_hashes.add(norm)
                test_ngrams_all.update(get_ngrams(norm, n=10))
    else:
        print("⚠️ Cảnh báo: Không tìm thấy Test Set để check leakage.")

    # --- 2. Các biến thống kê ---
    line_count = 0
    json_errors = 0
    invalid_last_message = 0
    invalid_labels = 0
    label_mismatch_count = 0
    
    test_overlap_exact = 0
    test_overlap_ngram = 0
    
    labels_dist = Counter()
    
    original_exacts = set()
    original_final_users = set()
    
    dup_aug_original_exact = 0
    dup_aug_original_fuser = 0

    valid_labels = {"safe", "unsafe", "controversial"}

    with open(MASTER_FILE, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip(): continue
            line_count += 1
            
            try:
                s = json.loads(line)
            except json.JSONDecodeError:
                json_errors += 1
                continue
                
            # --- Check label validity ---
            top_label = s.get("label", "").lower()
            if top_label not in valid_labels:
                invalid_labels += 1
            else:
                labels_dist[top_label] += 1
                
            # --- Check label consistency ---
            eval_data = s.get("evaluation", {})
            # Trong tập original có final_label_v3 hoặc final_label
            final_label = eval_data.get("final_label_v3") or eval_data.get("final_label") or top_label
            if final_label and final_label.lower() != top_label:
                label_mismatch_count += 1
                # In thử 1 mẫu để xem
                if label_mismatch_count == 1:
                    print(f"  [Mẫu mâu thuẫn label] ID: {s.get('sample_id')} | top_label: {top_label} | final_label: {final_label}")

            # --- Check messages ---
            msgs = s.get("messages", [])
            if not msgs or msgs[-1].get("role") != "user":
                invalid_last_message += 1
                
            # --- Check test leakage ---
            full_text = " ".join(m.get("content", "") for m in msgs)
            norm = normalize_text(full_text)
            
            if norm in test_exact_hashes:
                test_overlap_exact += 1
                
            sample_ngrams = get_ngrams(norm, n=10)
            if sample_ngrams.intersection(test_ngrams_all):
                test_overlap_ngram += 1
                
            # --- Check duplication within master ---
            # Xác định xem sample này đến từ đâu
            # Augmentation có "job_id" bắt đầu bằng AUG_
            is_aug = str(s.get("job_id", "")).startswith("AUG_")
            
            final_user_text = ""
            if msgs:
                final_user_text = normalize_text(msgs[-1].get("content", ""))
                
            if not is_aug:
                original_exacts.add(norm)
                original_final_users.add(final_user_text)
            else:
                # Nếu là Aug, check xem có trùng với Original đã quét qua không
                # Vì shuffle rồi nên đoạn này chỉ check với các Original đứng TƯỚC nó
                pass

    # Để check duplicate toàn diện giữa Aug và Original, ta cần lặp lại một lần nữa
    # hoặc dùng logic 2 list riêng. Để nhanh, ta load lại
    master_aug = []
    master_orig = []
    with open(MASTER_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            s = json.loads(line)
            if str(s.get("job_id", "")).startswith("AUG_"):
                master_aug.append(s)
            else:
                master_orig.append(s)
                
    orig_exacts = set(normalize_text(" ".join(m.get("content", "") for m in s.get("messages", []))) for s in master_orig)
    orig_fusers = set(normalize_text(s.get("messages", [])[-1].get("content", "")) for s in master_orig if s.get("messages"))
    
    for s in master_aug:
        msgs = s.get("messages", [])
        norm = normalize_text(" ".join(m.get("content", "") for m in msgs))
        fuser = normalize_text(msgs[-1].get("content", "")) if msgs else ""
        
        if norm in orig_exacts:
            dup_aug_original_exact += 1
        if fuser and fuser in orig_fusers:
            dup_aug_original_fuser += 1

    # --- IN REPORT ---
    print("\n" + "="*40)
    print("📊 BÁO CÁO SANITY CHECK")
    print("="*40)
    print(f"1. Tổng số dòng (JSONL): {line_count} (Kỳ vọng: 5264) {'✅' if line_count==5264 else '❌'}")
    print(f"2. Số lỗi parse JSON: {json_errors} {'✅' if json_errors==0 else '❌'}")
    print(f"3. Lỗi hội thoại (Last turn không phải user): {invalid_last_message} {'✅' if invalid_last_message==0 else '❌'}")
    print(f"4. Label nằm ngoài Safe/Unsafe/Controversial: {invalid_labels} {'✅' if invalid_labels==0 else '❌'}")
    print(f"5. Mâu thuẫn giữa label (top) và final_label: {label_mismatch_count} {'✅' if label_mismatch_count==0 else '❌'}")
    print(f"6. Leakage với Test Set (Exact): {test_overlap_exact} {'✅' if test_overlap_exact==0 else '❌'}")
    print(f"   Leakage với Test Set (N-gram): {test_overlap_ngram} {'✅' if test_overlap_ngram==0 else '❌'}")
    print(f"7. Duplicate Nội bộ (Aug vs Original):")
    print(f"   - Trùng lặp Exact match: {dup_aug_original_exact}")
    print(f"   - Trùng lặp Final User: {dup_aug_original_fuser}")
    print("8. Label Distribution cuối cùng (top-level label):")
    for k, v in labels_dist.items():
        print(f"   - {k}: {v}")
    print("="*40)

if __name__ == "__main__":
    main()
