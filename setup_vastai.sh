#!/bin/bash
echo "🚀 Bắt đầu cài đặt môi trường Qwen3Guard trên Vast AI..."

# 1. Cập nhật apt-get và cài đặt các công cụ cơ bản
apt-get update && apt-get install -y unzip htop tmux git jq

# 2. Cài đặt Python dependencies
echo "📦 Cài đặt thư viện Python..."
pip install --upgrade pip
pip install -r requirements.txt

# 3. Log in HuggingFace (nếu cần tải model private)
# uncomment and add token if needed
# huggingface-cli login --token "YOUR_HF_TOKEN" --add-to-git-credential

# 4. Log in WandB (để tracking quá trình train)
# uncomment and add token if needed
# wandb login "YOUR_WANDB_TOKEN"

echo "✅ Cài đặt hoàn tất! Bạn có thể bắt đầu quá trình train bằng lệnh:"
echo "python scripts/training/train.py --config configs/qwen3guard_06b_lora_v1.yaml"
