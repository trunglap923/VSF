import json
import argparse
from datasets import load_dataset

def main():
    parser = argparse.ArgumentParser(description="Format allenai/wildjailbreak for Qwen3Guard Benchmark")
    parser.add_argument("--output", type=str, default="data/splits/wildjailbreak_benchmark.jsonl")
    parser.add_argument("--config", type=str, default="eval", help="HuggingFace dataset config (train or eval)")
    parser.add_argument("--split", type=str, default="train", help="Dataset split (thường là train)")
    args = parser.parse_args()

    print(f"Loading allenai/wildjailbreak (config: {args.config}, split: {args.split})...")
    dataset = load_dataset("allenai/wildjailbreak", args.config, split=args.split)
    
    formatted_data = []
    
    for idx, row in enumerate(dataset):
        prompt = row.get("adversarial", "")
        if not prompt:
            continue
            
        raw_label = row.get("label", 0)
        gold_label = "unsafe" if raw_label == 1 else "safe"
        
        record = {
            "sample_id": f"wildjailbreak_{args.split}_{idx}",
            "combo_id": "wildjailbreak",
            "source": "wildjailbreak",
            "language": "en",
            "attack_type": "jailbreak" if gold_label == "unsafe" else "benign",
            "label": gold_label,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "evaluation": {
                "final_label": gold_label,
                "final_label_v3": gold_label
            }
        }
        formatted_data.append(record)

    # Lưu ra file JSONL
    print(f"Saving {len(formatted_data)} formatted samples to {args.output}...")
    import os
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    with open(args.output, "w", encoding="utf-8") as f:
        for item in formatted_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print("Done! Bạn có thể dùng file này truyền vào tham số --test_file của file evaluate_qwen3guard_lora.py")

if __name__ == "__main__":
    main()
