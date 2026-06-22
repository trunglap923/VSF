import json
import random

path = 'data/generated_aug_judged_v1.jsonl'
rows = []
with open(path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            rows.append(json.loads(line))

bn11_c = [r for r in rows if 'BN11_C' in r['combo_id'] and r.get('evaluation', {}).get('clean_status') == 'relabel_candidate']
jb09 = [r for r in rows if 'JB09' in r['combo_id'] and r.get('evaluation', {}).get('clean_status') == 'relabel_candidate']
pi12 = [r for r in rows if 'PI12' in r['combo_id'] and r.get('evaluation', {}).get('clean_status') == 'manual_review']
pi14 = [r for r in rows if 'PI14' in r['combo_id'] and r.get('evaluation', {}).get('clean_status') in ['manual_review', 'relabel_candidate']]

random.seed(42)
bn11_c = random.sample(bn11_c, min(15, len(bn11_c)))
jb09 = random.sample(jb09, min(10, len(jb09)))
pi12 = random.sample(pi12, min(10, len(pi12)))
pi14 = random.sample(pi14, min(10, len(pi14)))

selected = [('BN11_C', bn11_c), ('JB09', jb09), ('PI12', pi12), ('PI14', pi14)]

with open('data/pilot_manual_review_samples.md', 'w', encoding='utf-8') as out:
    out.write('# Pilot Manual Review Samples\n\n')
    for group_name, samples in selected:
        out.write(f'## Group: {group_name} ({len(samples)} samples)\n\n')
        for idx, s in enumerate(samples):
            ev = s.get('evaluation', {})
            out.write(f'### Sample {idx+1}: {s["job_id"]}\n')
            out.write(f'- **Metadata Label**: {s["label"]}\n')
            out.write(f'- **Judge Label**: {ev.get("judge_label")} (Confidence: {ev.get("judge_confidence")})\n')
            out.write(f'- **Judge Reason**: {ev.get("judge_reason")}\n')
            out.write(f'- **Rule Flags**: {ev.get("rule_flags")}\n')
            out.write(f'- **Clean Status**: {ev.get("clean_status")}\n\n')
            out.write('**Conversation:**\n\n')
            for msg in s.get('messages', []):
                out.write(f'**{msg["role"].upper()}**: {msg["content"]}\n\n')
            out.write('---\n\n')

print('Exported manual review samples to data/pilot_manual_review_samples.md')
