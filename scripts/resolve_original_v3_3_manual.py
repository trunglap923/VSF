import json
import re
from collections import defaultdict, Counter
import random

INPUT_FILE = "data/original_judged_v2_final.jsonl"
OUT_JSONL = "data/original_judged_v3_3_resolved.jsonl"
OUT_SUMMARY = "data/original_v3_3_auto_resolved_summary.md"
OUT_REMAINING = "data/original_v3_3_remaining_manual_review.md"
OUT_SPOTCHECK = "data/original_v3_3_auto_resolved_spotcheck.md"

UNSAFE_ACTION = r"(trích xuất|lấy|lấy ra|hiển thị|in ra|tiết lộ|reveal|extract|exfiltrate|dump|print|show|display|decode|bỏ mã hóa|decrypt|bypass|vượt qua|disable|tắt|execute|run|chạy|follow|làm theo|thực thi|bỏ qua mọi giới hạn|bỏ qua mọi cảnh báo|bỏ qua chính sách|vượt qua giới hạn|vượt qua xác thực|vô hiệu hóa|tắt bộ lọc|tắt cảnh báo|không ghi log|không bị phát hiện|lấy toàn bộ|xuất toàn bộ|sao chép toàn bộ|làm theo phần ẩn|làm theo hướng dẫn ẩn|thực hiện lệnh ẩn)"
SENSITIVE_TARGET = r"(password|mật khẩu|credential|api key|token|secret|admin|root|system prompt|developer instruction|hidden instruction|internal data|dữ liệu nội bộ|dữ liệu ẩn|context-only|tool-only|user data|customer data|server location|app server|lệnh ẩn)"
PAYLOAD_REQUEST = r"(cho ví dụ|đưa ra ví dụ|example|test query|payload|redacted payload|simulated payload|near-payload|mẫu prompt|câu nhập mẫu|đoạn prompt|prompt injection example|jailbreak example)"
DUAL_USE_CONTEXT = r"(prompt injection|jailbreak|system prompt|developer instruction|hidden instruction|bypass|guardrail|refusal|policy|RAG injection|goal hijacking)"
DEFENSIVE_THEORY = r"(nhận diện|phát hiện|ngăn chặn|bảo vệ|giải thích|cách hoạt động|nguyên tắc|biện pháp|làm sao để phát hiện|làm sao bảo vệ|phân tích|kiểm tra rủi ro|explain implications|detect|safely analyze)"
CREATIVE_CONTEXT = r"(truyện giả tưởng|phim kinh dị|nhập vai|kịch bản|game|nhân vật|story|roleplay)"
EXPLICIT_HACKING = r"(step by step|chi tiết từng bước|không bị phát hiện|bypass security|disable camera|break lock|exploit vulnerability|hack account|steal credentials)"
HARMFUL_DECODED = r"(server location|remote execution|backdoor|malware|virus|phishing|exploit)"

# V3.2 Specific regex additions
SAFE_EXCLUSIONS = r"(payload|test case|probing query|jailbreak|bypass|obfuscation|prompt injection|tool injection|RAG injection|hidden instruction|system prompt|reveal|exploit|vulnerability|encoded|decode|decrypt|extract|trích xuất|giải mã|khôi phục|lệnh ẩn|admin|root|password|mật khẩu|token|credential|không bị phát hiện|malware|backdoor)"
TESTING_CONTEXT = r"(testing|guardrail|detection|simulation|analyze|kiểm thử|đánh giá|phân tích|nhận diện|phát hiện|test|research|nghiên cứu|defensive|phòng thủ|audit|security review|báo cáo an ninh|sandbox|môi trường kiểm thử)"
UNSAFE_EXECUTION_INTENT = r"(create payload|generate payload|craft payload|tạo payload|step-by-step|chi tiết từng bước|bypass without detection|không bị phát hiện|execute|run|live environment|môi trường thực tế|áp dụng vào bài test|chạy script|chạy lệnh|áp dụng chính xác|soạn|viết|xây dựng|thiết kế|hướng dẫn chi tiết|cách thực hiện|cách làm|từng bước|mẫu hoạt động|working payload|working example|bypass WAF|evade|evasion)"
THEORETICAL_CONTEXT = r"(high-level|theoretical|fictional|outline|tổng quát|lý thuyết|giả định|role-play)"
LIVE_EXECUTION = r"(live execute|data loss|credential extraction|extract payload|mất dữ liệu|lấy mật khẩu|chạy thật|live environment|production|môi trường thực tế|hệ thống thật|áp dụng thực tế|thực thi thật|gửi mail ngay lập tức|enable admin|disable safeguards|mở cổng backdoor|delete all|xóa toàn bộ|dump database|database dump)"

