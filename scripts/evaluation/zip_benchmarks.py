import os
import zipfile

def main():
    # Danh sách các file JSONL cần nén
    files_to_zip = [
        "data/splits/test_final_original_v3.jsonl",
        "data/splits/wildjailbreak_benchmark.jsonl",
        "data/splits/jbb_behaviors_benchmark.jsonl",
        "data/splits/jailbreak3_guardrails_benchmark.jsonl",
        "data/splits/prompt_injections_benchmark.jsonl",
        "data/splits/multi_turn_jailbreak_benchmark.jsonl"
    ]
    
    zip_filename = "data/splits/qwen3guard_benchmarks.zip"
    
    print(f"Creating zip file: {zip_filename}")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files_to_zip:
            if os.path.exists(file):
                # Lưu file vào zip với đường dẫn gốc của nó (hoặc chỉ lấy tên file tùy bạn, ở đây lấy basename cho gọn)
                arcname = os.path.basename(file)
                zipf.write(file, arcname)
                print(f"Added {file} as {arcname}")
            else:
                print(f"WARNING: File {file} not found, skipping...")
                
    print(f"Compression completed successfully. Archive saved at: {zip_filename}")

if __name__ == "__main__":
    main()
