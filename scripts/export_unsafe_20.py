import json

INPUT = 'data/original_judged_v3_3_resolved.jsonl'
unsafe_samples = []

with open(INPUT, 'r', encoding='utf-8') as f:
    for line in f:
        if not line.strip(): continue
        s = json.loads(line)
        ev = s.get('evaluation', {})
        if ev.get('clean_status_v3') == 'auto_resolved' and ev.get('final_label_v3') == 'unsafe':
            unsafe_samples.append(s)

with open('data/v3_3_unsafe_review_20.md', 'w', encoding='utf-8') as f:
    f.write(f'# 20 Unsafe Auto-Resolved Samples for Manual Review\n\n')
    for s in unsafe_samples:
        ev = s.get('evaluation', {})
        msgs = s.get('messages', [])
        f.write(f"### Job ID: {s.get('job_id')} | Combo: {s.get('combo_id')}\n")
        f.write(f"- **Sample ID**: {s.get('sample_id', 'N/A')}\n")
        f.write(f"- **Rule**: `{ev.get('auto_resolve_rule')}`\n")
        f.write(f"- **Judge 1**: `{ev.get('judge_label')}` | **Judge 2**: `{ev.get('judge2_label')}`\n\n")
        for m in msgs:
            role = m.get('role').upper()
            content = m.get('content').replace('\n', '\n> ')
            f.write(f"**{role}**: \n> {content}\n\n")
        f.write("---\n")

print(f"Exported {len(unsafe_samples)} samples to data/v3_3_unsafe_review_20.md")
