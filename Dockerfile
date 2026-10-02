# 美妆视频蒸馏 Skill —— 完整运行环境（含 ffmpeg + PyTorch/Whisper）
# 用 3.11 而非最新版：openai-whisper 的 numba/torch 依赖对 3.11 兼容性最稳。
FROM python:3.11-slim

# 1) 系统级依赖：ffmpeg（ffprobe 随附）
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2) 先装依赖（利用 Docker layer cache，源码变动不重装 torch）
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir openai-whisper

# 3) 拷贝源码并本地安装
COPY . .
RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1 \
    DISTILL_WORKSPACE=/tmp/distill_workspace

# 默认以 CLI 入口运行；传参即可处理一个视频
ENTRYPOINT ["python", "-m", "makeup_distiller.ingestor"]
