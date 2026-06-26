# Qwen3Guard Training Pipeline

Quy trình train và đánh giá mô hình Qwen3Guard trên GPU (Vast AI).

## Cấu trúc thư mục

```
qwen3guard/
├── configs/
├── data/
│   ├── training/
│   └── splits/
├── scripts/
├── requirements.txt
├── setup_vastai.sh
├── train.sh
├── eval.sh
└── README.md
```

## Hướng dẫn chạy nhanh trên Vast.ai

**Bước 1: Giải nén & Setup**
```bash
unzip qwen3guard_work.zip -d qwen3guard
cd qwen3guard
chmod +x setup_vastai.sh train.sh eval.sh
./setup_vastai.sh
```

**Bước 2: Train mô hình**
```bash
./train.sh
```

**Bước 3: Evaluate & Lấy file Output**
```bash
./eval.sh
```

Sau khi chạy xong, file `outputs.zip` sẽ được tạo ra chứa checkpoints và logs. Bạn có thể dùng SCP hoặc tải trực tiếp về máy.
