import json
import argparse
from datasets import load_dataset
from collections import Counter

def main():
    parser = argparse.ArgumentParser(description="Format JailbreakBench/JBB-Behaviors for Qwen3Guard Benchmark")
    parser.add_argument("--output", type=str, default="data/splits/jbb_behaviors_benchmark.jsonl")
    args = parser.parse_args()

    # Load dataset config 'judge_comparison' which has the human vote columns
    print("Loading JailbreakBench/JBB-Behaviors (config: judge_comparison, split: test)...")
    dataset = load_dataset("JailbreakBench/JBB-Behaviors", "judge_comparison", split="test")
    
    formatted_data = []
    
    # We only care about human1, human2, human3, human_majority for the voting logic
    # The prompt is the `prompt` column
    # Goal can be used as combo_id or source info
    
    for idx, row in enumerate(dataset):
        prompt = row.get("prompt", "")
        if not prompt:
            continue
            
        # Lấy tất cả các nhãn đánh giá
        vote_columns = [
            'human1', 'human2', 'human3', 'human_majority', 
            'harmbench_cf', 'gpt4_cf', 'llamaguard2_cf', 'llama3_cf'
        ]
        
        votes = []
        eval_dict = {}
        for col in vote_columns:
            val = row.get(col, 0)
            votes.append(val)
            eval_dict[f"{col}_vote"] = val
            
        # Tính toán majority vote trên tất cả các cột
        vote_counts = Counter(votes)
        majority_vote = vote_counts.most_common(1)[0][0]
        
        gold_label = "unsafe" if majority_vote == 1 else "safe"
        
        eval_dict["final_label"] = gold_label
        eval_dict["final_label_v3"] = gold_label
        eval_dict["majority_vote_all"] = majority_vote
        
        record = {
            "sample_id": f"jbb_behaviors_test_{idx}",
            "combo_id": "jbb_behaviors",
            "source": "JBB-Behaviors",
            "language": "en",
            "attack_type": "jailbreak" if gold_label == "unsafe" else "benign",
            "label": gold_label,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "evaluation": eval_dict
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
