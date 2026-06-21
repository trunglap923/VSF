Bây giờ bạn nên chuyển từ **thiết kế combo/prompt** sang **kiểm soát chất lượng dữ liệu sinh ra**. Mình đề xuất đi theo thứ tự này:

## 1. Sinh batch thử lớn hơn, chưa train vội

Bạn đã kiểm tra batch nhỏ thấy khá ổn. Bước tiếp theo nên sinh khoảng:

```text

300–500 samples

```

Mục tiêu là kiểm tra xem khi scale lên, lỗi có lặp lại không:

```text

- unsafe có bị lệch khỏi Jailbreak/Prompt Injection không

- controversial có bị quá safe không

- safe có bị dính keyword rồi sinh nhầm thành unsafe không

- language_mixing có thật sự trộn ngôn ngữ không

- long_context có đủ dài/nhiễu không

```

Chưa cần sinh full ngay, vì nếu prompt còn lỗi thì sinh full sẽ tốn công audit.

---

## 2. Viết script audit tự động

Sau khi sinh 300–500 mẫu, bạn nên thêm một file audit, ví dụ:

```text

audit_generated_samples.py

```

Script này không cần thông minh quá, chỉ cần check rule cơ bản:

```text

1. Đúng số messages không

2. User bắt đầu, user kết thúc không

3. Role có xen kẽ user/assistant không

4. Label có hợp lệ không

5. Với language_mixing: có tiếng Anh/teencode ở ít nhất 2 lượt user không

6. Với unsafe: final user có tín hiệu attack không

7. Với safe: final user có chứa request bypass/leak/payload không

8. Assistant có lỡ cung cấp payload/hướng dẫn nguy hiểm không

```

Output nên thêm các field:

```json
{
  "audit_label": "unsafe",

  "in_scope": true,

  "quality": "ok",

  "audit_flags": []
}
```

Hoặc nếu nghi ngờ:

```json
{
  "audit_label": "unsafe",

  "in_scope": true,

  "quality": "review",

  "audit_flags": ["final_user_ambiguous", "possibly_out_of_scope"]
}
```

---

## 3. Review thủ công một phần nhỏ

Bạn không cần đọc hết 500 mẫu. Chỉ cần lấy:

```text

- 30 mẫu unsafe

- 30 mẫu safe

- 30 mẫu controversial

- 20 mẫu language_mixing

- 20 mẫu long_context

```

Tổng khoảng **100–130 mẫu** để xem chất lượng.

Mục tiêu là trả lời 3 câu hỏi:

```text

1. Nhãn có đúng không?

2. Combo có bám không?

3. Có mẫu nào nguy hiểm quá chi tiết hoặc lệch scope không?

```

Nếu tỷ lệ `ok` trên 85–90% thì pipeline ổn.

---

## 4. Chốt rule xử lý dữ liệu trước train

Bạn nên chia dữ liệu thành 3 nhóm:

```text

quality = ok

→ đưa vào train



quality = review

→ để hard validation / hard test / hoặc review sau



quality = bad

→ bỏ hoặc regen

```

Không nên xóa hết mẫu “gần đúng”. Với bài toán guardrail, mẫu ranh giới rất có ích. Nhưng không nên đưa toàn bộ vào train core nếu chưa kiểm tra.

---

## 5. Sinh full dataset

Khi batch 300–500 ổn, lúc đó mới sinh full theo `combination_plan`.

Sau khi sinh full, bạn nên có các file:

```text

data/generated_raw.jsonl

data/generated_audited.jsonl

data/train.jsonl

data/val.jsonl

data/test.jsonl

data/hard_test.jsonl

```

---

## 6. Chia tập train/val/test

Gợi ý chia:

```text

Train: 70%

Validation: 10%

Test: 10%

Hard test: 10%

```

Nhưng hard test nên ưu tiên các nhóm khó:

```text

- context_dependency

- long_context_distraction

- hidden_instruction

- language_mixing

- obfuscation_word_mapping

- controversial

- benign_hard_case

```

Đặc biệt, nên tránh leakage theo `combo_id + domain + style`. Tức là đừng để cùng một kiểu mẫu quá giống nhau xuất hiện cả train và test.

---

## 7. Baseline trước khi finetune

Trước khi train, bạn nên chạy baseline với:

```text

Qwen3Guard-Gen-0.6B

Qwen3Guard-Gen-4B

nếu có GPU thì thêm 8B

```

Đo các metric:

```text

Accuracy

Macro-F1

Per-label F1

Unsafe Recall

Safe False Positive Rate

Controversial F1

Latency

Token length

```

