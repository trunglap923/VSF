# Hướng dẫn chạy đánh giá Benchmark cho Qwen3Guard

Dưới đây là hướng dẫn chi tiết cách sử dụng các tập dữ liệu benchmark đã được format để đánh giá hiệu năng của mô hình **Qwen3Guard-Gen-0.6B**.

## 1. Giới thiệu các bộ dữ liệu

Tất cả các bộ benchmark đã được chuẩn hoá về chung một định dạng `JSONL` tương thích với code evaluation (`evaluate_qwen3guard_lora.py`). Chúng đã được nén lại trong file: `data/splits/qwen3guard_benchmarks.zip` (bạn cần giải nén ra trước khi chạy).

Các bộ dữ liệu bao gồm:

| Tên File                                 | Nguồn Dataset                             | Số lượng | Loại tấn công chính                   |
| :---------------------------------------- | :----------------------------------------- | :---------- | :---------------------------------------- |
| `test_final_original_v3.jsonl`          | Tập test nội bộ (V3)                    | 1,311       | Đa dạng (Mixed)                         |
| `wildjailbreak_benchmark.jsonl`         | `allenai/wildjailbreak`                  | 2,210       | Adversarial / Jailbreak (Benign + Unsafe) |
| `jbb_behaviors_benchmark.jsonl`         | `JailbreakBench/JBB-Behaviors`           | 300         | Jailbreak Behaviors (Majority Vote Label) |
| `jailbreak3_guardrails_benchmark.jsonl` | `huyhoangdinhcong/jailbreak3-guardrails` | 4,000       | Tiếng Việt Jailbreak                    |
| `prompt_injections_benchmark.jsonl`     | `deepset/prompt-injections`              | 116         | Prompt Injection / Prompt Leaking         |
| `multi_turn_jailbreak_benchmark.jsonl`  | `tom-gibbs/multi-turn_jailbreak...`      | 6,918       | Multi-turn Jailbreak                      |

## 2. Cách chạy đánh giá

Sử dụng script `scripts/evaluation/evaluate_qwen3guard_lora.py` để chạy dự đoán. Cú pháp chung như sau:

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py \
    --base_model "Qwen/Qwen3Guard-Gen-0.6B" \
    --adapter_path "outputs/qwen3guard_06b_lora_v3" \
    --test_file "data/splits/<TÊN_FILE_BENCHMARK>.jsonl" \
    --output_file "outputs/evaluation/eval_<TÊN_BENCHMARK>_06b.jsonl" \
    --load_in_4bit
```

> [!TIP]
> Bạn có thể thay đổi `--adapter_path` thành đường dẫn thư mục chứa checkpoint LoRA 4B (nếu bạn muốn test bản 4B sau khi training xong), hoặc bỏ `--adapter_path` nếu chỉ muốn test base model chưa finetune.

### 2.1. Lệnh chạy thực tế cho từng tập:

**Test trên tập WildJailbreak:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-0.6B" --adapter_path "outputs/qwen3guard_06b_lora_v3" --test_file "data/splits/wildjailbreak_benchmark.jsonl" --output_file "outputs/evaluation/eval_wildjailbreak_06b.jsonl" --load_in_4bit
```

**Test trên tập JailbreakBench Behaviors:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-0.6B" --adapter_path "outputs/qwen3guard_06b_lora_v3" --test_file "data/splits/jbb_behaviors_benchmark.jsonl" --output_file "outputs/evaluation/eval_jbb_behaviors_06b.jsonl" --load_in_4bit
```

**Test trên tập Jailbreak3 Guardrails (Tiếng Việt):**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-0.6B" --adapter_path "outputs/qwen3guard_06b_lora_v3" --test_file "data/splits/jailbreak3_guardrails_benchmark.jsonl" --output_file "outputs/evaluation/eval_jailbreak3_guardrails_06b.jsonl" --load_in_4bit
```

**Test trên tập Prompt Injections:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-0.6B" --adapter_path "outputs/qwen3guard_06b_lora_v3" --test_file "data/splits/prompt_injections_benchmark.jsonl" --output_file "outputs/evaluation/eval_prompt_injections_06b.jsonl" --load_in_4bit
```

**Test trên tập Multi-turn Jailbreak:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-0.6B" --adapter_path "outputs/qwen3guard_06b_lora_v3" --test_file "data/splits/multi_turn_jailbreak_benchmark.jsonl" --output_file "outputs/evaluation/eval_multi_turn_jailbreak_06b.jsonl" --load_in_4bit
```

