import json
import random

path = 'data/generated_aug_judged_v1.jsonl'
rows = []
with open(path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            rows.append(json.loads(line))

bn11_c = [r for r in rows if 'BN11_C' in r['combo_id'] and r.get('evaluation', {}).get('clean_status') == 'keep']
jb09 = [r for r in rows if 'JB09' in r['combo_id'] and r.get('evaluation', {}).get('clean_status') in ['keep', 'relabel_candidate']]
pi12 = [r for r in rows if 'PI12' in r['combo_id'] and r.get('evaluation', {}).get('clean_status') == 'keep']
pi14 = [r for r in rows if 'PI14' in r['combo_id'] and r.get('evaluation', {}).get('clean_status') in ['keep', 'manual_review']]
pi02 = [r for r in rows if 'PI02' in r['combo_id'] and r.get('evaluation', {}).get('clean_status') in ['manual_review', 'relabel_candidate']]

random.seed(42)
bn11_c = random.sample(bn11_c, min(5, len(bn11_c)))
jb09 = random.sample(jb09, min(5, len(jb09)))
pi12 = random.sample(pi12, min(5, len(pi12)))
pi14 = random.sample(pi14, min(5, len(pi14)))
pi02 = random.sample(pi02, min(5, len(pi02)))

selected = [('BN11_C (Keep)', bn11_c), ('JB09 (Keep/Relabel)', jb09), ('PI12 (Keep)', pi12), ('PI14 (Keep/Manual)', pi14), ('PI02 (Manual/Relabel)', pi02)]

with open('data/pilot_v3_manual_review.md', 'w', encoding='utf-8') as out:
    out.write('# Pilot V3 Manual Review Samples\n\n')
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

print('Exported V3 manual review samples to data/pilot_v3_manual_review.md')
