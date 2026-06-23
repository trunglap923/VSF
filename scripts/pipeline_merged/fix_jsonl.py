import json

def fix_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()

    lines = text.split('\n')
    valid_lines = []
    
    # It might be that the whole file is one line with literal "\n" inside
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Replace literal '\n' at the end of JSON objects
        # Wait, if they are joined by literally "\n", we can split by '\\n'
        sublines = line.split('\\n')
        for sub in sublines:
            sub = sub.strip()
            if not sub:
                continue
            try:
                json.loads(sub)
                valid_lines.append(sub)
            except Exception as e:
                print('Error on:', sub[:100], e)

    with open(path, 'w', encoding='utf-8') as f:
        for v in valid_lines:
            f.write(v + '\n')
    print(f'Fixed {path}. Wrote {len(valid_lines)} lines.')

fix_file('data/pipeline_merged/augmentation_clean_all_v1.jsonl')
