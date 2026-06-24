import os
import sys
import json
import yaml
import torch
import argparse
from pathlib import Path

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset
from trl import SFTTrainer, DataCollatorForCompletionOnlyLM

def parse_args():
    parser = argparse.ArgumentParser(description="Custom QLoRA Training Script")
    parser.add_argument("--config", type=str, required=True, help="Path to YAML config file")
    parser.add_argument("--dry_run", action="store_true", help="Run in dry-run mode (few samples, few steps)")
    parser.add_argument("--skip_training", action="store_true", help="Only run debug and exit")
    return parser.parse_args()

def load_config(yaml_path):
    with open(yaml_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def debug_loss_mask_preview(sample_messages, tokenizer, response_template_ids):
    """
    Hàm debug quan trọng nhất: Kiểm tra giả lập Loss Masking của TRL DataCollator.
    """
    print("\n" + "="*80)
    print("🛠️ DEBUG LOSS MASK PREVIEW (TRL Collator Logic Simulation)")
    print("="*80)
    
    # Simulate SFTTrainer formatting
    text = tokenizer.apply_chat_template(sample_messages, tokenize=False, add_generation_prompt=False)
    input_ids = tokenizer.encode(text, add_special_tokens=False)
    
    # Simulate TRL masking
    labels = input_ids.copy()
    match_idx = -1
    
    for i in range(len(input_ids) - len(response_template_ids) + 1):
        if input_ids[i:i+len(response_template_ids)] == response_template_ids:
            match_idx = i
            break
            
    if match_idx == -1:
        print("❌ LỖI NGHIÊM TRỌNG: Không tìm thấy response_template_ids trong input_ids!")
        print(f"Response IDs cần tìm: {response_template_ids}")
        print(f"Decoded Response: {repr(tokenizer.decode(response_template_ids))}")
        print("Vui lòng sử dụng FALLBACK manual masking thay thế!")
        return False
        
    mask_end = match_idx + len(response_template_ids)
    for i in range(mask_end):
        labels[i] = -100
        
    print("✅ Đã tìm thấy Response Template và thực hiện Masking.\n")
    print(f"{'TYPE':<10} | {'TOKEN_ID':<10} | {'TOKEN_TEXT'}")
    print("-" * 50)
    
    for tok_id, lbl_id in zip(input_ids, labels):
        token_str = tokenizer.decode([tok_id])
        token_repr = repr(token_str)
        if lbl_id == -100:
            print(f"[MASK]     | {tok_id:<10} | {token_repr}")
        else:
            print(f"[LOSS]     | {tok_id:<10} | {token_repr}")
            
    print("="*80 + "\n")
    return True

# -------------------------------------------------------------
# FALLBACK MANUAL MASKING (Nếu TRL Collator thất bại)
# -------------------------------------------------------------
def manual_preprocess_function(examples, tokenizer, max_seq_length):
    """
    Sử dụng hàm này trong `dataset.map` nếu TRL collator không hoạt động đúng.
    """
    input_ids_list = []
    labels_list = []
    attention_mask_list = []
    
    for msgs in examples['messages']:
        user_msgs = msgs[:-1]
        
        # Lấy độ dài phần user prompt (Mask)
        prompt_str = tokenizer.apply_chat_template(user_msgs, tokenize=False, add_generation_prompt=True)
        full_str = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
        
        prompt_tokens = tokenizer(prompt_str, add_special_tokens=False)['input_ids']
        full_tokens = tokenizer(full_str, add_special_tokens=False)['input_ids']
        
        prompt_len = len(prompt_tokens)
        
        label = full_tokens.copy()
        label[:prompt_len] = [-100] * prompt_len
        
        # Truncate
        if len(full_tokens) > max_seq_length:
            full_tokens = full_tokens[:max_seq_length]
            label = label[:max_seq_length]
            
        input_ids_list.append(full_tokens)
        labels_list.append(label)
        attention_mask_list.append([1] * len(full_tokens))
        
    return {
        "input_ids": input_ids_list,
        "labels": labels_list,
        "attention_mask": attention_mask_list
    }

def formatting_prompts_func(example, tokenizer):
    output_texts = []
    for i in range(len(example['messages'])):
        text = tokenizer.apply_chat_template(example['messages'][i], tokenize=False, add_generation_prompt=False)
        output_texts.append(text)
    return output_texts

def main():
    args = parse_args()
    config = load_config(args.config)
    
    # 1. Apply Dry-run Overrides
    if args.dry_run:
        print("⚠️ CHẾ ĐỘ DRY-RUN ĐƯỢC KÍCH HOẠT")
        config['output_dir'] = "outputs/qwen3guard_06b_lora_dryrun"
        config['num_train_epochs'] = 1
        config['max_steps'] = 20
        config['logging_steps'] = 1
        config['eval_steps'] = 10
        config['save_steps'] = 10
        print(f"Override Config: max_steps={config['max_steps']}, output_dir={config['output_dir']}")
        
    # Lưu lại resolved config
    os.makedirs(config['output_dir'], exist_ok=True)
    resolved_config_path = os.path.join(config['output_dir'], 'resolved_config.yaml')
    with open(resolved_config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)

    # 2. Load Tokenizer
    print(f"⏳ Đang tải Tokenizer: {config['model_name_or_path']}")
    tokenizer = AutoTokenizer.from_pretrained(config['model_name_or_path'], trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        
    # 3. Load Dataset
    print(f"⏳ Đang tải Dataset: {config['train_file']}")
    train_dataset = load_dataset("json", data_files=config['train_file'], split="train")
    eval_dataset = load_dataset("json", data_files=config['eval_file'], split="train")
    
    if args.dry_run:
        train_dataset = train_dataset.select(range(min(50, len(train_dataset))))
        eval_dataset = eval_dataset.select(range(min(20, len(eval_dataset))))
        
    # 4. Debug Mask Preview
    sample_messages = train_dataset[0]['messages']
    
    # Định nghĩa Response Template cho Qwen (ChatML)
    # add_generation_prompt=True thường thêm `<|im_start|>assistant\n`
    response_template = "<|im_start|>assistant\n"
    response_template_ids = tokenizer.encode(response_template, add_special_tokens=False)
    
    is_mask_valid = debug_loss_mask_preview(sample_messages, tokenizer, response_template_ids)
    
    if args.skip_training:
        print("🛑 --skip_training được bật. Dừng script.")
        return
        
    if not is_mask_valid:
        print("❌ Debug Mask thất bại. Vui lòng sử dụng FALLBACK manual_preprocess_function.")
        sys.exit(1)

    # 5. Load Model & LoRA
    print("⏳ Đang tải QLoRA Model (4-bit)...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=config.get('load_in_4bit', True),
        bnb_4bit_quant_type=config.get('bnb_4bit_quant_type', "nf4"),
        bnb_4bit_compute_dtype=torch.bfloat16 if config.get('bf16', False) else torch.float16,
        bnb_4bit_use_double_quant=config.get('bnb_4bit_use_double_quant', True)
    )
    
    model = AutoModelForCausalLM.from_pretrained(
        config['model_name_or_path'],
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )
    
    model = prepare_model_for_kbit_training(model)
    
    lora_config = LoraConfig(
        r=config.get('lora_r', 16),
        lora_alpha=config.get('lora_alpha', 32),
        lora_dropout=config.get('lora_dropout', 0.05),
        target_modules=config.get('lora_target_modules', "all-linear"),
        bias="none",
        task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # 6. Data Collator
    collator = DataCollatorForCompletionOnlyLM(
        response_template=response_template_ids, 
        tokenizer=tokenizer
    )

    # 7. Trainer setup
    training_args = TrainingArguments(
        output_dir=config['output_dir'],
        learning_rate=config.get('learning_rate', 2e-5),
        num_train_epochs=config.get('num_train_epochs', 3.0),
        per_device_train_batch_size=config.get('per_device_train_batch_size', 4),
        per_device_eval_batch_size=config.get('per_device_eval_batch_size', 4),
        gradient_accumulation_steps=config.get('gradient_accumulation_steps', 4),
        lr_scheduler_type=config.get('lr_scheduler_type', "cosine"),
        warmup_ratio=config.get('warmup_ratio', 0.1),
        eval_strategy=config.get('eval_strategy', "steps"),
        eval_steps=config.get('eval_steps', 100),
        save_steps=config.get('save_steps', 100),
        logging_steps=config.get('logging_steps', 10),
        save_total_limit=config.get('save_total_limit', 3),
        bf16=config.get('bf16', False),
        fp16=config.get('fp16', False),
        max_steps=config.get('max_steps', -1),
        load_best_model_at_end=config.get('load_best_model_at_end', False),
        metric_for_best_model=config.get('metric_for_best_model', "eval_loss"),
        seed=config.get('seed', 42),
        report_to="none" # Disable wandb for local run
    )
    
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        formatting_func=lambda x: formatting_prompts_func(x, tokenizer),
        data_collator=collator,
        max_seq_length=config.get('max_seq_length', 2048),
        packing=False # BẮT BUỘC ĐỂ DATA COLLATOR HOẠT ĐỘNG
    )
    
    # 8. Train & Save
    print("🚀 BẮT ĐẦU HUẤN LUYỆN...")
    trainer.train()
    
    print("💾 Đang lưu Adapter và Model State...")
    trainer.save_model(config['output_dir'])
    tokenizer.save_pretrained(config['output_dir'])
    
    # Sanity Check sau Dry-run
    if args.dry_run:
        print("\n" + "="*50)
        print("🧠 SANITY CHECK INFERENCE SAU DRY-RUN")
        print("="*50)
        
        model.eval()
        test_msg = eval_dataset[0]['messages'][:-1] # Lấy prompt, bỏ answer
        test_prompt = tokenizer.apply_chat_template(test_msg, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(test_prompt, return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=10)
            result = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
            
        print(f"Target Expected: {eval_dataset[0]['messages'][-1]['content']}")
        print(f"Model Generated: {result}")
        print("="*50 + "\n")
        
if __name__ == "__main__":
    main()
