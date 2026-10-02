"""美妆视频蒸馏 Skill —— 对外暴露主接口。

成员 A（预处理）→ VideoIngestor.ingest()
成员 B（蒸馏）→ 基于 IngestManifest 消费中间态，产出 DistillationResult。
"""
from .ingestor import VideoIngestor, default_workspace_root
from .schema import (
    DistillationResult,
    FrameInfo,
    IngestManifest,
    MakeupStyle,
    SOPStep,
    StyleTaxonomy,
    Transcript,
    TranscriptSegment,
    load_taxonomy,
)

__all__ = [
    "VideoIngestor",
    "default_workspace_root",
    "IngestManifest",
    "FrameInfo",
    "Transcript",
    "TranscriptSegment",
    "SOPStep",
    "DistillationResult",
    "MakeupStyle",
    "StyleTaxonomy",
    "load_taxonomy",
]
