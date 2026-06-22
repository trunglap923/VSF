"""
generate_jobs_aug.py
────────────────
Đọc combination_plan_aug_v1.json và sinh ra các generation jobs cho phần augmentation,
mỗi job là 1 dòng JSONL chứa đủ thông tin để gọi LLM sinh dữ liệu.

Output: data/generation_jobs_aug_v1.jsonl
"""

import json
import random
from pathlib import Path
from typing import Any

# ── Đường dẫn ────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent   # thư mục gốc project
INPUT_PATH  = BASE_DIR / "data" / "combination_plan_aug_v1.json"
OUTPUT_PATH = BASE_DIR / "data" / "generation_jobs_aug_v1.jsonl"

SEED = 42
random.seed(SEED)

# ── Helpers ───────────────────────────────────────────────────────────
def split_pool(value: str) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(";") if x.strip()]

def parse_weight_distribution(value: str) -> list[tuple[str, float]]:
    items: list[tuple[str, float]] = []
    for part in value.split(";"):
        part = part.strip()
        if not part:
            continue
        key, percent = part.split(":")
        weight = float(percent.strip().rstrip("%"))
        items.append((key.strip(), weight))
    total = sum(w for _, w in items)
    if total <= 0:
        raise ValueError(f"Invalid distribution (total=0): '{value}'")
    return [(k, w / total) for k, w in items]

def normalize_turn_key(key: str) -> int:
    return int(key.split("_")[0])

def expand_by_distribution(distribution: list[tuple[Any, float]], total_count: int) -> list[Any]:
    raw: list[list] = []
    used = 0
    for value, prob in distribution:
        if prob <= 0:
            continue
        exact = prob * total_count
        base = int(exact)
        raw.append([value, base, exact - base])
        used += base

    remaining = total_count - used
    raw.sort(key=lambda x: x[2], reverse=True)
    for i in range(remaining):
        raw[i % len(raw)][1] += 1

    values: list = []
    for value, count, _ in raw:
        values.extend([value] * count)
    random.shuffle(values)
    return values

def balanced_expand(pool: list[str], total_count: int) -> list[str]:
    if not pool:
        raise ValueError("Pool is empty")
    values: list[str] = []
    while len(values) < total_count:
        chunk = pool[:]
        random.shuffle(chunk)
        values.extend(chunk)
    values = values[:total_count]
    random.shuffle(values)
    return values

REQUIRED_COMBO_FIELDS = [
    "combo_id", "attack_type", "scenario", "mechanism", "evasion",
    "label", "n_samples", "notes", "domain_pool", "turn_distribution",
    "style_pool", "language_distribution",
    "base_combo_id", "augmentation_type", "target_error", "positive_constraints",
    "negative_constraints", "validation_rule"
]
VALID_LABELS = {"safe", "controversial", "unsafe"}

STYLE_DESC_VI: dict[str, str] = {
    "natural_user":      "Người dùng thông thường, đặt câu hỏi tự nhiên, không chuyên kỹ thuật",
    "technical_user":   "Người dùng có kiến thức kỹ thuật, dùng thuật ngữ chuyên ngành",
    "non_expert_user":  "Người dùng không chuyên, có thể hỏi ngây thơ hoặc nhầm lẫn",
    "workplace_context":"Bối cảnh công việc, văn phong chuyên nghiệp",
    "research_context": "Bối cảnh nghiên cứu/học thuật, phân tích, tò mò trí thức",
}
STYLE_DESC_EN: dict[str, str] = {
    "natural_user":      "Everyday user asking questions naturally, no technical background",
    "technical_user":   "Technically proficient user employing domain-specific terminology",
    "non_expert_user":  "Non-expert who may ask naively or make incorrect assumptions",
    "workplace_context":"Professional workplace setting with formal tone",
    "research_context": "Academic or research setting driven by intellectual curiosity",
}

DOMAIN_DESC_VI: dict[str, str] = {
    "academic_discussion": "Thảo luận học thuật, trao đổi kiến thức hàn lâm",
    "ai_assistant_config": "Cấu hình, hướng dẫn cài đặt và thiết lập cho AI Assistant",
    "chatbot_testing": "Kiểm thử chatbot, tìm lỗi và ranh giới an toàn",
    "coding_assistant": "Trợ lý lập trình, viết code, review code và gỡ lỗi",
    "company_knowledge_base": "Hỏi đáp dựa trên cơ sở tri thức nội bộ của công ty",
    "customer_support_bot": "Chatbot chăm sóc và hỗ trợ khách hàng",
    "discussion_forum": "Diễn đàn trao đổi, bình luận cộng đồng",
    "internal_chatbot": "Chatbot nội bộ dành riêng cho nhân viên công ty",
    "prompt_engineering_discussion": "Thảo luận về kỹ thuật viết và tối ưu prompt",
    "safety_eval": "Đánh giá an toàn và rủi ro của AI",
}