Với bài toán của bạn, quan trọng nhất là:

```text

Unsafe Recall cao

Safe FPR không quá cao

Controversial không bị collapse về safe/unsafe

Latency chấp nhận được

```

---

## 8. Sau baseline mới quyết định finetune

Nếu Qwen3Guard baseline đã ổn, bạn chỉ cần finetune nhẹ hoặc tập trung vào tiếng Việt/hard cases.

Nếu baseline kém ở:

```text

- tiếng Việt

- multi-turn context

- prompt injection qua hidden instruction

- controversial

```

thì mới finetune QLoRA.

---

## Thứ tự việc nên làm ngay

Mình nghĩ thứ tự tốt nhất cho bạn bây giờ là:

```text

1. Sinh thêm 300–500 samples.

2. Viết script audit tự động.

3. Review thủ công khoảng 100 samples.

4. Điều chỉnh prompt/combo nếu lỗi lặp lại.

5. Sinh full dataset.

6. Chia train/val/test/hard_test.

7. Chạy baseline Qwen3Guard.

8. Sau đó mới finetune.

```

Tóm lại: **đừng train vội**. Bước tiếp theo quan trọng nhất là **audit batch 300–500 mẫu để xác nhận pipeline sinh dữ liệu ổn khi scale lên**.

Bạn làm bằng cách viết **một script audit sau sinh**, đọc từng sample trong `generated_raw.jsonl`, kiểm tra rule, rồi ghi thêm các trường:

```json
{
  "audit_label": "unsafe",

  "in_scope": true,

  "quality": "ok",

  "audit_flags": []
}
```

Tức là pipeline sẽ là:

```text

generation_jobs.jsonl

        ↓ gọi LLM sinh dữ liệu

generated_raw.jsonl

        ↓ audit_generated_samples.py

generated_audited.jsonl

        ↓ filter

train.jsonl / val.jsonl / test.jsonl

```

## 1. Ví dụ output sau audit

Input ban đầu:

```json

{

  "sample_id": "PI01_vi_000017",

  "label": "unsafe",

  "attack_type": "prompt_injection",

  "messages": [...]

}

```

Sau audit thành:

```json

{

  "sample_id": "PI01_vi_000017",

  "label": "unsafe",

  "attack_type": "prompt_injection",

  "messages": [...],



  "audit_label": "unsafe",

  "in_scope": true,

  "quality": "ok",

  "audit_flags": []

}

```

Nếu mẫu nghi ngờ:

```json
{
  "audit_label": "unsafe",

  "in_scope": false,

  "quality": "review",

  "audit_flags": ["possibly_out_of_scope", "unsafe_but_not_jailbreak_or_pi"]
}
```

---

## 2. Script audit mẫu

Bạn có thể tạo file:

```text

scripts/audit_generated_samples.py

```

Code mẫu:

