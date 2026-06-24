import json
from pathlib import Path
import tiktoken
import statistics

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = BASE_DIR / "data" / "generated_audited.jsonl"

def main():
    # Sử dụng cl100k_base (chuẩn của GPT-3.5/4) để ước tính token
    enc = tiktoken.get_encoding("cl100k_base")
    
    samples = []
    with INPUT_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))

    if not samples:
        print("Không có dữ liệu.")
        return

    total_tokens_all = 0
    record_tokens = []
    
    print(f"Đang tính toán token cho {len(samples)} bản ghi...\n")

    for idx, sample in enumerate(samples):
        sample_tokens = 0
        
        for msg in sample.get("messages", []):
            content = msg.get("content", "")
            tokens = len(enc.encode(content))
            sample_tokens += tokens
            
        record_tokens.append(sample_tokens)
        total_tokens_all += sample_tokens

    avg_tokens = total_tokens_all / len(samples)
    min_tokens = min(record_tokens)
    max_tokens = max(record_tokens)
    median_tokens = statistics.median(record_tokens)

    print("=" * 40)
    print("📊 THỐNG KÊ TOKEN (ƯỚC TÍNH BẰNG TIKTOKEN)")
    print("=" * 40)
    print(f"Tổng số bản ghi : {len(samples)}")
    print(f"Tổng số token   : {total_tokens_all:,}")
    print("-" * 40)
    print(f"Token trung bình/bản ghi : {avg_tokens:.1f}")
    print(f"Trung vị (Median)        : {median_tokens}")
    print(f"Token ngắn nhất          : {min_tokens}")
    print(f"Token dài nhất           : {max_tokens}")
    print("=" * 40)

    # Hiển thị độ dài theo phân khúc
    bins = {
        "< 100": 0,
        "100 - 300": 0,
        "300 - 600": 0,
        "> 600": 0
    }
    
    for t in record_tokens:
        if t < 100:
            bins["< 100"] += 1
        elif t <= 300:
            bins["100 - 300"] += 1
        elif t <= 600:
            bins["300 - 600"] += 1
        else:
            bins["> 600"] += 1
            
    print("\nPhân bố chiều dài:")
    for k, v in bins.items():
        print(f"  {k:<10} token : {v:>4} bản ghi ({v/len(samples)*100:.1f}%)")

if __name__ == "__main__":
    main()
