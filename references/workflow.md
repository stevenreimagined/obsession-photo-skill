# 工作流向导 / Workflow Guide

这是把整套 skill 串起来的"地图"。新社员或不确定从哪开始时，先看这里：一次拍摄任务从头到尾该做什么、用哪个工具。**先判断用户在拍摄周期的哪个阶段**，再带他走对应步骤。

## 一次任务的完整流程

```
拍前 🅰 ── 定参数 ─────────────► recommend_settings.py / shooting_settings.md
        └─ 建目录结构 ─────────► organize.py scaffold（或 pipeline.py newshoot）

拍中 🅱 ── 现场问题诊断 ───────► troubleshooting.md
        ├─ 设置变灰/锁死 ──────► settings_locked.md
        └─ 构图当场检查 ───────► compose_check.py / annotate.py（可视化）

拍后 🅲 ── 导入+统一命名 ──────► organize.py rename
        ├─ 快速初检(找废片/坏文件)► triage.py
        ├─ 选片初筛+连拍最佳张 ──► cull.py
        ├─ 出可分享选片报告 ────► report.py
        ├─ 评图/点评+对标大师 ──► evaluation.md / master_matching.md
        └─ 后期修图 ──────────► editing.md / auto_edit.py
```

一键串联(可选)：
- 拍前：`python3 scripts/pipeline.py newshoot --name "Drama Festival" --date 2026-06-27`
- 拍后：`python3 scripts/pipeline.py postprocess 照片文件夹/` → 自动跑 初检→选片→HTML报告

## 新社员从哪开始 / Onramp

如果用户是刚入社的新人、不知道问什么，建议这样引导：

1. **先学会看**：发一张自己的照片来，按六维点评 + 对标大师，告诉他"好照片长什么样、差在哪"。
2. **再学会拍**：下次拍活动前，按场景查一份参数卡(`recommend_settings.py`)，并理解"为什么这么设"。
3. **现场会救场**：遇到偏色/脸暗/参数变灰，用 🅱 的诊断快速解决。
4. **最后学整理**：拍完用 `pipeline.py postprocess` 一键初检+选片+报告，再挑几张练后期。

不要一次把全部功能倒给新人——按他当前的任务，给当下最有用的那一两步。

## 配置 / Config

社团的默认值(缩写、机型、市电频率、阈值)集中在根目录 `config.yaml`，脚本会自动读取。改一次，全队统一。命令行参数仍可临时覆盖配置。

## 一条贯穿始终的原则

所有客观检测(清晰度、曝光、人脸、构图、睁闭眼…)都是**辅助**，用来把明显问题和最佳张快速挑出来；**审美、情绪、故事性和最终取舍，永远归摄影师**。脚本只建议、不替你删片、不替你定稿。
