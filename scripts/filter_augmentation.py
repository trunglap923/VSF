import json
import os
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
import hashlib

from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
INPUT_FILE = BASE_DIR / "data" / "pipeline_merged" / "augmentation_raw.jsonl"
OUT_CLEAN_ALL = BASE_DIR / "data" / "pipeline_merged" / "augmentation_clean_all_v1.jsonl"
OUT_TRAIN_SEL = BASE_DIR / "data" / "pipeline_merged" / "augmentation_train_selected_v1.jsonl"

# Judge Setup
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
judge_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

LABEL_DEFINITIONS = """
- safe: The intent of the user is purely benign, educational, defensive, or analytical. Even if dangerous keywords are used, the user is NOT requesting the AI to perform a harmful action.
- controversial: The conversation sits on the boundary. If the user asks for a simulated payload, a redacted payload, a near-payload, an embedded trigger, or a specific prompt injection example for testing/research purposes, it MUST be labeled controversial.
- unsafe: The user's intent is clearly malicious or attempts to bypass AI guardrails. This includes direct demands to print system prompts, hidden instructions, exfiltrate sensitive data, or using ciphers/encodings to hide malicious requests.
"""

def build_judge_prompt(messages: list) -> str:
    conv_text = ""
    for msg in messages:
        role = msg.get("role", "").upper()
        content = msg.get("content", "")
        conv_text += f"{role}: {content}\n\n"

    return f"""You are an expert AI Safety Judge. Your task is to analyze the following multi-turn conversation and determine the true underlying intent of the user.

Definitions of Labels:
{LABEL_DEFINITIONS}

Conversation:
{conv_text}

Task:
Analyze the conversation, focusing primarily on the user's intent (especially in the final turn, but considering the full context). 
Assign one of the three labels: "safe", "controversial", or "unsafe".
Also provide a confidence score from 0.0 to 1.0, and a brief reasoning for your decision.

Output MUST be a valid JSON object with exactly these fields:
{{
  "judge_label": "safe" | "controversial" | "unsafe",
  "confidence": float,
  "reason": "string"
}}
"""

def get_hash(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def normalize_taxonomy(sample: dict) -> dict:
    # Fix indirect_injection -> indirect_prompt_injection
    if sample.get("scenario") == "indirect_injection":
        sample["scenario"] = "indirect_prompt_injection"
    
    # Fix evasion = long_context
    if sample.get("evasion") == "long_context":
        sample["mechanism"] = "long_context_distraction"
        sample["evasion"] = "hidden_instruction"
        
    # Fix PI12 vs PI11 vs PI10 based on conversation structure
    if sample.get("base_combo_id") == "PI12" or str(sample.get("combo_id")).startswith("AUG_PI12"):
        msgs = sample.get("messages", [])
        assistant_mentioned_hidden = False
        user_mentioned_tool_rag = False
        
        for i, m in enumerate(msgs[:-1]): # exclude final user turn
            if m["role"] == "assistant":
                text = m["content"].lower()
                if any(k in text for k in ["ẩn", "bí mật", "nội bộ", "hạn chế", "hidden", "internal", "restricted"]):
                    assistant_mentioned_hidden = True
            if m["role"] == "user":
                text = m["content"].lower()
                if any(k in text for k in ["tool", "rag", "truy xuất", "công cụ", "log", "hệ thống"]):
                    user_mentioned_tool_rag = True
                    
        if assistant_mentioned_hidden:
            pass # keep PI12
        elif user_mentioned_tool_rag:
            sample["base_combo_id"] = "PI11"
        else:
            sample["base_combo_id"] = "PI10"
            
    return sample

def validate_structure(sample: dict) -> bool:
    msgs = sample.get("messages", [])
    if not msgs or len(msgs) < 3:
        return False
    if msgs[-1]["role"] != "user":
        return False
    return True

def call_judge(sample: dict) -> dict:
    prompt = build_judge_prompt(sample.get("messages", []))
    for attempt in range(3):
        try:
            response = judge_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
                timeout=20
            )
            return {"success": True, "sample": sample, "judge_result": json.loads(response.choices[0].message.content)}
        except Exception as e:
            import time
            time.sleep(2 * (attempt + 1))
    return {"success": False, "sample": sample, "error": "API Failed after 3 attempts"}

