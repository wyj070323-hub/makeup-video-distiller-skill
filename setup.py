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
        # openai-whisper 依赖 PyTorch（体积大），单独放 extras，便于轻量迭代：
        #   pip install -e ".[full]"
        "full": ["openai-whisper>=20231117"],
    },
    entry_points={
        "console_scripts": [
            "makeup-ingest=makeup_distiller.ingestor:main",
        ],
    },
    python_requires=">=3.9",
)
