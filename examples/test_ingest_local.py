"""成员 A 本地链路测试 —— 需已安装 ffmpeg（**不需要** whisper / 网络）。

用 ffmpeg 合成一段测试视频：
    0~10s  清晰测试图（testsrc2，边缘丰富）
    10~15s 全黑
    15~20s 纯灰
然后跑通「探测 → 抽帧 → Laplacian 过滤 → manifest」，验证全黑/纯灰帧被丢弃。

运行（先确保 ffmpeg 已装）：
    python examples/test_ingest_local.py
"""
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from makeup_distiller import VideoIngestor


def make_test_video(out: Path) -> Path:
    """用 ffmpeg lavfi 合成测试视频（无网络、无需真实素材）。"""
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc2=duration=10:size=640x480:rate=30",
        "-f", "lavfi", "-i", "color=c=black:duration=5:size=640x480:rate=30",
        "-f", "lavfi", "-i", "color=c=gray:duration=5:size=640x480:rate=30",
        "-filter_complex",
        "[0:v]format=yuv420p[a];[1:v]format=yuv420p[b];[2:v]format=yuv420p[c];"
        "[a][b][c]concat=n=3:v=1:a=0[out]",
        "-map", "[out]", str(out),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        video = make_test_video(tmp / "synthetic.mp4")

        ingestor = VideoIngestor(
            workspace_root=tmp / "ws",
            transcribe=False,       # 关键：不依赖 whisper
            frame_step_sec=1.5,
        )
        manifest = ingestor.ingest(str(video))

        print(f"video_id        : {manifest.video_id}")
        print(f"时长/分辨率      : {manifest.duration_sec:.1f}s  {manifest.width}x{manifest.height} @{manifest.fps:.1f}fps")
        print(f"共抽/丢弃/保留   : {manifest.total_frames_extracted} / {manifest.frames_dropped} / {len(manifest.frames)}")
        print("保留帧示例:")
        for f in manifest.frames[:5]:
            print(f"    {f.file}  t={f.timestamp_sec:5.2f}s  sharpness={f.sharpness}")

        # 断言：20s / 1.5 ≈ 14 帧，其中 5s 黑 + 5s 灰应被丢弃
        assert manifest.total_frames_extracted >= 10, "抽帧数量异常"
        assert manifest.frames_dropped > 0, "全黑/纯灰帧未被丢弃"
        assert len(manifest.frames) > 0, "清晰帧被误丢"
        assert all(f.sharpness >= ingestor.blur_threshold for f in manifest.frames), "保留帧仍存在模糊"
        print("✅ 抽帧→过滤→manifest 链路验证通过")


if __name__ == "__main__":
    main()