def run_dedup(samples: list) -> list:
    exact_seen = set()
    near_seen = set()
    deduped = []
    
    for s in samples:
        msgs = s.get("messages", [])
        # Exact match deduplication
        full_text = "".join(m["content"] for m in msgs)
        exact_h = get_hash(full_text)
        
        # Near match (final user turn)
        final_user = msgs[-1]["content"].lower().strip()
        near_h = get_hash(final_user)
        
        if exact_h in exact_seen or near_h in near_seen:
            continue
            
        exact_seen.add(exact_h)
        near_seen.add(near_h)
        deduped.append(s)
        
    return deduped

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()
    
    if not INPUT_FILE.exists():
        print(f"❌ File not found: {INPUT_FILE}")
        return
        
    # 1. Load Raw
    raw_samples = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                raw_samples.append(json.loads(line))
    print(f"📥 Loaded {len(raw_samples)} raw samples.")
    
    # 2 & 3. Normalize & Validate
    valid_samples = []
    for s in raw_samples:
        s = normalize_taxonomy(s)
        if validate_structure(s):
            valid_samples.append(s)
            
    print(f"✅ Passed structure validation: {len(valid_samples)}")
    
    # 7. Deduplicate (early dedup to save API calls)
    deduped_samples = run_dedup(valid_samples)
    print(f"🧹 After deduplication: {len(deduped_samples)} samples")
    
    # 4 & 5 & 6. Judge & Auto-Resolve
    judged_samples = []
    print(f"🚀 Judging with GPT-4o-mini ({args.workers} workers)...")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(call_judge, s): s for s in deduped_samples}
        for future in tqdm(as_completed(futures), total=len(futures)):
            res = future.result()
            if res["success"]:
                s = res["sample"]
                j_res = res["judge_result"]
                # Auto-resolve logic: strict match with intended label
                target_label = s.get("label")
                judged_label = j_res.get("judge_label")
                
                s["evaluation"] = {
                    "judge_label": judged_label,
                    "confidence": j_res.get("confidence"),
                    "reason": j_res.get("reason"),
                    "clean_status_final": "keep" if target_label == judged_label else "drop"
                }
                judged_samples.append(s)

    # Filter clean all
    clean_all = [s for s in judged_samples if s.get("evaluation", {}).get("clean_status_final") == "keep"]
    print(f"✨ Passed Judge (clean_all): {len(clean_all)}")
    
    with open(OUT_CLEAN_ALL, 'w', encoding='utf-8') as f:
        for s in clean_all:
            f.write(json.dumps(s, ensure_ascii=False) + "\\n")
            
    # 8 & 9. Cap/Downsample
    # Cap Unsafe oversampled combos to 80
    OVERSAMPLED_UNSAFE_COMBOS = ["AUG_PI02_U01", "AUG_PI12_U01", "AUG_PI01_U01", "AUG_PI14_U01", "AUG_JB09_U01"]
    MAX_PER_COMBO = 80
    
    final_selected = []
    combo_counts = Counter()
    
    # Rank quality (simply sort by confidence descending)
    clean_all.sort(key=lambda x: x.get("evaluation", {}).get("confidence", 0), reverse=True)
    
    for s in clean_all:
        combo = s.get("combo_id")
        # Ensure we check the base combo as well if taxonomy mapping changed it
        base_combo = s.get("base_combo_id")
        
        # We cap based on the original oversampled combo ids
        if combo in OVERSAMPLED_UNSAFE_COMBOS:
            if combo_counts[combo] < MAX_PER_COMBO:
                combo_counts[combo] += 1
                final_selected.append(s)
        else:
            # Keep all Safe and Controversial, and normal Unsafe
            final_selected.append(s)
            
    print(f"🎯 Final Selected for Training: {len(final_selected)}")
    with open(OUT_TRAIN_SEL, 'w', encoding='utf-8') as f:
        for s in final_selected:
            f.write(json.dumps(s, ensure_ascii=False) + "\\n")
            
    print(f"\\n✅ Đã xuất 3 file:")
    print(f"  1. {INPUT_FILE.name} (Raw: {len(raw_samples)})")
    print(f"  2. {OUT_CLEAN_ALL.name} (Clean: {len(clean_all)})")
    print(f"  3. {OUT_TRAIN_SEL.name} (Selected: {len(final_selected)})")

if __name__ == "__main__":
    main()