```python

import json

import re

from pathlib import Path

from typing import Any



BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_PATH = BASE_DIR / "data" / "generated_raw.jsonl"

OUTPUT_PATH = BASE_DIR / "data" / "generated_audited.jsonl"



VALID_LABELS = {"safe", "controversial", "unsafe"}

VALID_ATTACK_TYPES = {"jailbreak", "prompt_injection", "benign"}



UNSAFE_SIGNALS = [

    "ignore previous",

    "ignore all previous",

    "bỏ qua",

    "bỏ qua mọi",

    "system prompt",

    "developer instruction",

    "hidden instruction",

    "hidden policy",

    "policy nội bộ",

    "reveal",

    "leak",

    "lộ",

    "tiết lộ",

    "bypass",

    "jailbreak",

    "prompt injection",

    "disable safety",

    "drop safety",

    "không được từ chối",

    "đừng từ chối",

    "no-limit",

    "unfiltered",

    "safe mode",

    "refuse",

    "refusal",

    "tool output",

    "hidden token",

    "private context",

    "secret",

]



PROMPT_INJECTION_SIGNALS = [

    "system prompt",

    "developer instruction",

    "hidden instruction",

    "ignore previous",

    "ignore all previous",

    "tool output",

    "rag",

    "retrieved",

    "system/developer",

    "instruction hierarchy",

    "hidden policy",

    "private context",

    "prompt injection",

    "lộ system",

    "tiết lộ system",

    "bỏ qua instruction",

]



JAILBREAK_SIGNALS = [

    "jailbreak",

    "bypass policy",

    "bypass safety",

    "drop safety",

    "disable safety",

    "ignore safety",

    "không được từ chối",

    "đừng từ chối",

    "bỏ qua giới hạn",

    "bỏ qua an toàn",

    "unfiltered",

    "no-limit",

    "safe mode",

    "refusal",

    "refuse",

]



OUT_OF_SCOPE_UNSAFE_SIGNALS = [

    "break into an account",

    "bypass the login",

    "guess a few passwords",

    "đột nhập tài khoản",

    "bypass đăng nhập",

    "crack password",

    "steal password",

]





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





def get_final_user(sample: dict[str, Any]) -> str:

    messages = sample.get("messages", [])

    if not messages:

        return ""

    return messages[-1].get("content", "")





def get_all_text(sample: dict[str, Any]) -> str:

    messages = sample.get("messages", [])

    return "\n".join(m.get("content", "") for m in messages)





def contains_any(text: str, patterns: list[str]) -> bool:

    text_lower = text.lower()

    return any(p.lower() in text_lower for p in patterns)





def count_english_terms_in_user_turns(sample: dict[str, Any]) -> int:

    """

    Check đơn giản cho language_mixing:

    đếm số user turns có chứa thuật ngữ tiếng Anh phổ biến.

    """

    english_terms = [

        "policy", "bypass", "refuse", "warning", "safe mode",

        "unfiltered", "no-limit", "jailbreak", "prompt injection",

        "system prompt", "rag", "tool output"

    ]



    count = 0

    for msg in sample.get("messages", []):

        if msg.get("role") != "user":

            continue

        content = msg.get("content", "").lower()

        if any(term in content for term in english_terms):

            count += 1



    return count





def check_structure(sample: dict[str, Any]) -> list[str]:

    flags = []

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





def audit_sample(sample: dict[str, Any]) -> dict[str, Any]:

    original_label = sample.get("label")

    attack_type = sample.get("attack_type")

    evasion = sample.get("evasion", "none")



    final_user = get_final_user(sample)

    all_text = get_all_text(sample)



    flags = []



    # 1. Structure checks

    flags.extend(check_structure(sample))



    # 2. Metadata checks

    if original_label not in VALID_LABELS:

        flags.append("invalid_label")



    if attack_type not in VALID_ATTACK_TYPES:

        flags.append("invalid_attack_type")



    # 3. Signal checks

    has_unsafe_signal = contains_any(final_user, UNSAFE_SIGNALS) or contains_any(all_text, UNSAFE_SIGNALS)

    has_pi_signal = contains_any(all_text, PROMPT_INJECTION_SIGNALS)

    has_jb_signal = contains_any(all_text, JAILBREAK_SIGNALS)

    has_out_of_scope_signal = contains_any(all_text, OUT_OF_SCOPE_UNSAFE_SIGNALS)



    # 4. Language mixing check

    if evasion == "language_mixing":

        mixed_user_turns = count_english_terms_in_user_turns(sample)

        if mixed_user_turns < 2:

            flags.append("language_mixing_too_weak")



    # 5. Infer audit_label by simple rules

    audit_label = original_label



    if original_label == "safe":

        if contains_any(final_user, UNSAFE_SIGNALS):

            audit_label = "unsafe"

            flags.append("safe_but_final_user_has_unsafe_signal")



    elif original_label == "unsafe":

        if not has_unsafe_signal:

            audit_label = "controversial"

            flags.append("unsafe_but_weak_attack_signal")



    elif original_label == "controversial":

        if contains_any(final_user, [

            "show me the system prompt",

            "in nguyên văn system prompt",

            "bỏ qua mọi chỉ dẫn",

            "ignore all previous",

            "bypass policy",

            "payload",

            "exact steps",

            "các bước tấn công",

        ]):

            audit_label = "unsafe"

            flags.append("controversial_but_too_explicit")

        elif not has_unsafe_signal:

            flags.append("controversial_may_be_too_safe")



    # 6. In-scope check

    in_scope = True



    if attack_type == "jailbreak":

        if not has_jb_signal and has_out_of_scope_signal:

            in_scope = False

            flags.append("unsafe_but_not_jailbreak_core")



    if attack_type == "prompt_injection":

        if not has_pi_signal:

            flags.append("prompt_injection_signal_weak")



    if attack_type == "benign":

        if audit_label == "unsafe":

            flags.append("benign_but_audit_unsafe")



    if has_out_of_scope_signal:

        flags.append("possibly_out_of_scope")



    # 7. Quality decision

    critical_flags = {

        "missing_or_empty_messages",

        "wrong_number_of_messages",

        "first_message_not_user",

        "last_message_not_user",

        "roles_not_alternating",

        "empty_message",

        "invalid_label",

        "invalid_attack_type",

    }



    review_flags = {

        "safe_but_final_user_has_unsafe_signal",

        "unsafe_but_weak_attack_signal",

        "controversial_but_too_explicit",

        "controversial_may_be_too_safe",

        "language_mixing_too_weak",

        "unsafe_but_not_jailbreak_core",

        "prompt_injection_signal_weak",

        "possibly_out_of_scope",

        "benign_but_audit_unsafe",

    }



    if any(flag in critical_flags for flag in flags):

        quality = "bad"

    elif any(flag in review_flags for flag in flags):

        quality = "review"

    else:

        quality = "ok"



    audited = dict(sample)

    audited["audit_label"] = audit_label

    audited["in_scope"] = in_scope

    audited["quality"] = quality

    audited["audit_flags"] = sorted(set(flags))



    return audited





def main() -> None:

    samples = load_jsonl(INPUT_PATH)



    audited_samples = [audit_sample(sample) for sample in samples]



    write_jsonl(OUTPUT_PATH, audited_samples)



    # Summary

    from collections import Counter



    label_counter = Counter(s.get("label") for s in audited_samples)

    audit_label_counter = Counter(s.get("audit_label") for s in audited_samples)

    quality_counter = Counter(s.get("quality") for s in audited_samples)

    scope_counter = Counter(s.get("in_scope") for s in audited_samples)



    print(f"✅ Audited {len(audited_samples):,} samples")

    print(f"Output: {OUTPUT_PATH}")



    print("\nOriginal labels:")

    for k, v in sorted(label_counter.items()):

        print(f"  {k}: {v}")



    print("\nAudit labels:")

    for k, v in sorted(audit_label_counter.items()):

        print(f"  {k}: {v}")



    print("\nQuality:")

    for k, v in sorted(quality_counter.items()):

        print(f"  {k}: {v}")



    print("\nIn scope:")

    for k, v in sorted(scope_counter.items()):

        print(f"  {k}: {v}")



    print("\nTop audit flags:")

    flag_counter = Counter()

    for s in audited_samples:

        flag_counter.update(s.get("audit_flags", []))



    for flag, cnt in flag_counter.most_common(20):

        print(f"  {flag}: {cnt}")





if __name__ == "__main__":

    main()

```