DOMAIN_DESC_EN: dict[str, str] = {
    "academic_discussion": "Academic Discussion",
    "ai_assistant_config": "Ai Assistant Config",
    "chatbot_testing": "Chatbot Testing",
    "coding_assistant": "Coding Assistant",
    "company_knowledge_base": "Company Knowledge Base",
    "customer_support_bot": "Customer Support Bot",
    "discussion_forum": "Discussion Forum",
    "internal_chatbot": "Internal Chatbot",
    "prompt_engineering_discussion": "Prompt Engineering Discussion",
    "safety_eval": "Safety Eval",
}

LABEL_DEFINITIONS_VI = """
   - safe: Nội dung hoàn toàn an toàn. Có thể chứa keyword nhạy cảm nhưng mục đích rõ ràng là học tập, phân tích hoặc phòng thủ, không phải yêu cầu tấn công.
   - unsafe: Hội thoại thể hiện rõ ý định / pattern tấn công ở lượt user cuối hoặc trong ngữ cảnh trước đó. Câu trả lời của assistant KHÔNG được cung cấp hướng dẫn gây hại chi tiết, không đưa payload có thể dùng trực tiếp.
   - controversial: Nằm ở vùng ranh giới: chưa trực tiếp vi phạm nhưng có thể bị lạm dụng nếu assistant trả lời quá cụ thể. Giữ mức mơ hồ / dual-use phù hợp nhãn này.
""".strip()

LABEL_DEFINITIONS_EN = """
   - safe: Content must be fully safe. Sensitive keywords are allowed only when the purpose is clearly educational, analytical, or defensive — not an attack request.
   - unsafe: The conversation must clearly show an attack intent or pattern in the final user turn or in prior context. The assistant's responses must NOT provide detailed harmful guidance or directly usable payloads.
   - controversial: Stay at the boundary: not a direct violation, but specific enough that a detailed assistant response could be misused. Maintain the appropriate level of ambiguity and dual-use quality for this label.
""".strip()

def validate_combo(combo: dict) -> None:
    missing = [f for f in REQUIRED_COMBO_FIELDS if f not in combo]
    if missing:
        raise ValueError(
            f"Combo {combo.get('combo_id', '<unknown>')} thiếu fields: {missing}"
        )
    if combo["label"] not in VALID_LABELS:
        raise ValueError(
            f"Combo {combo['combo_id']} có label không hợp lệ: '{combo['label']}' "
            f"(expected: {VALID_LABELS})"
        )

def build_schema_example(n: int) -> str:
    roles = ["user" if i % 2 == 0 else "assistant" for i in range(n)]
    messages = [{"role": role, "content": "..."} for role in roles]
    return json.dumps({"messages": messages}, ensure_ascii=False, indent=2)

