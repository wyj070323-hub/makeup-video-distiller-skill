from setuptools import setup, find_packages

setup(
    name="makeup_distiller_skill",
    version="0.1.0",
    description="L'Oreal Hackathon - Makeup Video Distillation Skill for Qwen3-VL",
    author="Your Team",
    packages=find_packages(),
    install_requires=[
        "dashscope>=1.14.0",   # 成员 B 用
        "pydantic>=2.0.0",
        "yt-dlp",
        "ffmpeg-python",
        "pillow",
    ],
    extras_require={
        # faster-whisper（ctranslate2）依赖较重，单独放 extras，便于轻量迭代：
        #   pip install -e ".[full]"
        # 注意：faster-whisper 1.2.x 会调 av.open(..., metadata_errors="ignore")，
        # 该参数在 PyAV 19.0.0 已被移除，故显式约束 av<19，避免转写时报 TypeError。
        "full": ["faster-whisper>=1.0.0", "av>=11.0,<19.0"],
    },
    entry_points={
        "console_scripts": [
            "makeup-ingest=makeup_distiller.ingestor:main",
        ],
    },
    python_requires=">=3.9",
)
