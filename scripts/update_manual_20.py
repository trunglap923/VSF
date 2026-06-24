import json

update_ids = {
    'PI16_000031', 'PI15_000014', 'JB09_000018', 'JB02_000011',
    'CT05_000080', 'PI14_000004', 'CT07_000026', 'JB11_000068',
    'JB11_000052', 'CT05_000073', 'PI13_000011', 'JB13_000086',
    'CT07_000076'
}

input_file = 'data/original_judged_v3_3_resolved.jsonl'
samples = []

with open(input_file, 'r', encoding='utf-8') as f:
    for line in f:
        if not line.strip(): continue
        s = json.loads(line)
        if s.get('job_id') in update_ids:
            s['evaluation']['final_label_v3'] = 'controversial'
            print(f"Updated {s.get('job_id')} to controversial")
        samples.append(s)

with open(input_file, 'w', encoding='utf-8') as f:
    for s in samples:
        f.write(json.dumps(s, ensure_ascii=False) + '\n')

print('Update complete.')
