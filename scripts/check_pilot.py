import json

counts = {"TEST_BN01": 0, "TEST_PI01": 0, "TEST_JB02": 0}

with open('data/generated_pilot_test.jsonl', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        c_id = data['combo_id']
        if c_id in counts and counts[c_id] < 3:
            print(f"[{c_id}] ({data['language']})")
            print(f"User Final: {data['messages'][-1]['content']}")
            print("-" * 40)
            counts[c_id] += 1