### 2.2. Đánh giá Baseline (Model gốc chưa Finetune)

Nếu bạn muốn đánh giá khả năng của mô hình gốc (baseline) trước khi được finetune để làm mốc so sánh, bạn chỉ cần bỏ tham số `--adapter_path`. Các lệnh chạy chi tiết cho từng dataset như sau:

**Baseline - Tập Internal V3:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-0.6B" --test_file "data/splits/test_final_original_v3.jsonl" --output_file "outputs/evaluation/eval_baseline_internal_v3_06b.jsonl" --load_in_4bit
```

**Baseline - Tập WildJailbreak:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-0.6B" --test_file "data/splits/wildjailbreak_benchmark.jsonl" --output_file "outputs/evaluation/eval_baseline_wildjailbreak_06b.jsonl" --load_in_4bit
```

**Baseline - Tập JailbreakBench Behaviors:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-0.6B" --test_file "data/splits/jbb_behaviors_benchmark.jsonl" --output_file "outputs/evaluation/eval_baseline_jbb_behaviors_06b.jsonl" --load_in_4bit
```

**Baseline - Tập Jailbreak3 Guardrails (Tiếng Việt):**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-0.6B" --test_file "data/splits/jailbreak3_guardrails_benchmark.jsonl" --output_file "outputs/evaluation/eval_baseline_jailbreak3_guardrails_06b.jsonl" --load_in_4bit
```

**Baseline - Tập Prompt Injections:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-0.6B" --test_file "data/splits/prompt_injections_benchmark.jsonl" --output_file "outputs/evaluation/eval_baseline_prompt_injections_06b.jsonl" --load_in_4bit
```

**Baseline - Tập Multi-turn Jailbreak:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-0.6B" --test_file "data/splits/multi_turn_jailbreak_benchmark.jsonl" --output_file "outputs/evaluation/eval_baseline_multi_turn_jailbreak_06b.jsonl" --load_in_4bit
```

### 2.3. Lệnh chạy thực tế cho 4B LoRA

Cú pháp tương tự nhưng thay `base_model`, `adapter_path` và `output_file` trỏ về 4B:

**4B LoRA - Tập Internal V3:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-4B" --adapter_path "outputs/qwen3guard_4b_lora_v3" --test_file "data/splits/test_final_original_v3.jsonl" --output_file "outputs/evaluation/eval_test_final_original_v3_4b_lora.jsonl" --load_in_4bit
```

**4B LoRA - Tập WildJailbreak:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-4B" --adapter_path "outputs/qwen3guard_4b_lora_v3" --test_file "data/splits/wildjailbreak_benchmark.jsonl" --output_file "outputs/evaluation/eval_wildjailbreak_4b_lora.jsonl" --load_in_4bit
```

**4B LoRA - Tập JailbreakBench Behaviors:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-4B" --adapter_path "outputs/qwen3guard_4b_lora_v3" --test_file "data/splits/jbb_behaviors_benchmark.jsonl" --output_file "outputs/evaluation/eval_jbb_behaviors_4b_lora.jsonl" --load_in_4bit
```

**4B LoRA - Tập Jailbreak3 Guardrails (Tiếng Việt):**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-4B" --adapter_path "outputs/qwen3guard_4b_lora_v3" --test_file "data/splits/jailbreak3_guardrails_benchmark.jsonl" --output_file "outputs/evaluation/eval_jailbreak3_guardrails_4b_lora.jsonl" --load_in_4bit
```

**4B LoRA - Tập Prompt Injections:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-4B" --adapter_path "outputs/qwen3guard_4b_lora_v3" --test_file "data/splits/prompt_injections_benchmark.jsonl" --output_file "outputs/evaluation/eval_prompt_injections_4b_lora.jsonl" --load_in_4bit
```

**4B LoRA - Tập Multi-turn Jailbreak:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-4B" --adapter_path "outputs/qwen3guard_4b_lora_v3" --test_file "data/splits/multi_turn_jailbreak_benchmark.jsonl" --output_file "outputs/evaluation/eval_multi_turn_jailbreak_4b_lora.jsonl" --load_in_4bit
```

### 2.4. Đánh giá Baseline (Model gốc 4B chưa Finetune)

Tương tự phần 2.2, chúng ta bỏ tham số `--adapter_path` đi:

