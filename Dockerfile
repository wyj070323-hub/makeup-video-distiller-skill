# 美妆视频蒸馏 Skill —— 完整运行环境（含 ffmpeg + faster-whisper 转写）
FROM python:3.11-slim

# 1) 系统级依赖：ffmpeg（ffprobe 随附）
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2) 先装依赖（利用 Docker layer cache，源码变动不重装转写依赖）
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir "faster-whisper" "av<19"

# 3) 拷贝源码并本地安装
COPY . .
RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1 \
    DISTILL_WORKSPACE=/tmp/distill_workspace

# 默认以 CLI 入口运行；传参即可处理一个视频
ENTRYPOINT ["python", "-m", "makeup_distiller.ingestor"]
