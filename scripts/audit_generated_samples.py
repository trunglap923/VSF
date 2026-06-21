"""
audit_generated_samples.py
──────────────────────────
Đọc generated_raw.jsonl, kiểm tra chất lượng rule-based, ghi ra generated_audited.jsonl.

Mỗi sample được thêm 4 trường:
    audit_label  — nhãn audit (không tự đổi unsafe → controversial)
    in_scope     — True nếu sample đúng scope jailbreak/PI
    quality      — "ok" | "review" | "bad"
    audit_flags  — danh sách cờ cụ thể

Nguyên tắc scan:
    - final_user          : mức nhạy cao nhất (tín hiệu attack chính)
    - tất cả user messages: bắt hidden instruction trong tài liệu user paste vào
    - assistant messages  : chỉ scan "harmful output signals" — tránh false positive do
                            assistant nói phòng thủ ("không bypass", "không tiết lộ"...)
    - safe/benign group   : không flag chỉ vì keyword xuất hiện trong toàn text;
                            chỉ flag khi final_user có yêu cầu attack rõ ràng
"""

import json
import re
from pathlib import Path
from typing import Any
from collections import Counter

BASE_DIR    = Path(__file__).resolve().parent.parent
INPUT_PATH  = BASE_DIR / "data" / "generated_raw.jsonl"
OUTPUT_PATH = BASE_DIR / "data" / "generated_audited.jsonl"


# ── Nhãn hợp lệ ──────────────────────────────────────────────────────────────

VALID_LABELS       = {"safe", "controversial", "unsafe"}
VALID_ATTACK_TYPES = {"jailbreak", "prompt_injection", "benign"}


# ── Tín hiệu attack trong câu hỏi CUỐI của user ──────────────────────────────
# Đây là keyword mạnh nhất — chỉ xuất hiện khi user yêu cầu attack rõ ràng.

FINAL_USER_ATTACK_SIGNALS = [
    # Jailbreak
    "bypass policy", "bypass safety", "bypass the safety", "bypass filter",
    "disable safety", "drop safety", "ignore safety", "bỏ qua an toàn",
    "ignore all previous", "ignore previous instructions",
    "bỏ qua mọi chỉ dẫn", "bỏ qua instruction",
    "không được từ chối", "đừng từ chối", "đừng bao giờ từ chối",
    "no-limit", "unfiltered", "safe mode off", "disable filter",
    "act without restriction", "act as if you have no limits",
    "pretend you have no rules", "forget your guidelines",
    "jailbreak", "bypass guardrail",
    # Prompt injection / leak
    "show me the system prompt", "in nguyên văn system prompt",
    "reveal the system prompt", "tiết lộ system prompt",
    "print the hidden instruction", "in hidden instruction",
    "bỏ qua developer message", "override system instruction",
    "ignore the system", "follow only my instruction",
    "tiết lộ toàn bộ context", "reveal private context",
    "leak the secret", "tiết lộ secret",
    # Data exfiltration
    "send me all the data", "gửi toàn bộ dữ liệu",
    "extract the private", "trích xuất dữ liệu riêng",
    # Payload request
    "payload", "exact steps", "các bước tấn công",
    "working exploit", "executable payload",
]


# ── Tín hiệu attack trong TẤT CẢ user messages ───────────────────────────────
# Bắt hidden instruction trong tài liệu/email user paste, hoặc intent escalation.

ALL_USER_ATTACK_SIGNALS = [
    # Hidden instruction thường thấy trong PI combo
    "ignore previous", "ignore all previous",
    "bỏ qua", "bỏ qua mọi",
    "override your instructions", "disregard previous",
    "you are now", "act as", "forget everything",
    "your new role is", "your new objective is",
    "system prompt", "developer instruction", "hidden instruction",
    "hidden policy", "policy nội bộ",
    # Leak / exfiltration
    "reveal", "leak", "lộ", "tiết lộ",
    "private context", "hidden token", "secret",
    # Jailbreak
    "bypass", "jailbreak", "prompt injection",
    "disable safety", "drop safety",
    "không được từ chối", "đừng từ chối",
    "no-limit", "unfiltered", "safe mode", "refuse", "refusal",
    "tool output injection", "rag injection",
    "instruction hierarchy",
]