**Baseline 4B - Tập Internal V3:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-4B" --test_file "data/splits/test_final_original_v3.jsonl" --output_file "outputs/evaluation/eval_baseline_internal_v3_4b.jsonl" --load_in_4bit
```

**Baseline 4B - Tập WildJailbreak:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-4B" --test_file "data/splits/wildjailbreak_benchmark.jsonl" --output_file "outputs/evaluation/eval_baseline_wildjailbreak_4b.jsonl" --load_in_4bit
```

**Baseline 4B - Tập JailbreakBench Behaviors:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-4B" --test_file "data/splits/jbb_behaviors_benchmark.jsonl" --output_file "outputs/evaluation/eval_baseline_jbb_behaviors_4b.jsonl" --load_in_4bit
```

**Baseline 4B - Tập Jailbreak3 Guardrails (Tiếng Việt):**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-4B" --test_file "data/splits/jailbreak3_guardrails_benchmark.jsonl" --output_file "outputs/evaluation/eval_baseline_jailbreak3_guardrails_4b.jsonl" --load_in_4bit
```

**Baseline 4B - Tập Prompt Injections:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-4B" --test_file "data/splits/prompt_injections_benchmark.jsonl" --output_file "outputs/evaluation/eval_baseline_prompt_injections_4b.jsonl" --load_in_4bit
```

**Baseline 4B - Tập Multi-turn Jailbreak:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py --base_model "Qwen/Qwen3Guard-Gen-4B" --test_file "data/splits/multi_turn_jailbreak_benchmark.jsonl" --output_file "outputs/evaluation/eval_baseline_multi_turn_jailbreak_4b.jsonl" --load_in_4bit
```

## 3. Đánh giá Hệ thống SafeRoute E2E (0.6B + Router + 4B)

Sau khi bạn đã huấn luyện xong Router Model (bước cuối cùng của pipeline), bạn có thể chạy kịch bản End-to-End (E2E) trên các bộ benchmark để đo lường độ chính xác tổng hợp và khả năng tiết kiệm chi phí của toàn bộ hệ thống.

Cú pháp chung:

```bash
python scripts/evaluation/evaluate_benchmark_e2e.py --dataset "data/splits/<TÊN_FILE_BENCHMARK>.jsonl"
```

**E2E - Tập Internal V3:**

```bash
python scripts/evaluation/evaluate_benchmark_e2e.py --dataset data/splits/test_final_original_v3.jsonl
```

**E2E - Tập WildJailbreak:**

```bash
python scripts/evaluation/evaluate_benchmark_e2e.py --dataset data/splits/wildjailbreak_benchmark.jsonl
```

**E2E - Tập JailbreakBench Behaviors:**

```bash
python scripts/evaluation/evaluate_benchmark_e2e.py --dataset data/splits/jbb_behaviors_benchmark.jsonl
```

**E2E - Tập Jailbreak3 Guardrails (Tiếng Việt):**

```bash
python scripts/evaluation/evaluate_benchmark_e2e.py --dataset data/splits/jailbreak3_guardrails_benchmark.jsonl
```

**E2E - Tập Prompt Injections:**

```bash
python scripts/evaluation/evaluate_benchmark_e2e.py --dataset data/splits/prompt_injections_benchmark.jsonl
```

**E2E - Tập Multi-turn Jailbreak:**

```bash
python scripts/evaluation/evaluate_benchmark_e2e.py --dataset data/splits/multi_turn_jailbreak_benchmark.jsonl
```

## 4. Xem kết quả

Sau khi chạy xong các script evaluation (Dù là đánh giá Model lẻ hay đánh giá E2E), script sẽ tự động in ra màn hình bảng so sánh các chỉ số **Accuracy**, **Recall**, **F1-Score**, và **Cost**.

Kết quả dự đoán chi tiết từng mẫu sẽ được lưu vào file JSONL trong thư mục `outputs/evaluation/`. File này sẽ chứa thêm các trường như `prediction`, `routed_to` (nếu chạy E2E) để bạn đối chiếu với `gold_label`.

> [!NOTE]
> Kết quả Evaluation này (đặc biệt là các nhãn bị đoán sai) sẽ chính là dữ liệu nền tảng rất tốt để đưa vào phân tích lỗi (Error Analysis) hoặc báo cáo hiệu năng cuối cùng!

## 5. So sánh hiệu năng các mô hình (Compare Models)

Sau khi bạn đã chạy ra kết quả dự đoán của từng mô hình lẻ (0.6B, 4B) và của cả hệ thống Router E2E trên cùng một tập benchmark, bạn có thể dùng script `compare_models.py` để tính toán metric tổng hợp và sinh ra báo cáo so sánh tự động (lưu thành file `.txt`).

