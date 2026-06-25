import json
from collections import defaultdict

master_file = 'data/master_train_v1.jsonl'
test_file = 'data/splits/test_final_original_v1.jsonl'

# Mapping: (attack_type, scenario, mechanism) -> list of combo_ids
coverage = defaultdict(set)

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            obj = json.loads(line)
            # Chỉ tính original samples
            if obj.get('combo_id', '').startswith('AUG_'):
                continue
            
            bc = obj.get('combo_id')
            at = obj.get('attack_type', '')
            sc = obj.get('scenario', '')
            mc = obj.get('mechanism', '')
            
            coverage[(at, sc, mc)].add(bc)

process_file(master_file)
process_file(test_file)

print(f"{'Attack Type':<20} | {'Scenario':<32} | {'Mechanism':<26} | {'Combos'}")
print("-" * 105)

# Sort by attack_type, then scenario, then mechanism
for key in sorted(coverage.keys()):
    at, sc, mc = key
    combos_str = ', '.join(sorted(list(coverage[key])))
    print(f"{at:<20} | {sc:<32} | {mc:<26} | {combos_str}")
