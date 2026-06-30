import os
import shutil

# Destination directory
dest_dir = "qwen3guard_work"

# List of files to copy
files_to_copy = [
    "data/training/qwen3guard/train_sft_qwen3guard_v3.jsonl",
    "data/training/qwen3guard/val_sft_qwen3guard_v3.jsonl",
    "data/splits/router_pool_v3.jsonl",
    "data/splits/test_final_clean_v3.jsonl",
    "scripts/training/train.py",
    "scripts/evaluation/evaluate_qwen3guard_lora.py",
    "scripts/evaluation/error_analysis.py",
    # Data formatting & Benchmarking
    "scripts/evaluation/format_wildjailbreak_benchmark.py",
    "scripts/evaluation/format_jbb_behaviors_benchmark.py",
    "scripts/evaluation/format_jailbreak3_guardrails.py",
    "scripts/evaluation/format_prompt_injections.py",
    "scripts/evaluation/format_multi_turn_jailbreak.py",
    "scripts/evaluation/zip_benchmarks.py",
    "scripts/evaluation/evaluate_benchmark_e2e.py",
    "scripts/evaluation/compare_models.py",
    "data/splits/test_final_original_v3.jsonl",
    "data/splits/wildjailbreak_benchmark.jsonl",
    "data/splits/jbb_behaviors_benchmark.jsonl",
    "data/splits/jailbreak3_guardrails_benchmark.jsonl",
    "data/splits/prompt_injections_benchmark.jsonl",
    "data/splits/multi_turn_jailbreak_benchmark.jsonl",
    "BENCHMARK_GUIDE.md",
    
    # Router Pipeline scripts
    "scripts/training/extract_features.py",
    "scripts/training/verify_router_dataset.py",
    "scripts/training/build_router_dataset.py",
    "scripts/training/train_router.py",
    "scripts/evaluation/router_inference.py",
    "scripts/evaluation/evaluate_e2e_system.py",
    
    # New Test Scripts
    "scripts/evaluation/test_inference_gpu.py",
    "scripts/evaluation/test_router_speed.py",
    "scripts/evaluation/single_file_router_test.py",
    
    # Config files
    "configs/qwen3guard_06b_lora_v1.yaml",
    "configs/qwen3guard_4b_lora_v1.yaml",
    "configs/router_config_v1.yaml",
    "configs/cost_matrix_v1.yaml",
    "requirements.txt",
    "setup_vastai.sh",
    "train.sh",
    "eval.sh"
]

print(f"Bắt đầu copy các file sang thư mục: {dest_dir}")
import shutil
# Copy README to README.md in destination
if os.path.exists("README_vast.md"):
    dest_path = os.path.join(dest_dir, "README.md")
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    shutil.copy2("README_vast.md", dest_path)
    print(f"✅ Đã copy: README_vast.md -> README.md")

for file_path in files_to_copy:
    if os.path.exists(file_path):
        # Create destination path maintaining directory structure
        dest_path = os.path.join(dest_dir, file_path)
        
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        # Copy the file
        shutil.copy2(file_path, dest_path)
        print(f"✅ Đã copy: {file_path}")
    else:
        print(f"❌ Không tìm thấy file: {file_path}")

print("\nHoàn tất quá trình copy!")

print("Đang nén thư mục thành file zip...")
shutil.make_archive(dest_dir, 'zip', dest_dir)
print(f"✅ Đã tạo file nén: {dest_dir}.zip")