**Ví dụ lệnh chạy so sánh trên tập Internal V3:**

```bash
python scripts/evaluation/compare_models.py \
    --file_06b "outputs/evaluation/eval_test_final_original_v3_06b.jsonl" \
    --file_4b "outputs/evaluation/eval_test_final_original_v3_4b_lora.jsonl" \
    --file_router "outputs/evaluation/results_test_final_clean_v3.jsonl" \
    --file_baseline_06b "outputs/evaluation/eval_baseline_internal_v3_06b.jsonl" \
    --output_txt "outputs/evaluation/report_compare_v3.txt"
```

Bạn có thể chạy báo cáo so sánh cho các bộ dataset khác bằng các lệnh sau:

**So sánh trên tập WildJailbreak:**
```bash
python scripts/evaluation/compare_models.py \
    --file_06b "outputs/evaluation/eval_wildjailbreak_06b.jsonl" \
    --file_4b "outputs/evaluation/eval_wildjailbreak_4b_lora.jsonl" \
    --file_router "outputs/evaluation/results_wildjailbreak_benchmark.jsonl" \
    --file_baseline_06b "outputs/evaluation/eval_baseline_wildjailbreak_06b.jsonl" \
    --output_txt "outputs/evaluation/report_compare_wildjailbreak.txt"
```

**So sánh trên tập JailbreakBench Behaviors:**
```bash
python scripts/evaluation/compare_models.py \
    --file_06b "outputs/evaluation/eval_jbb_behaviors_06b.jsonl" \
    --file_4b "outputs/evaluation/eval_jbb_behaviors_4b_lora.jsonl" \
    --file_router "outputs/evaluation/results_jbb_behaviors_benchmark.jsonl" \
    --file_baseline_06b "outputs/evaluation/eval_baseline_jbb_behaviors_06b.jsonl" \
    --output_txt "outputs/evaluation/report_compare_jbb_behaviors.txt"
```

**So sánh trên tập Jailbreak3 Guardrails (Tiếng Việt):**
```bash
python scripts/evaluation/compare_models.py \
    --file_06b "outputs/evaluation/eval_jailbreak3_guardrails_06b.jsonl" \
    --file_4b "outputs/evaluation/eval_jailbreak3_guardrails_4b_lora.jsonl" \
    --file_router "outputs/evaluation/results_jailbreak3_guardrails_benchmark.jsonl" \
    --file_baseline_06b "outputs/evaluation/eval_baseline_jailbreak3_guardrails_06b.jsonl" \
    --output_txt "outputs/evaluation/report_compare_jailbreak3.txt"
```

**So sánh trên tập Prompt Injections:**
```bash
python scripts/evaluation/compare_models.py \
    --file_06b "outputs/evaluation/eval_prompt_injections_06b.jsonl" \
    --file_4b "outputs/evaluation/eval_prompt_injections_4b_lora.jsonl" \
    --file_router "outputs/evaluation/results_prompt_injections_benchmark.jsonl" \
    --file_baseline_06b "outputs/evaluation/eval_baseline_prompt_injections_06b.jsonl" \
    --output_txt "outputs/evaluation/report_compare_prompt_injections.txt"
```

**So sánh trên tập Multi-turn Jailbreak:**
```bash
python scripts/evaluation/compare_models.py \
    --file_06b "outputs/evaluation/eval_multi_turn_jailbreak_06b.jsonl" \
    --file_4b "outputs/evaluation/eval_multi_turn_jailbreak_4b_lora.jsonl" \
    --file_router "outputs/evaluation/results_multi_turn_jailbreak_benchmark.jsonl" \
    --file_baseline_06b "outputs/evaluation/eval_baseline_multi_turn_jailbreak_06b.jsonl" \
    --output_txt "outputs/evaluation/report_compare_multi_turn.txt"
```

## 6. Tải kết quả về máy tính cá nhân

Sau khi bạn đã thu thập đủ các kết quả test, bạn có thể nén riêng thư mục `evaluation` lại và tải về máy tính của mình để tiện làm slide báo cáo.

**Bước 1: Nén thư mục (Chạy trên Terminal của Vast.ai)**

```bash
zip -r evaluation_results.zip outputs/evaluation/
```

**Bước 2: Tải về máy (Chạy trên Terminal/CMD ở máy tính cá nhân của bạn)**

```bash
scp vastai:/workspace/qwen3guard_work/evaluation_results.zip .
```

(Lệnh này sẽ tải file `evaluation_results.zip` về thẳng thư mục hiện tại mà bạn đang mở CMD).