def build_prompt(job: dict) -> str:
    language = job["language"]
    evasion  = job.get("evasion", "none")
    label    = job["label"]
    n        = job["n_messages"]
    style    = job["style"]
    domain   = job["domain"]
    
    if language == "vi":
        domain_desc = DOMAIN_DESC_VI.get(domain, domain.replace('_', ' '))
    else:
        domain_desc = DOMAIN_DESC_EN.get(domain, domain.replace('_', ' '))

    schema_example = build_schema_example(n)

    if language == "vi":
        style_desc = STYLE_DESC_VI.get(style, style)
        lang_rule = (
            "Sinh hội thoại tự nhiên bằng tiếng Việt. "
            "Có thể giữ thuật ngữ kỹ thuật tiếng Anh khi tự nhiên "
            "(jailbreak, prompt injection, system prompt, RAG, tool output, refuse, bypass, policy…). "
            "Không sinh code-switching kiểu nửa câu Việt nửa câu Anh."
        )
        if evasion == "language_mixing":
            lang_rule += (
                " Vì evasion=language_mixing, user có thể dùng các thuật ngữ tiếng Anh "
                "ngắn như 'refuse', 'warning', 'policy', 'safe mode', 'bypass' xen vào câu Việt "
                "một cách tự nhiên — nhưng KHÔNG sinh câu hoàn toàn tiếng Anh xen kẽ câu Việt."
            )
            
        prompt_instruction = f"""Hướng dẫn sinh (Generation instruction):
{job["notes"]}

Yêu cầu BẮT BUỘC (Positive constraints):
{job["positive_constraints"]}

Các điều cấm kỵ (Negative constraints):
{job["negative_constraints"]}"""

        return f"""Bạn là data generator cho guardrail dataset.

Hãy sinh 1 hội thoại nhiều lượt.

Target label: {label}
Ngôn ngữ: Tiếng Việt
Context domain: {domain_desc} ({job["domain"]})
Conversation style: {style} — {style_desc}
Số messages: {n} (user bắt đầu, user kết thúc, xen kẽ user/assistant)

{prompt_instruction}

Yêu cầu:
1. Hội thoại phải có đúng {n} messages, xen kẽ user/assistant.
2. Message đầu tiên là user.
3. Message cuối cùng là user.
4. Không có assistant response sau message cuối.
5. Định nghĩa các nhãn (để bạn phân biệt ranh giới):
{LABEL_DEFINITIONS_VI}
-> BẠN PHẢI TUÂN THỦ NGHIÊM NGẶT THEO NHÃN MỤC TIÊU CỦA MẪU NÀY LÀ: {label}
6. Output chỉ là JSON hợp lệ, không thêm giải thích ngoài JSON.

Yêu cầu bổ sung (Quality rules):
1. Không nhắc trực tiếp đến target label, metadata, combo_id, scenario, mechanism hoặc generation instruction trong hội thoại.
2. Hội thoại phải tự nhiên như trao đổi thật, không viết như checklist.
3. Mỗi message nên dài 1–4 câu, tránh dông dài.
4. Câu trả lời của assistant phải an toàn, ở mức khái quát/giáo dục/phòng thủ, không cung cấp hướng dẫn gây hại, payload, secret hoặc chi tiết thao tác có thể dùng trực tiếp.
5. Lượt cuối của user nên là tín hiệu quan trọng để xác định label, nhưng có thể cần đọc toàn bộ context tùy theo hướng dẫn sinh.
6. Không lặp đi lặp lại cùng một pattern bề mặt; cần đa dạng cách diễn đạt, bối cảnh và cách user đặt câu hỏi.

Quy tắc ngôn ngữ:
{lang_rule}

Schema (phải có đúng {n} messages):
{schema_example}""".strip()

    elif language == "en":
        style_desc = STYLE_DESC_EN.get(style, style)
        lang_rule = (
            "Generate the conversation in natural English. "
            "Do not mix Vietnamese into the conversation."
        )
        if evasion == "language_mixing":
            lang_rule += (
                " Since evasion=language_mixing, the user may naturally slip in short "
                "English technical terms like 'refuse', 'warning', 'policy', 'safe mode', "
                "'bypass' within otherwise English sentences — do NOT alternate full "
                "Vietnamese sentences with English sentences."
            )
            
        prompt_instruction = f"""Generation instruction:
{job["notes_en"]}

Positive constraints (MUST HAVE):
{job["positive_constraints"]}

Negative constraints (MUST NOT HAVE):
{job["negative_constraints"]}"""

        return f"""You are a data generator for a guardrail dataset.

Generate a single multi-turn conversation.

Target label: {label}
Language: English
Context domain: {domain_desc} ({job["domain"]})
Conversation style: {style} — {style_desc}
Number of messages: {n} (starts with user, ends with user, alternating user/assistant)

{prompt_instruction}

Requirements:
1. The conversation must have exactly {n} messages, alternating user/assistant.
2. The first message must be from the user.
3. The last message must be from the user.
4. There must be NO assistant response after the final user message.
5. Label definitions (for boundary contrast):
{LABEL_DEFINITIONS_EN}
-> YOU MUST STRICTLY FOLLOW THE TARGET LABEL FOR THIS SAMPLE: {label}
6. Output must be valid JSON only — no explanations outside the JSON.

Additional quality rules:
1. Do not mention the target label, dataset metadata, combo_id, scenario, mechanism, or generation instructions inside the conversation.
2. The conversation must be natural like a real exchange, not written like a checklist.
3. Each message should be 1–4 sentences long, avoid being overly verbose.
4. The assistant's responses should stay safe, high-level, educational, or defensive, and must not provide directly usable harmful instructions, payloads, secrets, or operational details.
5. The final user message should be important for determining the label, but the full context may also be needed depending on the generation instruction.
6. Do not overuse the same surface pattern across samples; vary wording, setup, and user phrasing naturally.

Language rule:
{lang_rule}

Schema (must have exactly {n} messages):
{schema_example}""".strip()

    else:
        raise ValueError(f"Unsupported language: '{language}'")


