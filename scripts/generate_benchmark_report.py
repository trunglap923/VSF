import json
from collections import Counter

def generate_report(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = [json.loads(line) for line in f]
    
    total = len(data)
    
    labels = Counter(d.get('label', 'unknown') for d in data)
    attack_types = Counter(d.get('attack_type', 'unknown') for d in data)
    languages = Counter(d.get('language', 'unknown') for d in data)
    turns = Counter(d.get('n_messages', 0) for d in data)
    combos = Counter(d.get('combo_id', 'unknown') for d in data)
    
    report = f"# Benchmark v2 Coverage Report\n\n"
    report += f"**Total Samples:** {total}\n\n"
    
    report += "## 1. By Label\n"
    for k, v in sorted(labels.items()):
        report += f"- **{k}**: {v} ({v/total*100:.1f}%)\n"
        
    report += "\n## 2. By Attack Type\n"
    for k, v in sorted(attack_types.items()):
        report += f"- **{k}**: {v} ({v/total*100:.1f}%)\n"
        
    report += "\n## 3. By Language\n"
    for k, v in sorted(languages.items()):
        report += f"- **{k}**: {v} ({v/total*100:.1f}%)\n"
        
    report += "\n## 4. By Turns\n"
    for k, v in sorted(turns.items()):
        report += f"- **{k} turns**: {v} ({v/total*100:.1f}%)\n"
        
    report += "\n## 5. By Combo ID\n"
    for k, v in sorted(combos.items()):
        report += f"- **{k}**: {v} ({v/total*100:.1f}%)\n"
        
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
        
    print(f"Report generated successfully at {output_file}")

if __name__ == "__main__":
    generate_report(
        "data/splits/test_final_original_v3.jsonl",
        "data/splits/benchmark_v3_report.md"
    )
