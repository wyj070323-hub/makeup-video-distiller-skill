# 美妆视频蒸馏 Skill —— 成员 A 预处理模块

> 欧莱雅黑客松 · 成员 A（数据工程 & 预处理）交付物。
> 负责把抖音 / 小红书 / B 站妆教视频转成「中间态数据契约」，供成员 B 的 Qwen3-VL 蒸馏引擎消费。

## 1. 系统依赖

必须安装 **ffmpeg**（`ffprobe` 随附）：

| 平台 | 命令 |
|---|---|
| Windows | `winget install Gyan.FFmpeg` 或 `choco install ffmpeg` |
| macOS | `brew install ffmpeg` |
| Ubuntu | `sudo apt-get install -y ffmpeg` |

Python 依赖（轻量核心）：

```bash
pip install -r requirements.txt
# 若需字幕转写，再装（含 PyTorch，较大）：
pip install openai-whisper
```

## 2. 中间态数据契约（与成员 B 约定）

workspace 根目录：默认系统临时目录，或环境变量 `DISTILL_WORKSPACE` 指定（**A/B 必须一致**）。

```
<workspace>/<video_id>/
├── source.mp4          # 原始视频
├── audio.wav           # 16k 单声道音频（转写用，可关）
├── transcript.json     # 带时间戳字幕（schema.Transcript）
├── frames/             # 抽帧 + 过滤后保留的关键帧
└── manifest.json       # 成员 B 的唯一入口（schema.IngestManifest）
```

`manifest.json` 关键字段：`video_id`、`duration_sec`、`width/height/fps`、`frames[{file,timestamp_sec,entropy}]`、`transcript`、`frames_dir`。

## 3. 使用方式

```python
from makeup_distiller import VideoIngestor

ingestor = VideoIngestor(whisper_model="small", frame_step_sec=1.5)
manifest = ingestor.ingest("https://v.douyin.com/xxxx/")
print(manifest.model_dump_json(indent=2))
```

命令行：

```bash
python -m makeup_distiller.ingestor "https://v.douyin.com/xxxx/" --model small --step 1.5
# 只验证抽帧/过滤链路（不装 whisper 也可）：
python -m makeup_distiller.ingestor "本地视频.mp4" --no-transcribe
```

## 4. 自测

| 脚本 | 依赖 | 验证内容 |
|---|---|---|
| `examples/self_test.py` | 仅 Pillow | Laplacian 方差过滤 + 契约序列化（离线可跑） |
| `examples/test_ingest_local.py` | ffmpeg | 抽帧→过滤→manifest 完整链路（合成视频，无需 whisper/网络） |

```bash
python examples/self_test.py          # 无需任何系统依赖
python examples/test_ingest_local.py  # 需先装 ffmpeg
```

## 5. 打包 / 容器

```bash
pip install -e .            # 轻量安装（不含 whisper）
pip install -e ".[full]"    # 含 whisper（PyTorch，体积大）
docker build -t makeup-distiller .
```

