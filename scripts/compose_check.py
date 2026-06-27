#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compose_check.py — Obsession 构图/技术即时检测 / composition & technical checker

对单张照片做客观检测并给出"提醒清单"，模拟实时构图助手：
地平线倾斜、人脸切边、主体过于居中、头顶空间过多、主体过小、高光过曝、
主体疑似脱焦、疑似闭眼、背景偏杂乱。

用法 / Usage:
  python3 compose_check.py 照片.jpg

输出：终端提醒清单(✅通过 / ⚠️提醒)。
依赖：opencv-python(-headless), pillow, numpy
"""
import sys, os
import numpy as np
from PIL import Image, ImageOps

try:
    import cv2
except ImportError:
    sys.exit("需要 opencv：pip install opencv-python-headless --break-system-packages")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eyestate import eye_states  # 基于EAR的睁闭眼(只在确信时判定)

CASC = cv2.data.haarcascades
FACE = cv2.CascadeClassifier(CASC + "haarcascade_frontalface_default.xml")


def main():
    if len(sys.argv) < 2:
        sys.exit("用法: python3 compose_check.py 照片.jpg")
    path = sys.argv[1]
    if not os.path.exists(path):
        sys.exit(f"找不到文件: {path}")

    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    w, h = im.size
    sc = 1280/max(w, h)
    if sc < 1:
        im = im.resize((int(w*sc), int(h*sc)))
    rgb = np.asarray(im)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    gh, gw = gray.shape
    area = gh*gw

    out = []  # (ok, 文本)

    # 高光过曝
    over = 100*float((gray > 250).mean())
    under = 100*float((gray < 6).mean())
    if over > 8:
        out.append((False, f"高光过曝：约 {over:.1f}% 像素死白——减曝光/收高光，看直方图别贴右边。"))
    else:
        out.append((True, "高光正常，无明显死白。"))
    if under > 35:
        out.append((False, f"暗部过多：约 {under:.1f}% 死黑——欠曝或对比过强，可提亮阴影。"))

    # 地平线倾斜
    edges = cv2.Canny(gray, 60, 180)
    lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=max(120, gw//6))
    tilt = 0.0
    if lines is not None:
        angs = [np.degrees(l[0][1])-90 for l in lines[:60]
                if abs(np.degrees(l[0][1])-90) < 20]
        if angs:
            tilt = float(np.median(angs))
    if abs(tilt) >= 2:
        out.append((False, f"画面倾斜：约 {tilt:+.1f}°——把地平线/竖线摆正(后期或重拍)。"))
    else:
        out.append((True, "水平基本正(无明显倾斜)。"))

    # 人脸相关
    faces = FACE.detectMultiScale(gray, 1.1, 5, minSize=(max(30, gh//25),)*2)
    if len(faces):
        primary = max(faces, key=lambda f: f[2]*f[3])
        fx, fy, fw, fh = primary
        facepct = 100*(fw*fh)/area
        cx = (fx+fw/2)/gw; cy = (fy+fh/2)/gh

        # 切边
        m = 3
        if fx <= m or fy <= m or fx+fw >= gw-m or fy+fh >= gh-m:
            out.append((False, "人脸贴边/可能被切——给主体留出完整空间。"))
        else:
            out.append((True, "人脸未被切边。"))

        # 主体过小
        if facepct < 1.0:
            out.append((False, f"主体偏小(脸仅占 {facepct:.1f}%)——靠近些或用长焦放大主体。"))
        else:
            out.append((True, f"主体大小合适(脸占 {facepct:.1f}%)。"))

        # 过于居中
        if abs(cx-0.5) < 0.08 and abs(cy-0.5) < 0.08:
            out.append((False, "主体过于居中——试试三分法，把主体放交点更有张力。"))
        else:
            out.append((True, "主体不在死中心，构图有呼吸。"))

        # 头顶空间
        if cy < 0.5 and fy/gh > 0.35:
            out.append((False, f"头顶空间偏多(上方约 {100*fy/gh:.0f}%)——下压相机或裁掉多余天空。"))

        # 主体是否脱焦(脸区清晰度 vs 全图)
        roi = gray[fy:fy+fh, fx:fx+fw]
        if roi.size:
            face_sharp = cv2.Laplacian(roi, cv2.CV_64F).var()
            all_sharp = cv2.Laplacian(gray, cv2.CV_64F).var()
            if all_sharp > 0 and face_sharp < 0.5*all_sharp:
                out.append((False, "主体疑似没对上焦(脸比背景还糊)——对焦点对到眼睛/用眼部识别。"))
            else:
                out.append((True, "主体清晰度正常。"))

        # 闭眼：基于眼睛关键点(EAR)，只在确信时提醒；判断不了就如实说"未知"
        closed, opened, checked = eye_states(rgb)
        if checked == 0:
            out.append((True, "眼睛状态无法判断(脸太小/侧脸/未装mediapipe)——跳过，不臆断。"))
        elif closed > 0:
            out.append((False, f"检测到闭眼({closed}人)——回放确认，必要时重拍。"))
        else:
            out.append((True, f"眼睛是睁开的({opened}人)。"))

        # 背景杂乱(主体外区域的边缘密度)
        mask = np.ones_like(gray, bool)
        mask[max(0,fy-10):fy+fh+10, max(0,fx-10):fx+fw+10] = False
        bg_edge = float(edges[mask].mean())/255*100
        if bg_edge > 12:
            out.append((False, f"背景偏杂乱(边缘密度 {bg_edge:.0f})——换干净背景/大光圈虚化/换机位。"))
        else:
            out.append((True, "背景较干净。"))
    else:
        out.append((True, "未检测到人脸(风光/物体题材，跳过人物相关项)。"))

    # 输出
    print("="*50)
    print("📐 构图 / 技术即时检测 —", os.path.basename(path))
    print("="*50)
    warns = [t for ok, t in out if not ok]
    for ok, t in out:
        print(("  ✅ " if ok else "  ⚠️  ") + t)
    print("-"*50)
    if warns:
        print(f"共 {len(warns)} 条提醒。优先处理：{warns[0]}")
    else:
        print("没有检出明显问题，构图/技术基础扎实 👍")
    print("\n(客观检测仅供参考，最终以你的创作意图为准；规则是起点不是铁律)")


if __name__ == "__main__":
    main()