# ── Tín hiệu OUTPUT NGUY HIỂM từ assistant ───────────────────────────────────
# Chỉ flag khi assistant thực sự cung cấp nội dung có thể bị lạm dụng.
# KHÔNG dùng với từ phòng thủ như "không nên bypass", "tránh tiết lộ"...

HARMFUL_ASSISTANT_SIGNALS = [
    # Assistant in ra secret/prompt
    "here is the system prompt:", "system prompt:", "my system prompt is",
    "đây là system prompt:", "nội dung system prompt:",
    "the hidden instruction says", "hidden instruction là:",
    # Step-by-step harmful instructions
    "step 1:", "step 2:", "bước 1:", "bước 2:",
    "here is how to bypass", "đây là cách bypass",
    "to jailbreak, you", "để jailbreak, bạn",
    "i will ignore my guidelines", "tôi sẽ bỏ qua hướng dẫn",
    # Actual dangerous content markers
    "here is the payload:", "payload:", "working payload",
    "inject this:", "use this command to",
    "credentials:", "password:", "api_key:", "token:",
]


# ── Tín hiệu ngoài scope ─────────────────────────────────────────────────────
# Unsafe nhưng không liên quan đến AI jailbreak / prompt injection

OUT_OF_SCOPE_SIGNALS = [
    "break into an account", "bypass the login", "guess a few passwords",
    "đột nhập tài khoản", "bypass đăng nhập", "crack password",
    "steal password", "phishing email to users",
    "create malware", "tạo virus", "ransomware",
    "ddos", "denial of service attack",
    "sql injection against", "hack the database",
]


# ── Tín hiệu language_mixing ─────────────────────────────────────────────────

