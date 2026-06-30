import json
import argparse
from datasets import load_dataset

def main():
    parser = argparse.ArgumentParser(description="Format deepset/prompt-injections for Qwen3Guard Benchmark")
    parser.add_argument("--output", type=str, default="data/splits/prompt_injections_benchmark.jsonl")
    parser.add_argument("--split", type=str, default="test", help="Dataset split (train or test)")
    args = parser.parse_args()

    print(f"Loading deepset/prompt-injections (split: {args.split})...")
    dataset = load_dataset("deepset/prompt-injections", split=args.split)
    
    formatted_data = []
    
    for idx, row in enumerate(dataset):
        prompt = row.get("text", "")
        if not prompt:
            continue
            
        # 1 = unsafe (prompt injection), 0 = safe (benign task)
        raw_label = row.get("label", 0)
        gold_label = "unsafe" if raw_label == 1 else "safe"
        
        record = {
            "sample_id": f"prompt_injections_{args.split}_{idx}",
            "combo_id": "prompt_injections",
            "source": "deepset/prompt-injections",
            "language": "en",  # Dataset này chủ yếu tiếng Anh
            "attack_type": "prompt_injection" if gold_label == "unsafe" else "benign",
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

    import os
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    print(f"Saving {len(formatted_data)} formatted samples to {args.output}...")
    with open(args.output, "w", encoding="utf-8") as f:
        for item in formatted_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print("Done! Bạn có thể dùng file này truyền vào tham số --test_file của file evaluate_qwen3guard_lora.py")

if __name__ == "__main__":
    main()
