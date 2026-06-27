#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_edit.py — Obsession 一键修图脚本 / one-click tasteful photo editor

理念：后期是"让照片更接近当时的感受"，不是换一张照片。默认参数刻意保守，
做减法、不"一眼假"。所有强度都可调。

用法 / Usage:
  python3 auto_edit.py 输入图.jpg
  python3 auto_edit.py in.jpg -o out.jpg --shadows 0.10 --warmth -0.06 --vignette 0.12
  python3 auto_edit.py in.jpg --face 0.43,0.40 --darken 0.70,0.94 --darken 0.12,0.95
  python3 auto_edit.py in.jpg --auto-wb            # 自动白平衡(灰世界)
  python3 auto_edit.py in.jpg --no-compare         # 不生成对比图

输出 / Output:
  <name>_edited.jpg         全分辨率成品
  <name>_compare.jpg        原图/成品 左右对比(除非 --no-compare)

依赖: pillow, numpy
"""
import argparse, os, sys
import numpy as np
from PIL import Image, ImageOps, ImageFilter


def luma(a):
    return (0.2126*a[..., 0] + 0.7152*a[..., 1] + 0.114*a[..., 2])


def parse_xy(s):
    x, y = s.split(",")
    return float(x), float(y)


def radial(xx, yy, W, H, cx, cy, sx, sy):
    return np.exp(-(((xx-cx*W)/(sx*W))**2 + ((yy-cy*H)/(sy*H))**2)).astype(np.float32)


def main():
    ap = argparse.ArgumentParser(description="Obsession 一键修图")
    ap.add_argument("input")
    ap.add_argument("-o", "--output", default=None)
    ap.add_argument("--shadows", type=float, default=0.085,
                    help="提暗部强度 0~0.25 (默认0.085)")
    ap.add_argument("--highlights", type=float, default=0.05,
                    help="收高光强度 0~0.25 (默认0.05)")
    ap.add_argument("--contrast", type=float, default=1.05,
                    help="对比 1.0=不变 (默认1.05)")
    ap.add_argument("--warmth", type=float, default=-0.025,
                    help="色温:负=收暖变冷,正=加暖 -0.1~0.1 (默认-0.025)")
    ap.add_argument("--vibrance", type=float, default=0.06,
                    help="自然饱和度 0~0.3 (默认0.06,保护肤色)")
    ap.add_argument("--vignette", type=float, default=0.08,
                    help="暗角强度 0~0.3 (默认0.08)")
    ap.add_argument("--sharpen", type=float, default=0.4,
                    help="锐化量 0~1.5 (默认0.4,适量)")
    ap.add_argument("--auto-wb", action="store_true",
                    help="灰世界自动白平衡(温和)")
    ap.add_argument("--face", action="append", default=[],
                    metavar="cx,cy",
                    help="局部提亮中心(归一化0~1),可多次。提亮脸+收橘")
    ap.add_argument("--face-strength", type=float, default=0.12)
    ap.add_argument("--darken", action="append", default=[],
                    metavar="cx,cy",
                    help="局部压暗中心(归一化0~1),可多次。压干扰物")
    ap.add_argument("--darken-strength", type=float, default=0.30)
    ap.add_argument("--no-compare", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f"找不到文件: {args.input}")

    im = ImageOps.exif_transpose(Image.open(args.input)).convert("RGB")
    W, H = im.size
    arr = np.asarray(im).astype(np.float32) / 255.0
    log = []

    # 0. 自动白平衡(灰世界, 温和混合) ---------------------------------
    if args.auto_wb:
        means = arr.reshape(-1, 3).mean(0)
        g = means.mean()
        gain = np.clip(g / (means + 1e-5), 0.8, 1.2)
        wb = np.clip(arr * gain, 0, 1)
        arr = 0.6*wb + 0.4*arr          # 只校60%,避免矫枉过正
        log.append("自动白平衡(灰世界,60%)")

    # 1. 提暗部 / 收高光 --------------------------------------------
    L = luma(arr)[..., None]
    if args.shadows:
        arr = arr + args.shadows * np.clip(1-L, 0, 1)**2.2 * (1-arr)
        log.append(f"提暗部 {args.shadows:+.3f}")
    L = luma(arr)[..., None]
    if args.highlights:
        arr = arr - args.highlights * np.clip(L, 0, 1)**2.2 * arr
        log.append(f"收高光 -{args.highlights:.3f}")

    # 2. 对比(以0.5为支点) ------------------------------------------
    if args.contrast != 1.0:
        arr = (arr - 0.5) * args.contrast + 0.5
        log.append(f"对比 x{args.contrast:.2f}")

    # 3. 色温 -------------------------------------------------------
    if args.warmth:
        arr[..., 0] *= (1 + args.warmth)
        arr[..., 2] *= (1 - args.warmth)
        log.append(f"色温 {args.warmth:+.3f}")
    arr = np.clip(arr, 0, 1)

    # 4. 自然饱和度(vibrance: 对低饱和提得多,保护已高饱和与肤色) -------
    if args.vibrance:
        g = luma(arr)[..., None]
        sat = np.abs(arr - g).max(axis=2, keepdims=True)  # 当前饱和近似
        boost = args.vibrance * (1 - sat)                 # 越不饱和提越多
        arr = g + (arr - g) * (1 + boost)
        log.append(f"自然饱和度 {args.vibrance:+.3f}")
    arr = np.clip(arr, 0, 1)

    # 5. 局部提亮(脸) + 局部压暗(干扰) ------------------------------
    if args.face or args.darken:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        for s in args.face:
            cx, cy = parse_xy(s)
            m = radial(xx, yy, W, H, cx, cy, 0.085, 0.075)[..., None]
            arr = arr + args.face_strength * m * (1-arr)         # 提亮
            gray = luma(arr)[..., None]
            arr = arr*(1 - 0.16*m) + gray*(0.16*m)               # 收橘
            log.append(f"局部提亮@({cx},{cy})")
        for s in args.darken:
            cx, cy = parse_xy(s)
            m = radial(xx, yy, W, H, cx, cy, 0.20, 0.13)[..., None]
            arr = arr * (1 - args.darken_strength * m)
            log.append(f"局部压暗@({cx},{cy})")
    arr = np.clip(arr, 0, 1)

    # 6. 暗角 -------------------------------------------------------
    if args.vignette:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        cx, cy = 0.5*W, 0.47*H
        d = np.sqrt(((xx-cx)/(0.75*W))**2 + ((yy-cy)/(0.75*H))**2)
        vig = np.clip(1 - args.vignette*np.clip(d-0.55, 0, None)/0.45,
                      1-args.vignette, 1.0)[..., None]
        arr = arr * vig
        log.append(f"暗角 {args.vignette:.2f}")

    arr = np.nan_to_num(np.clip(arr, 0, 1))
    out = Image.fromarray((arr*255 + 0.5).astype(np.uint8))

    # 7. 锐化(最后, 适量) -------------------------------------------
    if args.sharpen:
        pct = int(np.clip(args.sharpen, 0, 1.5) * 100)
        out = out.filter(ImageFilter.UnsharpMask(radius=2.0, percent=pct, threshold=2))
        log.append(f"锐化 {args.sharpen:.2f}")

    base = os.path.splitext(args.input)[0]
    out_path = args.output or f"{base}_edited.jpg"
    out.save(out_path, quality=94)
    print("✅ 成品:", out_path)
    print("   处理:", " | ".join(log))

    if not args.no_compare:
        def small(p):
            c = p.copy(); c.thumbnail((1000, 1200)); return c
        a, b = small(im), small(out)
        gap = 24
        canvas = Image.new("RGB", (a.width+b.width+gap, max(a.height, b.height)),
                           (245, 245, 245))
        canvas.paste(a, (0, 0)); canvas.paste(b, (a.width+gap, 0))
        cmp_path = f"{base}_compare.jpg"
        canvas.save(cmp_path, quality=90)
        print("🔍 对比:", cmp_path, "(左原图 / 右成品)")

    # 过度提醒
    if (args.contrast > 1.25 or args.vibrance > 0.25 or args.shadows > 0.2
            or args.vignette > 0.25):
        print("⚠️  参数偏猛,小心'一眼假'。和原图对比若别人会问'P过头了吗',就往回收。")


if __name__ == "__main__":
    main()