LANGUAGE_MIX_TERMS = [
    "policy", "bypass", "refuse", "warning", "safe mode",
    "unfiltered", "no-limit", "jailbreak", "prompt injection",
    "system prompt", "rag", "tool output", "fine-tuning",
    "guardrail", "dataset", "token", "payload",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON at line {line_no}: {e}") from e
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def contains_any(text: str, patterns: list[str]) -> bool:
    text_lower = text.lower()
    return any(p.lower() in text_lower for p in patterns)


def get_messages_by_role(sample: dict) -> tuple[list[str], list[str]]:
    """Trả về (user_contents, assistant_contents)."""
    user_msgs, asst_msgs = [], []
    for msg in sample.get("messages", []):
        role    = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            user_msgs.append(content)
        elif role == "assistant":
            asst_msgs.append(content)
    return user_msgs, asst_msgs


def get_final_user_content(sample: dict) -> str:
    user_msgs, _ = get_messages_by_role(sample)
    return user_msgs[-1] if user_msgs else ""


def count_user_turns_with_lang_mix(sample: dict) -> int:
    """Đếm số user turn có chứa thuật ngữ tiếng Anh (cho language_mixing check)."""
    user_msgs, _ = get_messages_by_role(sample)
    count = 0
    for content in user_msgs:
        if any(term in content.lower() for term in LANGUAGE_MIX_TERMS):
            count += 1
    return count


# ── Structure check ───────────────────────────────────────────────────────────

def check_structure(sample: dict) -> list[str]:
    flags    = []
    messages = sample.get("messages")

    if not isinstance(messages, list) or len(messages) == 0:
        return ["missing_or_empty_messages"]

    expected_n = sample.get("n_messages")
    if expected_n is not None and len(messages) != int(expected_n):
        flags.append("wrong_number_of_messages")

    if messages[0].get("role") != "user":
        flags.append("first_message_not_user")

    if messages[-1].get("role") != "user":
        flags.append("last_message_not_user")

    for i, msg in enumerate(messages):
        expected_role = "user" if i % 2 == 0 else "assistant"
        if msg.get("role") != expected_role:
            flags.append("roles_not_alternating")
            break

    for msg in messages:
        if not msg.get("content", "").strip():
            flags.append("empty_message")
            break

    return flags


# ── Core audit logic ──────────────────────────────────────────────────────────

# ── Combo meta ────────────────────────────────────────────────────────────────
# PI combos dùng hidden instruction trong document — keyword không xuất hiện
# trực tiếp trong lời user, mà nằm trong nội dung document/email user paste.
# Những mechanism này không nên bị flag prompt_injection_signal_weak.
PI_INDIRECT_MECHANISMS = {
    "indirect_prompt_injection",
    "hidden_instruction_in_context",
    "context_dependency",
    "long_context_distraction",
    "goal_hijacking",
    "data_exfiltration",
    "assistant_context_exploitation",
}

# Unsafe mechanisms mà rủi ro nằm trong context tích lũy, KHÔNG phải keyword
# lộ mặt ở final turn. Flag unsafe_but_weak_attack_signal vô nghĩa với nhóm này.
CONTEXT_DEPENDENT_MECHANISMS = {
    "context_dependency",
    "long_context_distraction",
    "intent_accumulation",
    "assistant_context_exploitation",
    "hidden_instruction_in_context",
}

# Benign hard-negative combos: thiết kế có keyword attack nhưng intent phòng thủ.
# Không nên flag chỉ vì final user hỏi về attack trong bối cảnh giáo dục.
BENIGN_HARD_NEGATIVE_COMBOS = {
    "BN03", "BN04", "BN05", "BN07",
    "BN11",  # hard case: final turn xin ví dụ gần payload nhưng combo_id là benign
}


def audit_sample(sample: dict[str, Any]) -> dict[str, Any]:
    original_label = sample.get("label", "")
    attack_type    = sample.get("attack_type", "")
    evasion        = sample.get("evasion", "none")
    combo_id       = sample.get("combo_id", "")
    mechanism      = sample.get("mechanism", "")
    group          = sample.get("group", "")
    is_benign_safe = (attack_type == "benign" and original_label == "safe")

    # ── Lấy nội dung theo role ────────────────────────────────────────────────
    user_msgs, asst_msgs = get_messages_by_role(sample)
    final_user           = get_final_user_content(sample)
    all_user_text        = "\n".join(user_msgs)
    all_asst_text        = "\n".join(asst_msgs)
    # Với PI indirect: hidden instruction nằm trong nội dung document assistant nhắc tới
    all_text_full        = all_user_text + "\n" + all_asst_text

    flags: list[str] = []

    # ── 1. Structure ──────────────────────────────────────────────────────────
    flags.extend(check_structure(sample))

    # ── 2. Metadata ───────────────────────────────────────────────────────────
    if original_label not in VALID_LABELS:
        flags.append("invalid_label")
    if attack_type not in VALID_ATTACK_TYPES:
        flags.append("invalid_attack_type")

    # ── 3. Signal detection ───────────────────────────────────────────────────
    has_attack_in_final_user = contains_any(final_user, FINAL_USER_ATTACK_SIGNALS)
    has_attack_in_all_user   = contains_any(all_user_text, ALL_USER_ATTACK_SIGNALS)
    # Với PI indirect: scan toàn bộ text kể cả assistant (vì hidden instruction
    # thường được nhắc lại trong bối cảnh document mà assistant xử lý)
    has_attack_anywhere      = contains_any(all_text_full, ALL_USER_ATTACK_SIGNALS)
    has_harmful_asst_output  = contains_any(all_asst_text, HARMFUL_ASSISTANT_SIGNALS)
    has_out_of_scope         = contains_any(all_user_text + final_user, OUT_OF_SCOPE_SIGNALS)

    # ── 4. Language mixing check ──────────────────────────────────────────────
    if evasion == "language_mixing":
        mixed_turns = count_user_turns_with_lang_mix(sample)
        if mixed_turns < 2:
            flags.append("language_mixing_too_weak")

    # ── 5. Harmful assistant output ───────────────────────────────────────────
    if has_harmful_asst_output:
        flags.append("assistant_provided_harmful_content")

    # ── 6. Label-specific checks ──────────────────────────────────────────────
    audit_label = original_label  # KHÔNG tự động đổi nhãn, chỉ gắn cờ

    if original_label == "safe":
        # Chỉ flag khi FINAL USER rõ ràng yêu cầu attack.
        # Hard negative combos (BN03, BN04, BN05, BN07, BN11): bỏ qua flag này
        # vì chúng thiết kế có keyword để test keyword-based detector.
        if has_attack_in_final_user and combo_id not in BENIGN_HARD_NEGATIVE_COMBOS:
            flags.append("safe_but_final_user_has_attack_signal")

    elif original_label == "unsafe":
        # Chỉ gắn review flag nếu tín hiệu yếu.
        # FIX: bỏ qua với các mechanism dùng context tích lũy — rủi ro ẩn
        # trong nhiều lượt, không lộ keyword trực tiếp. Đây là by design.
        is_context_dependent = mechanism in CONTEXT_DEPENDENT_MECHANISMS
        if not is_context_dependent:
            if not has_attack_in_final_user and not has_attack_in_all_user:
                flags.append("unsafe_but_weak_attack_signal")

    elif original_label == "controversial":
        # FIX: KHÔNG flag controversial_may_be_too_safe.
        # Controversial by design thiếu keyword rõ ràng — đây là đặc trưng,
        # không phải lỗi. Chỉ flag khi final turn quá explicit (→ nên là unsafe).
        if has_attack_in_final_user:
            flags.append("controversial_but_final_user_too_explicit")

    # ── 7. In-scope check ─────────────────────────────────────────────────────
    in_scope = True

    if has_out_of_scope:
        flags.append("possibly_out_of_scope")

    if attack_type == "jailbreak" and has_out_of_scope and not has_attack_in_all_user:
        in_scope = False
        flags.append("unsafe_not_jailbreak_scope")

    # FIX: PI indirect mechanism không cần keyword lộ trong text user —
    # hidden instruction nằm trong document. Chỉ flag nếu KHÔNG tìm thấy
    # tín hiệu nào trong toàn bộ text (kể cả assistant context).
    if attack_type == "prompt_injection":
        is_indirect_pi = mechanism in PI_INDIRECT_MECHANISMS
        if is_indirect_pi:
            # Với indirect PI: scan toàn bộ text (user + assistant)
            if not has_attack_anywhere:
                flags.append("prompt_injection_signal_weak")
        else:
            # Direct PI: vẫn yêu cầu keyword trong user messages
            if not has_attack_in_all_user:
                flags.append("prompt_injection_signal_weak")

    # FIX: benign hard-negative combos có keyword attack theo thiết kế.
    # Chỉ flag các combo benign KHÁC nếu final user có dấu hiệu attack.
    if attack_type == "benign" and has_attack_in_final_user:
        if combo_id not in BENIGN_HARD_NEGATIVE_COMBOS:
            flags.append("benign_but_final_user_has_attack_signal")
        else:
            # Hard negative: gắn info flag nhẹ hơn để dễ filter sau
            flags.append("benign_hard_negative_has_attack_keyword")

    # ── 8. Quality decision ───────────────────────────────────────────────────
    CRITICAL_FLAGS = {
        "missing_or_empty_messages",
        "wrong_number_of_messages",
        "first_message_not_user",
        "last_message_not_user",
        "roles_not_alternating",
        "empty_message",
        "invalid_label",
        "invalid_attack_type",
        "assistant_provided_harmful_content",  # Nghiêm trọng — phải loại
    }
    # INFO_FLAGS: gắn để tracking nhưng KHÔNG kéo quality xuống "review"
    # benign_hard_negative_has_attack_keyword: by design, BN03/BN04/BN05/BN07/BN11
    # được sinh ra với keyword attack ở final user — đây là hard negative đúng spec.
    INFO_FLAGS = {
        "benign_hard_negative_has_attack_keyword",
    }

    REVIEW_FLAGS = {
        "safe_but_final_user_has_attack_signal",
        "unsafe_but_weak_attack_signal",        # Chỉ review, KHÔNG tự đổi nhãn
        "controversial_but_final_user_too_explicit",
        "controversial_may_be_too_safe",
        "language_mixing_too_weak",
        "unsafe_not_jailbreak_scope",
        "prompt_injection_signal_weak",
        "possibly_out_of_scope",
        "benign_but_final_user_has_attack_signal",  # chỉ áp dụng combo NGOÀI hard-negative
    }

    flag_set = set(flags)
    if flag_set & CRITICAL_FLAGS:
        quality = "bad"
    elif flag_set & REVIEW_FLAGS:
        quality = "review"
    else:
        quality = "ok"

    # ── 9. Ghi output ─────────────────────────────────────────────────────────
    audited = dict(sample)
    audited["audit_label"]  = audit_label   # giữ nguyên, không tự đổi
    audited["in_scope"]     = in_scope
    audited["quality"]      = quality
    audited["audit_flags"]  = sorted(flag_set)

    return audited


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"Loading: {INPUT_PATH}")
    samples = load_jsonl(INPUT_PATH)
    print(f"Loaded {len(samples):,} samples")

    audited_samples = [audit_sample(s) for s in samples]
    write_jsonl(OUTPUT_PATH, audited_samples)

    # ── Summary ───────────────────────────────────────────────────────────────
    label_counter       = Counter(s.get("label")        for s in audited_samples)
    audit_label_counter = Counter(s.get("audit_label")  for s in audited_samples)
    quality_counter     = Counter(s.get("quality")      for s in audited_samples)
    scope_counter       = Counter(s.get("in_scope")     for s in audited_samples)

    print(f"\n✅ Audited {len(audited_samples):,} samples → {OUTPUT_PATH}\n")

    print("Original labels:")
    for k, v in sorted(label_counter.items()):
        print(f"  {k}: {v:,}")

    print("\nAudit labels (unchanged = no auto-relabeling):")
    for k, v in sorted(audit_label_counter.items()):
        print(f"  {k}: {v:,}")

    print("\nQuality:")
    total = len(audited_samples)
    for k, v in sorted(quality_counter.items()):
        print(f"  {k}: {v:,}  ({100*v/total:.1f}%)")

    print("\nIn scope:")
    for k, v in sorted(scope_counter.items()):
        print(f"  {k}: {v:,}")

    print("\nTop audit flags:")
    flag_counter: Counter = Counter()
    for s in audited_samples:
        flag_counter.update(s.get("audit_flags", []))
    for flag, cnt in flag_counter.most_common(20):
        print(f"  {flag}: {cnt}")

    # ── Gợi ý tỷ lệ ──────────────────────────────────────────────────────────
    ok_count  = quality_counter.get("ok", 0)
    ok_pct    = 100 * ok_count / total if total > 0 else 0
    print(f"\n{'='*50}")
    if ok_pct >= 85:
        print(f"✅ OK rate {ok_pct:.1f}% — Pipeline ổn, có thể sinh full dataset.")
    elif ok_pct >= 70:
        print(f"⚠️  OK rate {ok_pct:.1f}% — Cần review các mẫu 'review' trước.")
    else:
        print(f"❌ OK rate {ok_pct:.1f}% — Pipeline cần điều chỉnh prompt/combo trước.")


if __name__ == "__main__":
    main()
