import json
import numpy as np
from pathlib import Path
from transformers import AutoTokenizer

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SFT_DIR = BASE_DIR / "data" / "training" / "qwen3guard"
IN_TRAIN = SFT_DIR / "train_sft_qwen3guard_v1.jsonl"
IN_VAL = SFT_DIR / "val_sft_qwen3guard_v1.jsonl"
REPORT_FILE = SFT_DIR / "token_length_report_v1.json"

MODEL_ID = "Qwen/Qwen2.5-0.5B"  # Dùng Base Model Tokenizer để đo đếm chính xác (Qwen3Guard base là Qwen2.5)
CUTOFF = 2048

def analyze_tokens(filepath, tokenizer):
    lengths = []
    over_cutoff = 0
    total = 0
    
    if not filepath.exists():
        return None
        
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            total += 1
            s = json.loads(line)
            
            # Format text hệt như lúc train sẽ format
            text = ""
            for msg in s.get("messages", []):
                text += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
            
            tokens = tokenizer.encode(text)
            l = len(tokens)
            lengths.append(l)
            
            if l > CUTOFF:
                over_cutoff += 1
                
    if not lengths:
        return None
        
    return {
        "total_samples": total,
        "mean_tokens": float(np.mean(lengths)),
        "median_tokens": float(np.median(lengths)),
        "p90_tokens": float(np.percentile(lengths, 90)),
        "p95_tokens": float(np.percentile(lengths, 95)),
        "p99_tokens": float(np.percentile(lengths, 99)),
        "max_tokens": int(np.max(lengths)),
        "samples_over_2048": over_cutoff,
        "over_cutoff_ratio": float(over_cutoff / total)
    }

def main():
    print("⏳ Đang tải Qwen Tokenizer...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    except Exception as e:
        print(f"Lỗi tải tokenizer {MODEL_ID}, thử tải Qwen/Qwen2-0.5B: {e}")
        tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2-0.5B")
        
    print(f"🚀 Phân tích Token Length cho Cutoff = {CUTOFF}...")
    
    train_stats = analyze_tokens(IN_TRAIN, tokenizer)
    print(f"Train Stats: {json.dumps(train_stats, indent=2)}")
    
    val_stats = analyze_tokens(IN_VAL, tokenizer)
    print(f"Val Stats: {json.dumps(val_stats, indent=2)}")
    
    report = {
        "model_tokenizer": MODEL_ID,
        "cutoff_threshold": CUTOFF,
        "train_sft": train_stats,
        "val_sft": val_stats
    }
    
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4, ensure_ascii=False)
        
    print(f"✅ Đã tạo báo cáo Token Length: {REPORT_FILE.name}")

if __name__ == "__main__":
    main()
