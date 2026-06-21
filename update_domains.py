import json

def main():
    path = 'data/combination_plan.json'
    with open(path, 'r', encoding='utf-8') as f:
        plan = json.load(f)

    extra_domains = ";email_processing;document_qa;customer_support_bot;hr_policy_qa;data_analysis;coding_assistant"
    
    target_combos = [f"BN{i:02d}" for i in range(3, 14)] + ["CT07", "CT08"]

    modified = 0
    for c in plan:
        if c['combo_id'] in target_combos:
            if "email_processing" not in c['domain_pool']:
                c['domain_pool'] += extra_domains
                modified += 1
                
    if modified > 0:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        print(f"Updated {modified} combos.")
    else:
        print("No combos needed updating.")

if __name__ == '__main__':
    main()