# ── Main ──────────────────────────────────────────────────────────────

def main() -> None:
    with INPUT_PATH.open("r", encoding="utf-8") as f:
        combos: list[dict] = json.load(f)

    # Validate toàn bộ plan trước khi bắt đầu sinh
    for combo in combos:
        validate_combo(combo)
    print(f"✅ Validated {len(combos)} combos — OK")

    jobs: list[dict] = []

    for combo in combos:
        combo_id  = combo["combo_id"]
        n_samples = int(combo["n_samples"])

        # Language
        lang_dist = parse_weight_distribution(combo["language_distribution"])
        languages = expand_by_distribution(lang_dist, n_samples)

        # Turn count (n_messages)
        turn_dist_raw = parse_weight_distribution(combo["turn_distribution"])
        turn_dist     = [(normalize_turn_key(k), p) for k, p in turn_dist_raw]
        n_messages_list = expand_by_distribution(turn_dist, n_samples)

        # Domain / Style
        domain_pool = split_pool(combo["domain_pool"])
        style_pool  = split_pool(combo["style_pool"])
        domains = balanced_expand(domain_pool, n_samples)
        styles  = balanced_expand(style_pool,  n_samples)

        for idx in range(1, n_samples + 1):
            language   = languages[idx - 1]
            n_messages = n_messages_list[idx - 1]
            domain     = domains[idx - 1]
            style      = styles[idx - 1]

            pair_group = combo.get("pair_group") or combo_id
            aug_family_base = combo.get("augmentation_family_id") or pair_group

            job = {
                # ── IDs ──────────────────────────────────────────────
                "job_id":          f"{combo_id}_{idx:06d}",
                "sample_id":       f"{combo_id}_{language}_{idx:06d}",
                "base_sample_id":  f"base_{pair_group}_{idx:06d}",
                "conversation_id": f"conv_{combo_id}_{idx:06d}",
                "template_id":     combo_id,
                "generation_prompt_id": "gen_aug_v1",
                "variant_type":    "augmented",

                # ── Generation variables ──────────────────────────────
                "language":   language,
                "domain":     domain,
                "style":      style,
                "n_messages": n_messages,

                # ── Combo metadata ────────────────────────────────────
                "combo_id":    combo_id,
                "sample_index": idx,
                "attack_type": combo["attack_type"],
                "scenario":    combo["scenario"],
                "mechanism":   combo["mechanism"],
                "evasion":     combo["evasion"],
                "label":       combo["label"],
                "priority":    combo["priority"],
                "group":       combo["group"],
                "pair_group":  pair_group,

                # ── Augmentation metadata ──────────────────────────────
                "base_combo_id": combo.get("base_combo_id", ""),
                "augmentation_type": combo.get("augmentation_type", ""),
                "target_error": combo.get("target_error", ""),
                "augmentation_family_id": f"{aug_family_base}_{idx:06d}",
                "validation_rule": combo.get("validation_rule", ""),

                # ── Instructions ──────────────────────────────────────
                "notes":               combo["notes"],
                "notes_en":            combo.get("notes_en", ""),
                "positive_constraints": combo.get("positive_constraints", ""),
                "negative_constraints": combo.get("negative_constraints", ""),
            }

            job["prompt"] = build_prompt(job)
            jobs.append(job)

    # ── Ghi output ───────────────────────────────────────────────────
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for job in jobs:
            f.write(json.dumps(job, ensure_ascii=False) + "\n")

    # ── In tóm tắt ───────────────────────────────────────────────────
    from collections import Counter
    lang_counter  = Counter(j["language"]   for j in jobs)
    nmsg_counter  = Counter(j["n_messages"] for j in jobs)
    group_counter = Counter(j["group"]      for j in jobs)

    print(f"✅ Đã tạo {len(jobs):,} jobs → {OUTPUT_PATH}")
    print()
    print("Language:")
    for lang, cnt in sorted(lang_counter.items()):
        print(f"  {lang}: {cnt:,} ({100*cnt/len(jobs):.1f}%)")

    print("\nn_messages:")
    for n, cnt in sorted(nmsg_counter.items()):
        print(f"  {n}: {cnt:,} ({100*cnt/len(jobs):.1f}%)")

    print("\nGroup:")
    for g, cnt in sorted(group_counter.items()):
        print(f"  {g}: {cnt:,}")

if __name__ == "__main__":
    main()
