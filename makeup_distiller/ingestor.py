"""成员 A —— 数据工程与预处理（Video Ingestor）。

职责：
1. 用 yt-dlp 下载抖音 / 小红书 / B 站视频；
2. 用 ffmpeg 提取音频，交给 Whisper 生成带时间戳的 transcript.json；
3. 按固定步长（默认 1.5s）抽帧，并用 Laplacian 方差过滤全黑 / 模糊帧；
4. 汇总输出中间态契约 manifest.json 到 <workspace>/<video_id>/。

中间态目录契约（与成员 B 约定，字段见 schema.py，勿随意改动）：
    <workspace>/<video_id>/
    ├── source.mp4          # 原始视频
    ├── audio.wav           # 提取的 16k 单声道音频（转写用）
    ├── transcript.json     # Whisper 带时间戳字幕（schema.Transcript）
    ├── frames/             # 抽帧 + 过滤后保留的帧（frames/00001.jpg ...）
    └── manifest.json       # 中间态清单（schema.IngestManifest）

运行方式（真机）：
    python -m makeup_distiller.ingestor "https://v.douyin.com/xxxx/" --model small

只验证抽帧/过滤链路（无需 whisper）：
    python -m makeup_distiller.ingestor "本地视频.mp4" --no-transcribe
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageFilter, ImageStat

from .schema import FrameInfo, IngestManifest, Transcript, TranscriptSegment

# 3x3 Laplacian 卷积核（8 邻域），用于计算锐度/模糊度。
# 清晰帧边缘多 → 卷积后方差高；模糊/纯色帧边缘被抹平 → 方差趋近 0。
LAPLACIAN_KERNEL = (-1, -1, -1, -1, 8, -1, -1, -1, -1)


def default_workspace_root() -> Path:
    """workspace 根目录：优先读环境变量 DISTILL_WORKSPACE，否则落在系统临时目录。

    成员 A / B 必须使用同一个根目录（用环境变量约定），跨平台兼容：
    - Linux/macOS 下等价于 /tmp/distill_workspace；
    - Windows 下为 %TEMP%\\distill_workspace。
    """
    import os

    env = os.environ.get("DISTILL_WORKSPACE")
    if env:
        return Path(env)
    return Path(tempfile.gettempdir()) / "distill_workspace"


def _parse_fraction(text: str) -> float:
    """把 ffprobe 的 '30000/1001' 转成 float。"""
    try:
        num, den = text.split("/")
        return float(num) / float(den) if float(den) else 0.0
    except (ValueError, AttributeError):
        return 0.0


class VideoIngestor:
    """视频下载 + 音频转写 + 关键帧抽取的主入口。"""

    def __init__(
        self,
        workspace_root: Optional[Path] = None,
        frame_step_sec: float = 1.5,
        whisper_model: str = "small",
        language: str = "zh",
        transcribe: bool = True,
        blur_threshold: float = 100.0,
        black_brightness_threshold: float = 12.0,
        keep_audio: bool = True,
    ) -> None:
        self.workspace_root = Path(workspace_root) if workspace_root else default_workspace_root()
        self.frame_step_sec = frame_step_sec
        self.whisper_model = whisper_model
        self.language = language
        self.transcribe = transcribe
        self.blur_threshold = blur_threshold
        self.black_brightness_threshold = black_brightness_threshold
        self.keep_audio = keep_audio

    # ------------------------------------------------------------------ #
    # 顶层入口
    # ------------------------------------------------------------------ #
    def ingest(self, source: str, video_id: Optional[str] = None) -> IngestManifest:
        """完整预处理流水线：下载 → 探测 → (转写) → 抽帧过滤 → 写 manifest。"""
        self._require_ffmpeg()

        video_id = video_id or self._derive_video_id(source)
        work_dir = self.workspace_root / video_id
        work_dir.mkdir(parents=True, exist_ok=True)

        source_video = self._ensure_local_video(source, work_dir)
        probe = self._probe(source_video)

        # 转写可跳过：无 whisper / 离线开发时，仍可验证抽帧链路
        if self.transcribe:
            self._extract_audio(source_video, work_dir / "audio.wav")
            transcript = self._transcribe(work_dir / "audio.wav", video_id)
            if not self.keep_audio:
                (work_dir / "audio.wav").unlink(missing_ok=True)
        else:
            transcript = Transcript(video_id=video_id, language=self.language, model=self.whisper_model)
        (work_dir / "transcript.json").write_text(
            transcript.model_dump_json(indent=2), encoding="utf-8"
        )

        frames_dir = work_dir / "frames"
        frames, total, dropped = self._extract_frames(source_video, frames_dir)

        manifest = IngestManifest(
            video_id=video_id,
            source_url=source if self._looks_like_url(source) else None,
            source_video=source_video.name,
            duration_sec=probe["duration"],
            width=probe["width"],
            height=probe["height"],
            fps=probe["fps"],
            frame_step_sec=self.frame_step_sec,
            transcript="transcript.json",
            frames_dir="frames",
            frames=frames,
            total_frames_extracted=total,
            frames_dropped=dropped,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        (work_dir / "manifest.json").write_text(
            manifest.model_dump_json(indent=2), encoding="utf-8"
        )
        return manifest

    # ------------------------------------------------------------------ #
    # 步骤 3：下载
    # ------------------------------------------------------------------ #
    def _ensure_local_video(self, source: str, work_dir: Path) -> Path:
        """source 若是本地文件则直接复用；否则用 yt-dlp 下载到 work_dir。"""
        src_path = Path(source)
        if src_path.exists():
            return src_path.resolve()

        import yt_dlp

        opts = {
            "outtmpl": str(work_dir / "source.%(ext)s"),
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([source])

        candidates = sorted(work_dir.glob("source.*"))
        if not candidates:
            raise FileNotFoundError(f"下载失败，未在 {work_dir} 找到产物")
        target = candidates[0]
        # 契约约定为 source.mp4，非 mp4 则统一改名（ffmpeg/whisper 按内容识别，不受影响）
        if target.suffix.lower() != ".mp4":
            target = target.rename(target.with_suffix(".mp4"))
        return target

    # ------------------------------------------------------------------ #
    # 步骤 4：探测元信息
    # ------------------------------------------------------------------ #
    def _probe(self, video_path: Path) -> dict:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", str(video_path),
        ]
        data = json.loads(self._run(cmd).stdout)
        video_stream = next(s for s in data["streams"] if s["codec_type"] == "video")
        duration = float(data["format"].get("duration") or 0.0)
        if not duration:
            duration = float(video_stream.get("duration") or 0.0)
        return {
            "duration": duration,
            "width": int(video_stream.get("width") or 0),
            "height": int(video_stream.get("height") or 0),
            "fps": _parse_fraction(video_stream.get("avg_frame_rate") or "0/1"),
        }

    # ------------------------------------------------------------------ #
    # 步骤 5：抽音频
    # ------------------------------------------------------------------ #
    def _extract_audio(self, video_path: Path, out_path: Path) -> None:
        self._run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-ac", "1", "-ar", "16000", str(out_path),
        ])

    # ------------------------------------------------------------------ #
    # 步骤 6：Whisper 转写
    # ------------------------------------------------------------------ #
    def _transcribe(self, audio_path: Path, video_id: str) -> Transcript:
        try:
            import whisper
        except ImportError as exc:  # 延迟导入，避免未装 torch/whisper 时影响抽帧测试
            raise RuntimeError(
                "未安装 openai-whisper，请先执行 pip install openai-whisper"
            ) from exc

        model = whisper.load_model(self.whisper_model)
        result = model.transcribe(str(audio_path), language=self.language)
        segments = [
            TranscriptSegment(start=float(s["start"]), end=float(s["end"]), text=str(s["text"]).strip())
            for s in result.get("segments", [])
        ]
        return Transcript(video_id=video_id, language=self.language, model=self.whisper_model, segments=segments)

    # ------------------------------------------------------------------ #
    # 步骤 7：抽帧 + 过滤
    # ------------------------------------------------------------------ #
    def _extract_frames(self, video_path: Path, frames_dir: Path) -> tuple[List[FrameInfo], int, int]:
        frames_dir.mkdir(parents=True, exist_ok=True)
        fps_expr = f"1/{self.frame_step_sec}"
        self._run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-vf", f"fps={fps_expr}", "-q:v", "2", str(frames_dir / "%05d.jpg"),
        ])

        kept: List[FrameInfo] = []
        total = 0
        dropped = 0
        for idx, frame_path in enumerate(sorted(frames_dir.glob("*.jpg"))):
            total += 1
            entropy, mean, sharpness = self._analyze_frame(frame_path)
            if self._should_keep(entropy, mean, sharpness):
                timestamp = round(idx * self.frame_step_sec, 2)
                kept.append(FrameInfo(
                    file=str(frame_path.relative_to(frames_dir.parent)),
                    timestamp_sec=timestamp,
                    entropy=round(entropy, 3),
                    sharpness=round(sharpness, 2),
                ))
            else:
                dropped += 1
                frame_path.unlink(missing_ok=True)  # 丢弃全黑/模糊帧，节省空间
        return kept, total, dropped

    @staticmethod
    def _analyze_frame(path: Path) -> tuple[float, float, float]:
        """返回 (灰度熵值 0~8, 亮度均值 0~255, Laplacian 方差锐度)。

        锐度用「Laplacian 方差」衡量：清晰帧边缘多 → 方差高；
        模糊/纯色帧边缘被抹平 → 方差趋近 0。比熵值更能区分「高熵但模糊」的帧。
        """
        img = Image.open(path).convert("L")
        entropy = img.entropy()
        mean = ImageStat.Stat(img).mean[0]
        edges = img.filter(ImageFilter.Kernel((3, 3), LAPLACIAN_KERNEL, scale=1))
        # 裁掉卷积边界伪影：Kernel 在边缘外扩会产生 1px 非零环，
        # 否则均匀/纯色帧会被误判为"清晰"。裁 2px 安全余量。
        w, h = edges.size
        edges = edges.crop((2, 2, w - 2, h - 2))
        sharpness = ImageStat.Stat(edges).var[0]
        return entropy, mean, sharpness

    def _should_keep(self, entropy: float, mean: float, sharpness: float) -> bool:
        if mean < self.black_brightness_threshold:  # 全黑帧
            return False
        if sharpness < self.blur_threshold:  # 模糊/纯色帧（Laplacian 方差过低）
            return False
        return True

    # ------------------------------------------------------------------ #
    # 工具方法
    # ------------------------------------------------------------------ #
    @staticmethod
    def _looks_like_url(text: str) -> bool:
        return bool(re.match(r"^https?://", text.strip()))

    @staticmethod
    def _derive_video_id(source: str) -> str:
        src = source.strip()
        if Path(src).exists():
            return Path(src).stem
        # 尝试提取平台短 id，失败则用 URL 哈希兜底
        m = re.search(r"(?:video/|item/|/v/|BV[0-9A-Za-z]+|/e/)([0-9A-Za-z_-]+)", src)
        if m:
            return m.group(1)[:16]
        return hashlib.sha1(src.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def _require_ffmpeg() -> None:
        if shutil.which("ffmpeg") is None:
            raise RuntimeError(
                "未找到 ffmpeg，请先安装并加入 PATH。\n"
                "  Windows: winget install Gyan.FFmpeg  (或 choco install ffmpeg)\n"
                "  macOS:   brew install ffmpeg\n"
                "  Ubuntu:  sudo apt-get install -y ffmpeg"
            )

    @staticmethod
    def _run(cmd: List[str]) -> subprocess.CompletedProcess:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"命令执行失败：{' '.join(cmd)}\n{proc.stderr[-1000:]}")
        return proc


def main() -> None:
    parser = argparse.ArgumentParser(description="成员 A：美妆视频预处理 ingestor")
    parser.add_argument("source", help="视频 URL 或本地文件路径")
    parser.add_argument("--step", type=float, default=1.5, help="抽帧步长（秒）")
    parser.add_argument("--model", default="small", help="Whisper 模型：tiny/base/small/medium")
    parser.add_argument("--blur-threshold", type=float, default=100.0, help="Laplacian 方差阈值，低于则判为模糊帧")
    parser.add_argument("--no-transcribe", action="store_true", help="跳过 Whisper 转写（仅测抽帧/过滤链路）")
    parser.add_argument("--workspace", default=None, help="workspace 根目录（默认读 DISTILL_WORKSPACE）")
    args = parser.parse_args()

    ingestor = VideoIngestor(
        workspace_root=Path(args.workspace) if args.workspace else None,
        frame_step_sec=args.step,
        whisper_model=args.model,
        transcribe=not args.no_transcribe,
        blur_threshold=args.blur_threshold,
    )
    manifest = ingestor.ingest(args.source)
    print(f"[完成] video_id={manifest.video_id}")
    print(f"[抽帧] 保留 {len(manifest.frames)} / 共抽 {manifest.total_frames_extracted} / 丢弃 {manifest.frames_dropped}")
    print(f"[清单] {ingestor.workspace_root / manifest.video_id / 'manifest.json'}")


if __name__ == "__main__":
    main()
