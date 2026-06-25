import json
from collections import defaultdict

master_file = 'data/master_train_v1.jsonl'
test_file = 'data/splits/test_final_original_v1.jsonl'

combos = defaultdict(lambda: {'count': 0, 'label': '', 'attack_type': '', 'scenario': '', 'mechanism': '', 'languages': defaultdict(int)})

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            obj = json.loads(line)
            # Chỉ tính original samples
            if obj.get('combo_id', '').startswith('AUG_'):
                continue
                
            bc = obj.get('combo_id')
            combos[bc]['count'] += 1
            combos[bc]['label'] = obj.get('label', '')
            combos[bc]['attack_type'] = obj.get('attack_type', '')
            combos[bc]['scenario'] = obj.get('scenario', '')
            combos[bc]['mechanism'] = obj.get('mechanism', '')
            combos[bc]['languages'][obj.get('language', 'unknown')] += 1

process_file(master_file)
process_file(test_file)

print(f"{'Combo':<6} | {'Count':<5} | {'Label':<13} | {'Attack Type':<16} | {'Scenario':<30} | {'Mechanism':<25} | {'Languages'}")
print("-" * 130)

for bc in sorted(combos.keys()):
    c = combos[bc]
    langs = ', '.join([f"{k}:{v}" for k, v in c['languages'].items()])
    print(f"{bc:<6} | {c['count']:<5} | {c['label']:<13} | {c['attack_type']:<16} | {c['scenario']:<30} | {c['mechanism']:<25} | {langs}")
