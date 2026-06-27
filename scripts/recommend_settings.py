#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
recommend_settings.py — Obsession 拍前参数推荐 / pre-shoot settings advisor

按场景输出整套相机参数 + 解释 + 现场提醒。这是确定性的"参数卡"生成器；
更细的取舍和机型差异见 references/shooting_settings.md，让 AI 结合现场补充。

用法 / Usage:
  python3 recommend_settings.py --scene basketball --camera FX30 --light low
  python3 recommend_settings.py --list                 # 列出所有场景
  python3 recommend_settings.py --scene stage --region 50

场景 scene: basketball stage lecture outdoor group portrait lowlight banquet
依赖: 无(纯标准库)
"""
import argparse, sys

# 每个场景的参数预设。值是起点，脚本会按 light/region 微调。
SCENES = {
    "basketball": {
        "name": "室内运动 / 篮球",
        "strategy": "快门优先保证动作清晰——运动模糊救不回，噪点能后期降。",
        "shutter": "1/500 s 以上", "shutter_why": "凝固跳跃、快攻的瞬间",
        "aperture": "尽可能最大(f/2.8)", "aperture_why": "多进光、压低 ISO",
        "iso": "Auto ISO，上限 12800", "iso_why": "把亮度波动交给相机，保动作",
        "wb": "手动设色温(约 4500K)", "wb_why": "避免画面连续变色",
        "af": "AF-C + 人物/眼部识别", "af_why": "跟住移动球员",
        "burst": "Hi+", "burst_why": "一串里挑动作最完整的一张",
        "fmt": "RAW", "fmt_why": "暗光下暗部宽容度更好",
        "video": "50p(50Hz)/60p(60Hz)，180°快门", "pp": "S-Cinetone 直出 / S-Log3 调色",
    },
    "stage": {
        "name": "舞台演出 / 晚会(追光高反差)",
        "strategy": "按追光下的人脸测光，宁欠勿过保住高光；快门跟住走动。",
        "shutter": "1/250 s 起(静态独舞可1/160)", "shutter_why": "演员走动不糊",
        "aperture": "尽量最大(f/2.8)", "aperture_why": "进光、虚化杂乱背景",
        "iso": "Auto ISO，上限 12800", "iso_why": "暗场够亮，接受可控噪点",
        "wb": "手动(舞台暖光 3200–3800K)", "wb_why": "别让 AWB 被暖光带偏",
        "af": "AF-C + 眼部识别，对焦区域中等", "af_why": "避免追焦跑到背景",
        "burst": "Hi", "burst_why": "抓表情与动作峰值",
        "fmt": "RAW", "fmt_why": "高反差需要宽容度救暗部",
        "video": "25p/50p，180°快门", "pp": "S-Log3(留调色空间)",
    },
    "lecture": {
        "name": "室内活动 / 讲座 / 会议",
        "strategy": "稳住人物手势的清晰度，控制噪点，颜色统一。",
        "shutter": "1/160–1/250 s", "shutter_why": "讲话手势不糊",
        "aperture": "f/2.8–f/4", "aperture_why": "虚化杂乱会场、突出讲者",
        "iso": "Auto ISO，上限 6400", "iso_why": "室内中等光，画质够干净",
        "wb": "手动(暖光 3800–4500K)", "wb_why": "会议室混合光易偏色",
        "af": "AF-C + 眼部识别", "af_why": "讲者小幅走动也跟得住",
        "burst": "中速连拍", "burst_why": "抓自然表情",
        "fmt": "RAW+JPEG", "fmt_why": "快出图 + 保留后期余地",
        "video": "25p/50p，180°快门", "pp": "标准/S-Cinetone 直出",
    },
    "outdoor": {
        "name": "室外活动 / 运动会(白天)",
        "strategy": "光线充足，快门拉高抓动作，ISO 压低保画质。",
        "shutter": "动作 1/1000 s / 常规 1/500 s", "shutter_why": "户外动作锐利",
        "aperture": "f/4–f/5.6", "aperture_why": "留点景深方便抓拍",
        "iso": "Auto ISO，上限 1600", "iso_why": "白天够用，画质最佳",
        "wb": "晴天 5400K / 阴天 6500K", "wb_why": "按天气定，或手动",
        "af": "AF-C + 人物识别", "af_why": "跟住跑动的人",
        "burst": "Hi+", "burst_why": "连拍挑峰值动作",
        "fmt": "RAW+JPEG", "fmt_why": "快出图 + 后期余地",
        "video": "25p/50p 或 100p+ 升格", "pp": "S-Cinetone / HLG",
    },
    "group": {
        "name": "合影 / 团体",
        "strategy": "前后排都要实，多拍几张防闭眼。",
        "shutter": "1/200 s 以上", "shutter_why": "防个别人晃动",
        "aperture": "f/5.6–f/8", "aperture_why": "景深够，前后排都清晰",
        "iso": "尽量低(100–400)", "iso_why": "画质最干净",
        "wb": "按光线手动", "wb_why": "肤色统一",
        "af": "AF-S，对焦第一排人脸", "af_why": "把焦平面放在人群前段",
        "burst": "低速连拍", "burst_why": "多张里选都睁眼的一张",
        "fmt": "RAW+JPEG", "fmt_why": "保肤色与后期空间",
        "video": "—", "pp": "—",
    },
    "portrait": {
        "name": "人像 / 采访",
        "strategy": "大光圈虚化 + 眼睛必须实。",
        "shutter": "1/200 s(配合焦距)", "shutter_why": "防抖、防轻微移动",
        "aperture": "大光圈 f/1.4–f/2.8", "aperture_why": "背景虚化、突出人物",
        "iso": "尽量低", "iso_why": "肤质干净",
        "wb": "手动，保肤色准确", "wb_why": "肤色是人像成败关键",
        "af": "AF-C + 眼部识别", "af_why": "焦点死死咬住眼睛",
        "burst": "单张/低速", "burst_why": "抓自然表情",
        "fmt": "RAW", "fmt_why": "肤色与影调精修",
        "video": "25p/50p，180°快门", "pp": "S-Cinetone / S-Log3",
    },
    "banquet": {
        "name": "室内宴会 / 颁奖(混合光)",
        "strategy": "混合光控色温，快门保人物，闪灯可选。",
        "shutter": "1/160 s", "shutter_why": "敬酒、走动不糊",
        "aperture": "f/2.8–f/4", "aperture_why": "进光 + 适度虚化",
        "iso": "Auto ISO，上限 6400", "iso_why": "宴会厅偏暗",
        "wb": "手动(暖光 3500–4200K)", "wb_why": "宴会暖光重，AWB 会乱",
        "af": "AF-C + 眼部识别", "af_why": "跟住走动的人",
        "burst": "中速", "burst_why": "抓敬酒/颁奖瞬间",
        "fmt": "RAW+JPEG", "fmt_why": "救色温与暗部",
        "video": "25p/50p", "pp": "标准/S-Cinetone",
    },
    "lowlight": {
        "name": "暗光 / 夜景活动",
        "strategy": "保住最低安全快门，宁可高 ISO 也别让主体糊。",
        "shutter": "不低于 1/125 s", "shutter_why": "运动模糊比噪点更难救",
        "aperture": "最大", "aperture_why": "尽量多进光",
        "iso": "Auto ISO，上限 12800–25600", "iso_why": "接受噪点换清晰",
        "wb": "手动", "wb_why": "夜景混合光易偏色",
        "af": "AF-C + 眼部识别 + 对焦辅助", "af_why": "暗光对焦难，找高对比边缘",
        "burst": "中速", "burst_why": "多张挑最稳的",
        "fmt": "RAW", "fmt_why": "暗部提亮空间",
        "video": "25p/50p，必要时降快门", "pp": "S-Log3",
    },
}

FLICKER = {50: "1/50、1/100 s(及整数倍)", 60: "1/60、1/120 s(及整数倍)"}


def adjust_for_light(s, light):
    s = dict(s)
    if light == "low":
        s["iso"] += "（光线差，可再上调上限一档）"
        s["shutter"] += "（太暗时优先降快门，别只拉 ISO）"
    elif light == "good":
        s["iso"] = s["iso"].replace("12800", "6400").replace("25600", "12800")
        s["iso"] += "（光线好，上限可下调保画质）"
    return s


def main():
    ap = argparse.ArgumentParser(description="拍前参数推荐")
    ap.add_argument("--scene", help="场景名，见 --list")
    ap.add_argument("--camera", default=None, help="机型，如 FX30 / α7IV / R6")
    ap.add_argument("--light", choices=["low", "normal", "good"], default="normal")
    ap.add_argument("--region", type=int, choices=[50, 60], default=50,
                    help="市电频率：中国/欧洲=50，北美/日东=60")
    ap.add_argument("--list", action="store_true", help="列出场景")
    args = ap.parse_args()

    if args.list or not args.scene:
        print("可用场景 / scenes:")
        for k, v in SCENES.items():
            print(f"  {k:12s} {v['name']}")
        if not args.scene:
            return
    if args.scene not in SCENES:
        sys.exit(f"未知场景: {args.scene}（用 --list 查看）")

    s = adjust_for_light(SCENES[args.scene], args.light)
    cam = args.camera or "通用"
    light_cn = {"low": "灯光一般/偏暗", "normal": "光线正常", "good": "光线充足"}[args.light]

    print("="*52)
    print(f"🎬 场景：{s['name']} · {cam} · {light_cn}")
    print("="*52)
    print(f"策略：{s['strategy']}\n")
    rows = [
        ("快门", s["shutter"], s["shutter_why"]),
        ("光圈", s["aperture"], s["aperture_why"]),
        ("ISO", s["iso"], s["iso_why"]),
        ("白平衡", s["wb"], s["wb_why"]),
        ("对焦", s["af"], s["af_why"]),
        ("连拍", s["burst"], s["burst_why"]),
        ("格式", s["fmt"], s["fmt_why"]),
    ]
    if s.get("video") and s["video"] != "—":
        rows.append(("视频帧率", s["video"], "按市电频率减少闪烁"))
        rows.append(("Picture Profile", s["pp"], "调色用Log/快出片用直出风格"))
    for k, v, why in rows:
        print(f"· {k}：{v}")
        print(f"    └ {why}")

    # 防频闪
    print(f"· 防频闪：{args.region}Hz 安全快门 {FLICKER[args.region]}")
    if args.camera and args.camera.upper().startswith("FX"):
        print("    └ FX 系列为电子快门、无机械快门 → 没有'防闪烁拍摄'，"
              "只能靠选对快门速度避 LED 条纹")
    else:
        print("    └ 有机械快门的机型可直接开'防闪烁拍摄(Anti-flicker)'")

    print("\n⚠️ 现场提醒：")
    print("  · 先对一次白平衡基准(对中性灰/白)，整场色调才统一。")
    print("  · ISO 频繁顶到上限 = 光线不够，优先降快门(到安全下限)而不是无限拉 ISO。")
    print("  · 数值是起点，开拍后看回放直方图微调，保住高光不死白。")
    print("\n（更细的取舍与你机型的菜单叫法，见 references/shooting_settings.md）")


if __name__ == "__main__":
    main()