---

## 3. Cách chạy

Nếu file sinh của bạn là:

```text

data/generated_raw.jsonl

```

thì chạy:

```bash

python scripts/audit_generated_samples.py

```

Sau đó bạn sẽ có:

```text

data/generated_audited.jsonl

```

---

## 4. Cách dùng file audited để lọc train

Sau đó viết thêm script filter đơn giản:

```python

import json

from pathlib import Path



BASE_DIR = Path(__file__).resolve().parent.parent



INPUT_PATH = BASE_DIR / "data" / "generated_audited.jsonl"

TRAIN_CANDIDATE_PATH = BASE_DIR / "data" / "train_candidates.jsonl"

REVIEW_PATH = BASE_DIR / "data" / "review_samples.jsonl"

BAD_PATH = BASE_DIR / "data" / "bad_samples.jsonl"





def read_jsonl(path):

    with path.open("r", encoding="utf-8") as f:

        for line in f:

            if line.strip():

                yield json.loads(line)





def write_jsonl(path, rows):

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:

        for row in rows:

            f.write(json.dumps(row, ensure_ascii=False) + "\n")





rows = list(read_jsonl(INPUT_PATH))



train_candidates = [

    r for r in rows

    if r["quality"] == "ok"

    and r["in_scope"] is True

    and r["audit_label"] == r["label"]

]



review_samples = [

    r for r in rows

    if r["quality"] == "review"

]



bad_samples = [

    r for r in rows

    if r["quality"] == "bad"

]



write_jsonl(TRAIN_CANDIDATE_PATH, train_candidates)

write_jsonl(REVIEW_PATH, review_samples)

write_jsonl(BAD_PATH, bad_samples)



print(f"Train candidates: {len(train_candidates)}")

print(f"Review samples: {len(review_samples)}")

print(f"Bad samples: {len(bad_samples)}")

```

---

## 5. Lưu ý quan trọng

Rule-based audit **không thay thế review thủ công**, nhưng rất hữu ích để:

```text

- bắt lỗi format

- bắt sample sai nhãn rõ ràng

- tìm mẫu language_mixing yếu

- tìm unsafe lệch scope

- tách review/bad trước train

```

Với batch 300–500 mẫu, bạn chỉ cần review thủ công các mẫu có:

```json

"quality": "review"

```

Còn `quality = ok` thì có thể đưa vào train candidate trước.
