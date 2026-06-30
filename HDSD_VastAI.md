# HƯỚNG DẪN HUẤN LUYỆN VÀ ĐÁNH GIÁ MÔ HÌNH TRÊN VAST.AI

Tài liệu này tổng hợp lại toàn bộ quy trình từ lúc đẩy code lên GPU Server (Vast.ai) cho đến khi huấn luyện (Train), đánh giá (Test) và tải kết quả về máy cá nhân.

## BƯỚC 1: Đẩy dữ liệu lên Server

Trên **máy tính cá nhân** (Mở CMD hoặc PowerShell tại thư mục `Company`), chạy lệnh sau để upload toàn bộ mã nguồn và dữ liệu lên server:

```bash
scp qwen3guard_work.zip vastai:/workspace/
```

## BƯỚC 2: Cài đặt Môi trường (Giải quyết lỗi CUDA)

Truy cập vào **Terminal của Vast.ai**, tiến hành giải nén và cài đặt môi trường. (Lệnh `setup_vastai.sh` sẽ tự động biên dịch thư viện C++ `bitsandbytes` để phù hợp với phiên bản CUDA của máy chủ đó, giúp tránh lỗi văng VRAM).

```bash
cd /workspace
unzip -o qwen3guard_work.zip -d qwen3guard_work/
cd qwen3guard_work
bash setup_vastai.sh
```

## BƯỚC 3: Quản lý cửa sổ Terminal (Tmux)

Để theo dõi tiến trình hiệu quả, hãy chia đôi màn hình Terminal của Vast.ai:

1. Bấm `Ctrl + B`, thả tay ra.
2. Bấm phím `"` (để chia trên/dưới) hoặc `%` (để chia trái/phải).
3. Chuyển qua lại giữa các ô bằng cách bấm `Ctrl + B` rồi dùng các phím **Mũi tên**.

Ở ô màn hình phụ, chạy lệnh sau để theo dõi dung lượng VRAM và công suất GPU theo thời gian thực:

```bash
watch -n 1 nvidia-smi
```

## BƯỚC 4: Huấn luyện (Fine-tuning)

Ở ô màn hình chính, kích hoạt kịch bản huấn luyện:

```bash
bash train.sh
```

_Lưu ý: Mô hình 0.6B trên card A100 sẽ mất khoảng 40 phút. Cấu hình đã được tối ưu chống tràn VRAM bằng `gradient_checkpointing` và `gradient_accumulation_steps`._

## BƯỚC 5: Kiểm thử (Evaluation)

Sau khi quá trình Train kết thúc, hãy chạy kịch bản Test Mù để tính điểm Accuracy, F1-Score:

**Để kiểm thử mô hình 0.6B:**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py \
    --base_model "Qwen/Qwen3Guard-Gen-0.6B" \
    --adapter_path "outputs/qwen3guard_06b_lora_v3" \
    --test_file "data/splits/test_final_clean_v3.jsonl" \
    --output_file "outputs/eval_results_06b_lora.jsonl" \
    --load_in_4bit
```

**Để kiểm thử mô hình 4B (Sau khi Train xong):**

```bash
python scripts/evaluation/evaluate_qwen3guard_lora.py \
    --base_model "Qwen/Qwen3Guard-Gen-4B" \
    --adapter_path "outputs/qwen3guard_4b_lora_v3" \
    --test_file "data/splits/test_final_clean_v3.jsonl" \
    --output_file "outputs/eval_results_4b_lora.jsonl" \
    --load_in_4bit