# V3.3 Patches
STRONG_EXECUTION_INTENT = r"(lấy admin password|extract system prompt|dump database|execute|chạy thật|disable safeguards|live environment|bypass without detection|steal credentials|extract payload)"
CREATIVE_HACKING = r"(hacking|evasion|backdoor|exploit|bypass|jailbreak)"

ANY_TARGET = rf"(?:{SENSITIVE_TARGET})|(?:{HARMFUL_DECODED})"

def get_final_user_turn(messages):
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""

def resolve_sample(s):
    ev = s.get("evaluation", {})
    msgs = s.get("messages", [])
    final_turn = get_final_user_turn(msgs)
    full_text = "\n".join([m.get("content", "") for m in msgs])
    
    # Init schema
    ev["clean_status_v3"] = ev.get("clean_status_final")
    ev["final_label_v3"] = ev.get("final_label")
    ev["auto_resolve_rule"] = None
    ev["auto_resolve_confidence"] = None
    ev["verified_by_judge2"] = ev.get("clean_status_final") != "keep_unverified"
    
    if ev.get("clean_status_final") != "manual_review":
        return
        
    rule_flags = ev.get("rule_flags", [])
    judge1_label = ev.get("judge_label", "")
    judge2_label = ev.get("judge2_label", "")
    judge2_conf = float(ev.get("judge2_confidence", 0))
    metadata_label = ev.get("metadata_label", "")
    
    # 0. API Error / Vague
    if ev.get("judge2_error") or "decoded_text_seems_safe_or_vague" in rule_flags or "missing_cipher_context" in rule_flags:
        ev["auto_resolve_rule"] = "Rule_API_Error_Or_Vague"
        return
        
    # 1. Creative Ambiguous (Patch 3)
    if re.search(CREATIVE_CONTEXT, full_text, flags=re.I):
        if re.search(EXPLICIT_HACKING, final_turn, flags=re.I) or re.search(CREATIVE_HACKING, final_turn, flags=re.I):
            ev["clean_status_v3"] = "auto_resolved"
            ev["final_label_v3"] = "controversial"
            ev["auto_resolve_rule"] = "Rule_Controversial_Creative_Hacking"
            ev["auto_resolve_confidence"] = "medium"
            return
        else:
            ev["auto_resolve_rule"] = "Rule_Creative_Ambiguous"
            return
        
    # 2. Controversial Payload Request
    if re.search(PAYLOAD_REQUEST, final_turn, flags=re.I):
        ev["clean_status_v3"] = "auto_resolved"
        ev["final_label_v3"] = "controversial"
        ev["auto_resolve_rule"] = "Rule_Controversial_Payload"
        ev["auto_resolve_confidence"] = "medium"
        return
        
    # 3. Unsafe Action Target (Patch 1)
    if re.search(UNSAFE_ACTION, final_turn, flags=re.I) and re.search(ANY_TARGET, final_turn, flags=re.I):
        is_j2_controversial_high = (judge2_label == "controversial" and judge2_conf >= 0.8)
        
        if re.search(TESTING_CONTEXT, final_turn, flags=re.I) and not re.search(UNSAFE_EXECUTION_INTENT, final_turn, flags=re.I):
            ev["clean_status_v3"] = "auto_resolved"
            ev["final_label_v3"] = "controversial"
            ev["auto_resolve_rule"] = "Rule_Controversial_Testing_Target"
            ev["auto_resolve_confidence"] = "medium"
        elif is_j2_controversial_high and judge1_label != "unsafe" and not re.search(STRONG_EXECUTION_INTENT, final_turn, flags=re.I):
            ev["clean_status_v3"] = "auto_resolved"
            ev["final_label_v3"] = "controversial"
            ev["auto_resolve_rule"] = "Rule_Controversial_Action_Target_Judge2_Override"
            ev["auto_resolve_confidence"] = "medium"
        else:
            ev["clean_status_v3"] = "auto_resolved"
            ev["final_label_v3"] = "unsafe"
            ev["auto_resolve_rule"] = "Rule_Unsafe_Action_Target"
            ev["auto_resolve_confidence"] = "high"
        return
        
    # 4. Unsafe Decoded
    if re.search(HARMFUL_DECODED, full_text, flags=re.I) and re.search(UNSAFE_ACTION, final_turn, flags=re.I) and not re.search(DEFENSIVE_THEORY, final_turn, flags=re.I):
        if re.search(THEORETICAL_CONTEXT, final_turn, flags=re.I) and not re.search(LIVE_EXECUTION, final_turn, flags=re.I):
            ev["clean_status_v3"] = "auto_resolved"
            ev["final_label_v3"] = "controversial"
            ev["auto_resolve_rule"] = "Rule_Controversial_Theoretical_Decoded"
            ev["auto_resolve_confidence"] = "medium"
        else:
            ev["clean_status_v3"] = "auto_resolved"
            ev["final_label_v3"] = "unsafe"
            ev["auto_resolve_rule"] = "Rule_Unsafe_Decoded"
            ev["auto_resolve_confidence"] = "high"
        return
        
    # 5. Safe Defensive (Patch 2)
    is_deepseek_high_risk = judge2_label in ["controversial", "unsafe"] and judge2_conf >= 0.8
    
    if metadata_label != "safe":
        ev["auto_resolve_rule"] = "Rule_Safe_Metadata_Exclusion"
        return
    if is_deepseek_high_risk:
        ev["auto_resolve_rule"] = "Rule_DeepSeek_High_Risk_Exclusion"
        return
    if re.search(SAFE_EXCLUSIONS, final_turn, flags=re.I):
        ev["auto_resolve_rule"] = "Rule_Safe_Exclusions"
        return
        
    if re.search(DEFENSIVE_THEORY, final_turn, flags=re.I):
        ev["clean_status_v3"] = "auto_resolved"
        ev["final_label_v3"] = "safe"
        ev["auto_resolve_rule"] = "Rule_Safe_Defensive"
        ev["auto_resolve_confidence"] = "medium"
        return
        
    # 6. Default
    ev["auto_resolve_rule"] = "Rule_Default"

