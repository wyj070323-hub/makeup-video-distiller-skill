"""成员 A 自测脚本 —— 不依赖 ffmpeg / whisper / 网络即可运行。

验证：
1. Laplacian 方差 + 亮度过滤逻辑（清晰 / 全黑 / 纯灰 / 模糊帧的判定）；
2. 中间态契约（IngestManifest / Transcript）可正确序列化。

重点看 blur 用例：模糊帧「熵值仍高但锐度低」，Laplacian 方差能正确识别，
而旧版熵值法会漏判。

运行：
    python examples/self_test.py
"""
from pathlib import Path
import sys
import tempfile

# 让脚本能直接以 python examples/self_test.py 方式导入包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageFilter

from makeup_distiller.schema import FrameInfo, IngestManifest, Transcript, TranscriptSegment
from makeup_distiller.ingestor import VideoIngestor


def _make_image(mode: str, path: Path, size=(320, 240)) -> None:
    if mode == "noise":          # 高熵高锐度帧 → 应保留
        img = Image.effect_noise(size, 64).convert("L")
    elif mode == "blur":         # 噪声 + 高斯模糊 → 熵仍高但锐度低 → 应丢弃
        img = Image.effect_noise(size, 64).convert("L").filter(ImageFilter.GaussianBlur(radius=6))
    elif mode == "black":        # 全黑帧 → 应丢弃
        img = Image.new("L", size, 0)
    elif mode == "flat":         # 纯灰帧（低熵低锐度）→ 应丢弃
        img = Image.new("L", size, 128)
    else:
        raise ValueError(mode)
    img.save(path)


def test_filter() -> None:
    ing = VideoIngestor()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        cases = {"noise": True, "black": False, "flat": False, "blur": False}
        for mode, expect_keep in cases.items():
            p = tmp / f"{mode}.jpg"
            _make_image(mode, p)
            entropy, mean, sharpness = ing._analyze_frame(p)
            got = ing._should_keep(entropy, mean, sharpness)
            assert got is expect_keep, (
                f"{mode}: 期望 keep={expect_keep}，实际={got} "
                f"(entropy={entropy:.2f}, mean={mean:.2f}, sharpness={sharpness:.1f})"
            )
            print(f"  [OK] {mode:6s} entropy={entropy:5.2f} mean={mean:5.1f} sharpness={sharpness:8.1f} -> keep={got}")


def test_manifest_roundtrip() -> None:
    manifest = IngestManifest(
        video_id="demo123",
        source_url="https://v.douyin.com/demo/",
        duration_sec=30.0,
        width=1080, height=1920, fps=30.0, frame_step_sec=1.5,
        frames=[FrameInfo(file="frames/00001.jpg", timestamp_sec=0.0, entropy=6.8, sharpness=350.0)],
        total_frames_extracted=20, frames_dropped=3,
        created_at="2026-10-02T10:00:00",
    )
    data = manifest.model_dump_json()
    restored = IngestManifest.model_validate_json(data)
    assert restored.video_id == "demo123"
    assert restored.frames[0].sharpness == 350.0

    transcript = Transcript(video_id="demo123", segments=[
        TranscriptSegment(start=0.0, end=2.4, text="今天教大家一个消肿大地色眼妆"),
    ])
    assert "消肿" in transcript.model_dump_json()
    print("  [OK] IngestManifest / Transcript JSON 序列化与反序列化一致")


if __name__ == "__main__":
    print("=== 成员 A 自测开始 ===")
    test_filter()
    test_manifest_roundtrip()
    print("=== 全部通过 ===")