```

## BƯỚC 6: Sao lưu và Tải kết quả về máy

**Tại Terminal của Vast.ai:** Nén dữ liệu. Bạn có 2 tuỳ chọn:

- **Tuỳ chọn 1 (Lưu toàn bộ):** Nén toàn bộ cả LoRA Checkpoint (vài GB) và file đánh giá (Eval).

```bash
zip -r outputs_backup.zip outputs/
```

- **Tuỳ chọn 2 (Chỉ lưu kết quả Eval):** Nếu bạn chỉ muốn lưu các file dự đoán `.jsonl` để tiết kiệm dung lượng và thời gian tải.

```bash
zip -j eval_results.zip outputs/*.jsonl
```

**Tại máy tính cá nhân (CMD / PowerShell):** Chạy lệnh tải về tương ứng với file bạn vừa nén:

```bash
scp vastai:/workspace/qwen3guard_work/outputs_backup.zip .
# Hoặc nếu dùng Tuỳ chọn 2:
scp vastai:/workspace/qwen3guard_work/eval_results.zip .
```

Sau đó bạn có thể giải nén file `.zip` vừa tải về trên máy cá nhân để phân tích lỗi hoặc viết báo cáo.

---

## GIAI ĐOẠN 2: HUẤN LUYỆN ROUTER (ĐIỀU PHỐI ĐỘNG)

Khi bạn đã hoàn thành việc huấn luyện cho mô hình con (0.6B) và mô hình to (4B/8B), hệ thống cần một bộ Router để quyết định xem câu hỏi nào sẽ được giao cho mô hình nào xử lý.

## BƯỚC 7: Trích xuất đặc trưng (Feature Extraction)

Ta cần chạy lại tập dữ liệu qua mô hình 0.6B và 4B để lấy "Độ tự tin" (Logits) và "Trạng thái ẩn" (Hidden States) làm tài nguyên cho Router:

```bash
python scripts/training/extract_features.py
```

_(Cấu hình sẽ được tự động đọc từ file `configs/router_config_v1.yaml`)_

## BƯỚC 8: Kiểm định và Gán nhãn cho Router

Kịch bản này sẽ xem xét câu nào con 0.6B trả lời sai thì gán nhãn `1` (Cần cầu cứu con to), câu nào trả lời đúng gán nhãn `0` (Tự xử lý được).

```bash
python scripts/training/verify_router_dataset.py
python scripts/training/build_router_dataset.py
```

## BƯỚC 9: Huấn luyện Router

Dựa trên các đặc trưng (Features) và Nhãn (Labels) vừa tạo, ta train các thuật toán Machine Learning truyền thống (LR, PCA, XGBoost, MLP) để làm người gác cổng:

```bash
python scripts/training/train_router.py
```

## BƯỚC 10: Đánh giá hệ thống End-to-End

Cuối cùng, kịch bản này sẽ mô phỏng lại toàn bộ hệ thống thực tế (Router + Small Model + Large Model), in ra bảng phân tích chi phí cuối cùng và Upper Bound Oracle để so sánh hiệu năng.

```bash
python scripts/evaluation/evaluate_e2e_system.py
```

---

## MẸO TIẾT KIỆM: THUÊ SERVER MỚI ĐỂ TRAIN TIẾP (RESUME WORKFLOW)

Nếu bạn hủy máy chủ cũ để tiết kiệm chi phí và thuê một máy chủ mới vào ngày hôm sau để Train con 4B, hãy làm theo các bước sau để "hợp nhất" dữ liệu:

**1.** Đảm bảo đã cập nhật IP/Port mới trong file `~/.ssh/config` trên máy cá nhân.

**2.** Tải mã nguồn lên Server mới và Train con 4B như bình thường:

```bash
scp qwen3guard_work.zip vastai:/workspace/
```

(Sau đó trên Server: Giải nén, cài môi trường `bash setup_vastai.sh` và chạy `python scripts/training/train.py --config configs/qwen3guard_4b_lora_v1.yaml`).

**3.** **ĐỢI KHI CON 4B TRAIN XONG**, tải file `outputs_backup.zip` (chứa kết quả của con 0.6B mà bạn đã tải về trước đó) lên Server mới:

```bash
scp outputs_backup.zip vastai:/workspace/qwen3guard_work/
```

**4.** Giải nén trên Terminal của Server để hợp nhất 2 mô hình vào chung thư mục `outputs`:

```bash
unzip -o outputs_backup.zip
```

Lúc này bạn đã có đủ cả 2 thư mục (`qwen3guard_06b_lora_v3` và `qwen3guard_4b_lora_v3`) trên Server. Bạn có thể tự tin chạy tiếp **Giai đoạn 2 (BƯỚC 7 - 10)**.