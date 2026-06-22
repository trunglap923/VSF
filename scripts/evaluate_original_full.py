import json
import pandas as pd
from collections import Counter
import random

path = 'data/original_judged_v1.jsonl'
out_path = 'data/original_full_manual_review.md'
rows = []
try:
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
except FileNotFoundError:
    print('File not found')
    exit()

print(f'Total rows: {len(rows)}')

if len(rows) > 0:
    evals = [r.get('evaluation', {}) for r in rows]
    
    clean_statuses = [e.get('clean_status', 'unknown') for e in evals]
    print('\n=== Clean Status Distribution ===')
    for k, v in Counter(clean_statuses).items():
        print(f'{k}: {v}')
        
    print('\n=== Metadata Label vs Judge Label ===')
    df = pd.DataFrame([{
        'metadata_label': e.get('metadata_label'),
        'judge_label': e.get('judge_label')
    } for e in evals])
    print(pd.crosstab(df['metadata_label'], df['judge_label']))
    
    print('\n=== Top Rule Flags ===')
    all_flags = []
    for e in evals:
        all_flags.extend(e.get('rule_flags', []))
    print(Counter(all_flags).most_common(5))

    candidates = [r for r in rows if r.get('evaluation', {}).get('clean_status') in ('relabel_candidate', 'manual_review')]
    random.shuffle(candidates)
    sampled = candidates[:100]

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('# Full Original - Manual Review Samples\n\n')
        for s in sampled:
            ev = s.get('evaluation', {})
            cid = s.get('combo_id')
            jid = s.get('job_id')
            ml = ev.get('metadata_label')
            jl = ev.get('judge_label')
            jc = ev.get('judge_confidence')
            cs = ev.get('clean_status')
            rf = ev.get('rule_flags')
            rs = ev.get('rule_source')
            ar = ev.get('applied_validation_rule')
            jr = ev.get('judge_reason')

            f.write(f'## Combo: {cid} | Job: {jid}\n')
            f.write(f'- Metadata Label: {ml}\n')
            f.write(f'- Judge Label: {jl} (Confidence: {jc})\n')
            f.write(f'- Status: {cs}\n')
            f.write(f'- Rule Flags: {rf}\n')
            f.write(f'- Rule Source: {rs} | Applied Rule: {ar}\n')
            f.write(f'- Reason: {jr}\n\n')
            f.write('### Conversation\n')
            for msg in s.get('messages', []):
                role = msg.get('role').upper()
                content = msg.get('content')
                f.write(f'**{role}**:\n{content}\n\n')
            f.write('---\n\n')

    print(f'\nExported {len(sampled)} samples to {out_path}')
