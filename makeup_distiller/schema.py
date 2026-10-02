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