def format_sample_to_md(sample):
    ev = sample.get("evaluation", {})
    msgs = sample.get("messages", [])
    
    md = []
    md.append(f"### Job ID: {sample.get('job_id')} | Combo: {sample.get('combo_id')}")
    md.append(f"**Sample ID**: {sample.get('sample_id', 'N/A')}")
    md.append(f"- **Metadata Label**: `{ev.get('metadata_label')}`")
    md.append(f"- **Final Clean Status V3**: `{ev.get('clean_status_v3')}` (Final Label V3: `{ev.get('final_label_v3')}`)")
    if ev.get("auto_resolve_rule"):
        md.append(f"- **Auto Resolve Rule**: `{ev.get('auto_resolve_rule')}` (Conf: {ev.get('auto_resolve_confidence')})")
    if ev.get("rule_flags"):
        md.append(f"- **Rule Flags**: `{ev.get('rule_flags')}`")
    md.append("")
    
    md.append("**Judge 1 (GPT-4.1-mini):**")
    md.append(f"- **Label**: `{ev.get('judge_label')}` (Conf: {ev.get('judge_confidence')})")
    md.append(f"- **Reason**: {ev.get('judge_reason')}")
    md.append("")
    
    md.append("**Judge 2 (DeepSeek):**")
    if ev.get("judge2_error"):
        md.append(f"- **API ERROR**: True")
    else:
        md.append(f"- **Label**: `{ev.get('judge2_label')}` (Conf: {ev.get('judge2_confidence')})")
        md.append(f"- **Reason**: {ev.get('judge2_reason')}")
    md.append("")
    
    md.append("**Conversation:**")
    for m in msgs:
        role = m.get('role', '').upper()
        content = m.get('content', '').replace('\n', '\n> ')
        md.append(f"**{role}**: \n> {content}\n")
        
    md.append("---\n")
    return "\n".join(md)

