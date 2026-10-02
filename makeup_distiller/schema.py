"""数据契约（Contract-First，成员 A / B 共同约定，勿随意改动字段）。

本文件承载两层契约：
1. 阶段一（成员 A 产出）的中间态数据：Transcript / FrameInfo / IngestManifest；
2. 阶段二（成员 B 产出）的最终结构化结果：SOPStep / DistillationResult。

成员 B 只读成员 A 写出的 ``manifest.json`` 与 ``transcript.json``，
即可与成员 A 完全解耦并行开发。
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 阶段一 · 中间态契约（成员 A 产出）
# ---------------------------------------------------------------------------

class TranscriptSegment(BaseModel):
    """Whisper 输出的单句字幕（带毫秒级时间戳）。"""
    start: float = Field(..., description="起始时间，单位秒")
    end: float = Field(..., description="结束时间，单位秒")
    text: str = Field(..., description="该句字幕文本")


class Transcript(BaseModel):
    """口播字幕全集，写入 transcript.json。"""
    video_id: str
    language: str = "zh"
    model: str = Field("small", description="Whisper 模型规模")
    segments: List[TranscriptSegment] = Field(default_factory=list)


class FrameInfo(BaseModel):
    """单张关键帧的信息（仅记录过滤后保留的帧）。"""
    file: str = Field(..., description="相对路径，如 frames/00001.jpg")
    timestamp_sec: float = Field(..., description="帧在视频中的时刻（秒）")
    entropy: float = Field(..., description="灰度熵值（0~8），供成员 B 调试参考")
    sharpness: Optional[float] = Field(None, description="Laplacian 方差锐度，越大越清晰")


class IngestManifest(BaseModel):
    """中间态清单，写入 manifest.json —— 这是成员 B 的唯一入口。"""
    video_id: str
    source_url: Optional[str] = None
    source_video: str = Field("source.mp4", description="原始视频相对文件名")
    duration_sec: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    frame_step_sec: float = Field(1.5, description="抽帧步长（秒）")
    transcript: str = Field("transcript.json", description="字幕文件相对路径")
    frames_dir: str = Field("frames", description="帧目录相对路径")
    frames: List[FrameInfo] = Field(default_factory=list, description="过滤后保留的帧")
    total_frames_extracted: int = 0
    frames_dropped: int = 0
    created_at: str = ""


# ---------------------------------------------------------------------------
# 阶段二 · 最终结构化契约（成员 B 产出）
# ---------------------------------------------------------------------------

class SOPStep(BaseModel):
    """单步美妆 SOP。"""
    step_id: int
    timestamp: str = Field(..., description='时间戳，如 "00:15"')
    action_description: str = Field(..., description="动作要领")
    facial_zone: str = Field(..., description='上妆部位，如"眼尾"')
    tool_type: str = Field(..., description='抽象工具，如"扁头细节刷"')
    technique_tips: str = Field(..., description="避坑/技巧提示")


class DistillationResult(BaseModel):
    """最终蒸馏结果。"""
    video_id: str
    makeup_style: str = Field(..., description='妆容风格，如"消肿大地色眼妆"')
    suitable_features: List[str] = Field(
        default_factory=list, description='适合特征，如"肿眼泡"、"内双"'
    )
    sop_steps: List[SOPStep] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 妆容风格分类法（受控词表，数据见 makeup_distiller/taxonomy.json）
# ---------------------------------------------------------------------------

class MakeupStyle(BaseModel):
    """单个妆容风格条目，对应 taxonomy.json 中 styles 的一项。"""
    id: str = Field(..., description="稳定 slug，如 korean")
    name: str = Field(..., description="风格名，如 韩式妆")
    aliases: List[str] = Field(default_factory=list, description="别名")
    style_archetypes: List[str] = Field(
        default_factory=list,
        description="适合风格：古典/自然/优雅/浪漫/少年/少女/前卫/戏剧/时尚",
    )
    bone_mass: List[str] = Field(
        default_factory=list, description="量感：小量感/中量感/大量感"
    )
    bone_texture: List[str] = Field(
        default_factory=list, description="骨骼质感：骨感/肉感/适中"
    )
    face_type: str = Field("", description="浓淡颜：浓颜系/淡颜系/浓淡皆可")
    essence: List[str] = Field(default_factory=list, description="妆容要点关键词")
    attributes_complete: bool = Field(False, description="是否已从原始笔记补齐属性")
    covered_video: Optional[str] = Field(None, description="已覆盖该风格的视频 video_id")
    coverage: str = Field("missing", description="covered / partial / missing")
    notes: str = Field("", description="备注（OCR 存疑、映射说明等）")


class StyleTaxonomy(BaseModel):
    """完整妆容风格分类法。"""
    version: str = "1.0"
    updated_at: str = ""
    note: str = ""
    attribute_axes: dict = Field(default_factory=dict, description="属性轴取值表")
    styles: List[MakeupStyle] = Field(default_factory=list)


def load_taxonomy() -> StyleTaxonomy:
    """读取随包分发的 taxonomy.json，返回校验后的 StyleTaxonomy。"""
    import json
    from pathlib import Path

    path = Path(__file__).parent / "taxonomy.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return StyleTaxonomy.model_validate(data)
