import json
import argparse
import ast
from datasets import load_dataset

def main():
    parser = argparse.ArgumentParser(description="Format tom-gibbs/multi-turn_jailbreak_attack_datasets for Qwen3Guard Benchmark")
    parser.add_argument("--output", type=str, default="data/splits/multi_turn_jailbreak_benchmark.jsonl")
    parser.add_argument("--split", type=str, default="train", help="Dataset split")
    args = parser.parse_args()

    print(f"Loading tom-gibbs/multi-turn_jailbreak_attack_datasets (split: {args.split})...")
    dataset = load_dataset("tom-gibbs/multi-turn_jailbreak_attack_datasets", split=args.split)
    
    formatted_data = []
    
    for idx, row in enumerate(dataset):
        # Bộ dữ liệu này chuyên chứa các Multi-turn jailbreak attacks
        # Cột "Multi-turn conversation" lưu mảng các tin nhắn (dưới dạng chuỗi hoặc list dictionaries)
        convo_raw = row.get("Multi-turn conversation", "")
        
        if not convo_raw:
            continue
            
        try:
            # Nếu nó là chuỗi định dạng list, parse nó ra list of dicts
            if isinstance(convo_raw, str):
                messages = ast.literal_eval(convo_raw)
            else:
                messages = convo_raw
        except Exception as e:
            print(f"Bỏ qua dòng {idx} do lỗi parse tin nhắn: {e}")
            continue
            
        # Tất cả dữ liệu trong bộ này đều được xem là Jailbreak (unsafe)
        gold_label = "unsafe"
        
        record = {
            "sample_id": f"multi_turn_jailbreak_{args.split}_{idx}",
            "combo_id": "multi_turn_jailbreak",
            "source": "tom-gibbs/multi-turn_jailbreak_attack_datasets",
            "language": "en",  
            "attack_type": "jailbreak_multi_turn",
            "label": gold_label,
            "messages": messages,
            "evaluation": {
                "final_label": gold_label,
                "final_label_v3": gold_label,
                "goal": row.get("Goal", ""),
                "model": row.get("Model", "")
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
