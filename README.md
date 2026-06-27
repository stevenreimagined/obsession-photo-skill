# Obsession · 摄影看图 / 评图 / 修图助手

一个面向**摄影社新社员**的 Claude Skill。用温和、具体、可执行的方式，帮新社员看懂好照片、客观评估自己的作品、学会基础后期。中英双语，覆盖活动纪实、人像、风光建筑等题材。

A Claude Skill that mentors **new photography-club members** — helping them understand what makes a good photo, evaluate their own shots' quality and color, and learn basic post-processing. Bilingual (Chinese + English terms), covering documentary/event, portrait, and landscape/architecture.

## 功能 / What it does

覆盖一次拍摄任务的**全流程：拍前 → 拍中 → 拍后**。

**🅰 拍前**

1. **场景参数推荐** — 给出场景+机型(如室内篮球/FX30)，输出快门/光圈/ISO/白平衡/对焦/连拍/格式/视频帧率/Picture Profile/防频闪一整套参数，**并解释为什么**。

**🅱 拍中**

2. **现场问题诊断** — 描述问题(偏黄/脸暗/LED条纹/失焦)，按"最可能原因→立即操作→下一步"给方案。
2b. **设置变灰诊断** — 某参数"不能调/变灰/开不了"(快门/ISO/眼控/触控追踪)时，定位是哪个模式锁住的(S&Q/Cine EI/高帧率/曝光模式/代理录制)并给解锁步骤。
3. **构图/技术检测** — 脚本检测地平线倾斜、人脸切边、主体过中心/过小、头顶空间、高光过曝、主体脱焦、疑似闭眼、背景杂乱。

**🅲 拍后**

4. **评图** — 按"主体·构图·光线·曝光·色彩·瞬间"六维点评，给拍摄分/颜色分 + 最该改的一件事 + 对标大师。
5. **EXIF 参数教学** — 读取并解读拍摄参数。
6. **一键修图** — 按标准工作流自动处理，参数可调、默认保守，自动出原图/成品对比。
7. **批量选片初筛 + 连拍最佳张** — 把整个文件夹分成 推荐保留/可选/建议淘汰/技术问题，连拍分组挑★最佳张，输出 CSV + 彩框标注拼图。**只建议、不自动删除**。
8. **建文件夹 + 统一命名** — 按活动一键生成标准目录(RAW/Video/Audio/Selects/Edit/Export/Delivery)，并批量统一命名(默认预览，确认后执行)。
9. **快速素材初检** — 导完素材先扫一遍，只标技术问题(失焦/抖动/过曝/损坏/合照闭眼/连拍重复/视频无音轨/片段过短/时间断点)，输出定位报告。**只标记、不删除**。
10. **可视化标注 + HTML 选片报告** — 把检测画到图上(三分线/人脸框/地平线/过曝斑马)；选片结果一键出可分享的 HTML 报告(可打印成 PDF)。
11. **一键流水线 + 配置化** — `pipeline.py` 把初检→选片→报告串成一条命令；社团默认值集中在 `config.yaml`，改一次全队统一。

设计基调：先肯定、再点问题、只给一条最高优先级建议、客观工具只做辅助、**最终决定权永远在摄影师**。

## 怎么用 / How to use

安装后，发给 Claude 一张照片，说：

- "帮我看看这张拍得怎么样" → 结构化点评
- "这张怎么修 / 后期怎么调" → 分步修图方向
- "什么样的照片算好照片" → 概念讲解 + 大师标准

## 结构 / Structure

```
obsession.skill/
├── SKILL.md                  # 主控:三阶段路由 + 评图/修图流程 + 工具用法
├── config.yaml               # 社团默认值(缩写/机型/频率/阈值/水印,可选)
├── evals/                    # 触发测试集 + 覆盖核查
├── references/
│   ├── workflow.md           # 工作流地图 + 新社员引导
│   ├── shooting_settings.md  # 🅰 拍前参数方法论 + 场景预设 + 防频闪 + 机型说明
│   ├── troubleshooting.md    # 🅱 现场问题诊断(原因→操作→下一步)
│   ├── settings_locked.md    # 🅱 设置变灰/锁死诊断(S&Q/Cine EI/高帧率等)
│   ├── evaluation.md         # 🅲 六维评图框架 + 评分尺度 + 选片用法
│   ├── masters.md            # 各题材摄影大师与可学技术
│   ├── master_matching.md    # 🅲 对标大师的匹配方法与话术
│   ├── editing.md            # 🅲 7 步修图工作流 + 常见问题对照表
│   └── benchmarks.md         # 各题材优秀照片文字标杆 + 社团作品库
└── scripts/
    ├── recommend_settings.py # 🅰 场景→整套参数(带解释)
    ├── exif_info.py          # 🅲 读取并解读拍摄参数
    ├── auto_edit.py          # 🅲 一键修图(可调参数 + 自动对比图)
    ├── compose_check.py      # 🅱 单张构图/技术检测
    ├── annotate.py           # 🅱 检测结果可视化(三分线/人脸框/地平线/斑马)
    ├── cull.py               # 🅲 批量选片初筛 + 连拍最佳张
    ├── report.py             # 🅲 由cull结果生成HTML选片报告
    ├── organize.py           # 🅰/🅲 建标准目录结构 + 统一命名
    ├── triage.py             # 🅲 快速素材初检(只标问题,不删除)
    ├── pipeline.py           # 一键流水线(newshoot / postprocess)
    ├── eyestate.py           # 睁闭眼判断模块(EAR,被调用)
    └── _config.py            # 读取 config.yaml(被调用)
```

依赖：`pip install opencv-python-headless pillow numpy mediapipe pyyaml --break-system-packages`
（参数/命名/EXIF 类只需标准库或 pillow；图像分析脚本需 opencv+numpy；**睁闭眼需 mediapipe(可选)**——没装则标"无法判断"；视频初检需系统 `ffmpeg/ffprobe`；`config.yaml` 需 pyyaml(没装则用内置默认值)）。用法见 SKILL.md 的"工具脚本"一节。

## 安装 / Installation

将本仓库内容放入你的 Claude skills 目录(或在 Cowork / Claude Code 中作为 skill 加载)。`benchmarks.md` 末尾的"社团优秀作品库"一节可以随时追加你们社团自己的优秀样片特征，让评图标准越来越贴合本社审美。

## 致谢 / Notes

参考资料标尺采用**文字描述**而非内嵌图片，因此无版权风险、体积小、易维护。大师技术要点综合自公开的摄影教学资料。

## License

MIT — 见 [LICENSE](LICENSE)。
