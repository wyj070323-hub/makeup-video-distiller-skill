# 妆容风格分类法（Makeup Style Taxonomy）

> 契约版本：`taxonomy.json` v1.0 · 2026-10-02
> 机器可读数据源：`makeup_distiller/taxonomy.json`（成员 B 通过 `load_taxonomy()` 读取）
> 用途：作为 `DistillationResult.makeup_style` 的**受控词表**，让每个蒸馏出的 Skill 都落在一个标准风格标签上，从而支撑「识别不同妆容」的检索/匹配。

## 1. 数据来源

小红书两条笔记的卡片（OCR 提取）：

- 「2026🌟16种妆容趋势盘点｜找到你的本命妆容」
- 「被这些妆容硬控了！✨ 承包你一个月的不同风格妆」

两条笔记合并共 **20 个风格**。其中 12 个（新中式妆及之后）带完整属性卡片，8 个（高智妆～野猫妆）目前只有风格名，属性待补。

## 2. 三个属性轴（识别妆容的特征维度）

每条风格尽量用下面三个轴打标签，这是「识别妆容」的核心区分维度：

| 轴 | 字段 | 取值 |
|---|---|---|
| 适合风格（气质原型） | `style_archetypes` | 古典 / 自然 / 优雅 / 浪漫 / 少年 / 少女 / 前卫 / 戏剧 / 时尚 |
| 适合骨骼·量感 | `bone_mass` | 小量感 / 中量感 / 大量感 |
| 适合骨骼·质感 | `bone_texture` | 骨感 / 肉感 / 适中 |
| 浓淡颜 | `face_type` | 浓颜系 / 淡颜系 / 浓淡皆可 |
| 妆容要点（自由关键词） | `essence` | 如 贵气、清透、低饱和、重结构轻色彩 |

## 3. 风格清单（20 个）

| # | id | 风格 | 浓淡颜 | 量感 | 要点 | 覆盖 |
|---|---|---|---|---|---|---|
| 1 | gao_zhi | 高智妆 | — | — | — | ⬜ 缺 |
| 2 | korean | 韩式妆 | — | — | — | ✅ BV12Z5v6nEdb |
| 3 | asian_flattering | 亚裔妆 | — | — | — | ✅ BV1P5LA6sEEh |
| 4 | rich_girl | 千金妆 | — | — | — | ⬜ 缺 |
| 5 | hong_kong | 港风妆 | — | — | — | ⬜ 缺 |
| 6 | plain_water | 白开水妆 | — | — | — | 🟡 BV1kK7a6gEq9（伪素颜，近似） |
| 7 | japanese_magazine | 日杂妆 ⚠️ | — | — | — | ⬜ 缺 |
| 8 | wild_cat | 野猫妆 | — | — | — | ⬜ 缺 |
| 9 | thai_mature | 泰系御姐 | 浓颜系 | 大量感 | 贵气·成熟·重结构轻色彩 | ⬜ 缺 |
| 10 | euro_mixed | 轻欧混血妆 | 淡颜系 | 中/小量感 | 盐系·清爽·低饱和 | ⬜ 缺 |
| 11 | new_chinese | 新中式妆 | 淡颜系 | 中量感 | 秀丽·轻描淡写 | ⬜ 缺 |
| 12 | retro_80s | 80年代妆 | 浓淡皆可 | 中量感 | 直线 | ⬜ 缺 |
| 13 | cold_beauty | 清冷美人妆 | 淡颜系 | 中/小量感 | 冷感·静态 | ⬜ 缺 |
| 14 | tomboy_heroic | 英气少年妆 | 淡颜系 | 小量感 | 清爽·俊朗·英气 | ⬜ 缺 |
| 15 | red_carpet | 明星红毯妆 | 浓淡皆可 | 大/中量感 | 精致·气质·女性美 | ⬜ 缺 |
| 16 | american_plain_water | 美式白开水妆 | 浓颜系 | 大量感 | 华丽·张扬·低饱和 | ⬜ 缺 |
| 17 | western_glam | 欧美妆 | 浓颜系 | 大量感 | 张扬·精致华丽 | ⬜ 缺 |
| 18 | french_romantic | 法式浪漫妆 | 浓淡皆可 | 小/中量感 | 真实·自然 | ⬜ 缺 |
| 19 | thai_light | 轻泰妆 | 淡颜系 | 小/中量感 | 清透·质感·低饱和 | ⬜ 缺 |
| 20 | american_freckle | 美式慵懒雀斑妆 | 浓颜系 | 小量感 | 野性·酷 | ⬜ 缺 |

> ⚠️ #7「日杂妆」OCR 存疑，原文可能是「日杂妆」或「日系妆」，待确认。

## 4. 覆盖现状

- **确定覆盖**：2 / 20（韩式妆、亚裔妆）
- **近似覆盖**：1 / 20（白开水妆 ← 伪素颜视频）
- **待补**：17 / 20

「戴眼镜化妆」「上镜妆」等属于**场景/条件标签**，不是独立风格，不占本词表类目。

## 5. 用法

```python
from makeup_distiller import load_taxonomy

tax = load_taxonomy()
print(tax.version, f"{len(tax.styles)} 个风格")
for s in tax.styles:
    print(s.id, s.name, s.coverage, s.face_type, " ".join(s.essence))
```

成员 B 在产出 `DistillationResult` 时，`makeup_style` 应取本表 `name`（或 `id`），并尽量补 `suitable_features` 用本表三个属性轴取值。
