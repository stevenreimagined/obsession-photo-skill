# Obsession · 摄影看图 / 评图 / 修图助手

一个面向**摄影社新社员**的 Claude Skill。用温和、具体、可执行的方式，帮新社员看懂好照片、客观评估自己的作品、学会基础后期。中英双语，覆盖活动纪实、人像、风光建筑等题材。

A Claude Skill that mentors **new photography-club members** — helping them understand what makes a good photo, evaluate their own shots' quality and color, and learn basic post-processing. Bilingual (Chinese + English terms), covering documentary/event, portrait, and landscape/architecture.

## 功能 / What it does

1. **看懂好照片** — 用通俗语言讲解什么是好照片，对照摄影大师的标准与可模仿的技术。
2. **评估作品** — 发来一张照片，按"主体·构图·光线·曝光·色彩·瞬间"六维点评，给出拍摄分与颜色分，并指出**最该改的一件事**。
3. **后期指导** — 给出分步修图工作流(选片→裁剪→白平衡→曝光→调色→局部→锐化)和"问题→对应调整"对照表。

设计基调：先肯定、再点问题、只给一条最高优先级建议、**永不打击新社员信心**。

## 怎么用 / How to use

安装后，发给 Claude 一张照片，说：

- "帮我看看这张拍得怎么样" → 结构化点评
- "这张怎么修 / 后期怎么调" → 分步修图方向
- "什么样的照片算好照片" → 概念讲解 + 大师标准

## 结构 / Structure

```
obsession.skill/
├── SKILL.md                  # 主控:路由 + 评图输出结构 + 修图流程
└── references/
    ├── evaluation.md         # 六维评图框架 + 评分尺度 + 选片用法
    ├── masters.md            # 各题材摄影大师与可学技术
    ├── editing.md            # 7 步修图工作流 + 常见问题对照表
    └── benchmarks.md         # 各题材优秀照片文字标杆 + 社团作品库
```

## 安装 / Installation

将本仓库内容放入你的 Claude skills 目录(或在 Cowork / Claude Code 中作为 skill 加载)。`benchmarks.md` 末尾的"社团优秀作品库"一节可以随时追加你们社团自己的优秀样片特征，让评图标准越来越贴合本社审美。

## 致谢 / Notes

参考资料标尺采用**文字描述**而非内嵌图片，因此无版权风险、体积小、易维护。大师技术要点综合自公开的摄影教学资料。

## License

MIT — 见 [LICENSE](LICENSE)。
