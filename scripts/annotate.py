#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
annotate.py — 构图/技术可视化标注 / draw composition & technical overlays

把客观检测画到图上，比纯文字更直观：三分线、人脸框、地平线倾斜参考线、
高光过曝斑马线(红)。用于教学和拍中复盘。

用法 / Usage:
  python3 annotate.py 照片.jpg                 # 输出 照片_annotated.jpg
  python3 annotate.py 照片.jpg -o out.jpg
  python3 annotate.py 照片.jpg --no-zebra --no-thirds   # 关掉某些图层
依赖：opencv-python(-headless) + pillow + numpy
"""
import argparse, os, sys
import numpy as np

try:
    import cv2
except ImportError:
    sys.exit("需要 opencv：pip install opencv-python-headless --break-system-packages")
from PIL import Image, ImageOps, ImageDraw

CASC = cv2.data.haarcascades
FACE = cv2.CascadeClassifier(CASC + "haarcascade_frontalface_default.xml")


def main():
    ap = argparse.ArgumentParser(description="构图/技术可视化标注")
    ap.add_argument("input")
    ap.add_argument("-o", "--output", default=None)
    ap.add_argument("--no-thirds", action="store_true", help="不画三分线")
    ap.add_argument("--no-faces", action="store_true", help="不画人脸框")
    ap.add_argument("--no-horizon", action="store_true", help="不画地平线参考")
    ap.add_argument("--no-zebra", action="store_true", help="不画过曝斑马线")
    args = ap.parse_args()
    if not os.path.exists(args.input):
        sys.exit(f"找不到文件: {args.input}")

    im = ImageOps.exif_transpose(Image.open(args.input)).convert("RGB")
    W, H = im.size
    # 工作尺寸(检测)；标注画在原图上
    sc = 1280/max(W, H)
    small = im.resize((int(W*sc), int(H*sc))) if sc < 1 else im
    gray = cv2.cvtColor(np.asarray(small), cv2.COLOR_RGB2GRAY)
    inv = (W/small.width)  # 小图坐标 → 原图坐标

    draw = ImageDraw.Draw(im, "RGBA")
    lw = max(2, W//500)

    # 过曝斑马线(红色半透明覆盖高光死白区)
    if not args.no_zebra:
        full_gray = np.asarray(im.convert("L"))
        mask = full_gray > 250
        if mask.any():
            overlay = np.zeros((H, W, 4), np.uint8)
            stripe = (np.add.outer(np.arange(H), np.arange(W)) // max(6, W//180)) % 2 == 0
            overlay[mask & stripe] = (255, 40, 40, 150)
            im.paste(Image.fromarray(overlay), (0, 0), Image.fromarray(overlay))
            draw = ImageDraw.Draw(im, "RGBA")  # 重建draw
            over_pct = 100*mask.mean()
            draw.text((lw*3, lw*3), f"OVEREXPOSED {over_pct:.1f}%",
                      fill=(255, 80, 80, 255))

    # 三分线
    if not args.no_thirds:
        c = (255, 255, 255, 120)
        for k in (1, 2):
            draw.line([(W*k/3, 0), (W*k/3, H)], fill=c, width=lw)
            draw.line([(0, H*k/3), (W, H*k/3)], fill=c, width=lw)
        for kx in (1, 2):
            for ky in (1, 2):
                x, y = W*kx/3, H*ky/3
                r = lw*3
                draw.ellipse([x-r, y-r, x+r, y+r], outline=(255, 255, 0, 200), width=lw)

    # 人脸框
    if not args.no_faces:
        faces = FACE.detectMultiScale(gray, 1.1, 5,
                                      minSize=(max(30, gray.shape[0]//25),)*2)
        for (x, y, w, h) in faces:
            box = [x*inv, y*inv, (x+w)*inv, (y+h)*inv]
            draw.rectangle(box, outline=(60, 220, 90, 255), width=lw)
        if len(faces):
            draw.text((lw*3, H-lw*10), f"FACES {len(faces)}", fill=(60, 220, 90, 255))

    # 地平线倾斜参考(检测近水平长线的中位角度)
    if not args.no_horizon:
        edges = cv2.Canny(gray, 60, 180)
        lines = cv2.HoughLines(edges, 1, np.pi/180,
                               threshold=max(120, gray.shape[1]//6))
        tilt = 0.0
        if lines is not None:
            angs = [np.degrees(l[0][1])-90 for l in lines[:60]
                    if abs(np.degrees(l[0][1])-90) < 20]
            if angs:
                tilt = float(np.median(angs))
        if abs(tilt) >= 1.0:
            import math
            cx, cy = W/2, H/2
            dx = math.cos(math.radians(tilt))*W
            dy = math.sin(math.radians(tilt))*W
            draw.line([(cx-dx/2, cy-dy/2), (cx+dx/2, cy+dy/2)],
                      fill=(80, 160, 255, 220), width=lw)
            draw.text((lw*3, lw*8), f"TILT {tilt:+.1f}deg", fill=(120, 180, 255, 255))

    out = args.output or os.path.splitext(args.input)[0] + "_annotated.jpg"
    im.save(out, quality=92)
    print("✅ 已标注:", out)
    print("   图层: 三分线(白+黄交点) · 人脸框(绿) · 地平线倾斜(蓝) · 过曝斑马(红)")


if __name__ == "__main__":
    main()