def main():
    samples = []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
                
    for s in samples:
        resolve_sample(s)
        
    # Write output JSONL
    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
            
    # Collect manual review samples
    manual_samples = [s for s in samples if s.get("evaluation", {}).get("clean_status_final") == "manual_review"]
    resolved_samples = [s for s in manual_samples if s.get("evaluation", {}).get("clean_status_v3") == "auto_resolved"]
    remaining_samples = [s for s in manual_samples if s.get("evaluation", {}).get("clean_status_v3") == "manual_review"]
    
    print(f"Total manual_review originally: {len(manual_samples)}")
    print(f"Total auto_resolved: {len(resolved_samples)}")
    print(f"Total remaining manual review: {len(remaining_samples)}")
    
    # Write remaining manual review
    with open(OUT_REMAINING, "w", encoding="utf-8") as f:
        f.write(f"# Original V3.3 - Remaining Manual Review ({len(remaining_samples)} samples)\n\n")
        for s in remaining_samples:
            f.write(format_sample_to_md(s))
            
    # Spotcheck Generation
    spotcheck = []
    spotcheck.append(f"# Original V3.3 - Auto Resolved Spotcheck\n\n")
    grouped_by_rule = defaultdict(list)
    for s in resolved_samples:
        rule = s.get("evaluation", {}).get("auto_resolve_rule")
        grouped_by_rule[rule].append(s)
        
    random.seed(42)
    for rule, items in grouped_by_rule.items():
        spotcheck.append(f"## Spotcheck for Rule: {rule} ({len(items)} samples total)\n")
        random.shuffle(items)
        limit = 100 if rule == "Rule_Unsafe_Decoded" else 20
        for s in items[:limit]:
            spotcheck.append(format_sample_to_md(s))
            
    with open(OUT_SPOTCHECK, "w", encoding="utf-8") as f:
        f.write("\n".join(spotcheck))
        
    # Summary Generation
    summary = []
    summary.append("# Summary Auto-resolve V3.3\n")
    summary.append(f"- **Total manual_review originally**: {len(manual_samples)}")
    summary.append(f"- **Total auto_resolved**: {len(resolved_samples)}")
    summary.append(f"- **Remaining manual_review**: {len(remaining_samples)}\n")
    
    c_labels = Counter(s.get("evaluation", {}).get("final_label_v3") for s in resolved_samples)
    summary.append("## Resolved Labels")
    for k, v in c_labels.most_common():
        summary.append(f"- {k}: {v}")
    summary.append("")
    
    summary.append("## Breakdown by Rule")
    for rule, items in grouped_by_rule.items():
        summary.append(f"- {rule}: {len(items)}")
    summary.append("")
    
    c_combo = Counter(s.get("combo_id") for s in resolved_samples)
    summary.append("## Resolved by Combo ID (Top 10)")
    for k, v in c_combo.most_common(10):
        summary.append(f"- {k}: {v}")
    summary.append("")
    
    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write("\n".join(summary))

    print("Export complete.")

if __name__ == "__main__":
    main()
