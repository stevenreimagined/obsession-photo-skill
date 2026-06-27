#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cull.py — Obsession 选片初筛 + 连拍最佳张 / AI first-pass culling & best-of-burst

对一个文件夹里的照片做客观技术分析，给出建议分类——但**绝不自动删除**，
最终决定权永远在摄影师手里。

检测：清晰度/虚焦、严重过曝/欠曝、人脸数量与大小、疑似闭眼、构图(切边/过中心/
头顶空间/主体过小)、连拍相似分组并挑最佳张。

分类(四档)：
  推荐保留 KEEP  · 可选 OPT  · 建议淘汰 CULL  · 技术问题 TECH

用法 / Usage:
  python3 cull.py 文件夹/                       # 分析并输出报告
  python3 cull.py 文件夹/ -o 结果目录/           # 指定输出目录
  python3 cull.py 文件夹/ --blur 60 --burst 6   # 调阈值

输出：cull_report.csv(全部指标) + cull_contactsheet.jpg(彩框标注拼图) + 终端汇总
依赖：opencv-python(-headless), pillow, numpy
"""
import argparse, os, glob, csv, sys
import numpy as np
from PIL import Image, ImageOps, ImageDraw

try:
    import cv2
except ImportError:
    sys.exit("需要 opencv：pip install opencv-python-headless --break-system-packages")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eyestate import eye_states, available as eyes_available  # 基于EAR的睁闭眼

CASC = cv2.data.haarcascades
FACE = cv2.CascadeClassifier(CASC + "haarcascade_frontalface_default.xml")

EXTS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp")

# 分类的颜色(BGR->用RGB给PIL)与英文短标(拼图上用ASCII,避免中文乱码)
CAT = {
    "推荐保留": ("KEEP", (60, 180, 75)),
    "可选":     ("OPT",  (245, 200, 40)),
    "建议淘汰": ("CULL", (140, 140, 140)),
    "技术问题": ("TECH", (220, 50, 50)),
}


def load_cv(path, long_edge=1280, sharp_edge=2400):
    """按EXIF校正方向。返回:缩略图(检测/构图用) + 较高分辨率灰度(算清晰度用)。
    清晰度在 ~2400px 上分块算，缩太小会抹掉细节让好图糊图分不开。"""
    full = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    w, h = full.size
    # 清晰度专用：保留较多细节
    ssc = sharp_edge / max(w, h)
    sharp_im = full.resize((int(w*ssc), int(h*ssc))) if ssc < 1 else full
    sharp_gray = cv2.cvtColor(np.asarray(sharp_im), cv2.COLOR_RGB2GRAY)
    # 缩略图，用于人脸/曝光/构图
    sc = long_edge / max(w, h)
    im = full.resize((int(w*sc), int(h*sc))) if sc < 1 else full
    gray = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2GRAY)
    return im, gray, sharp_gray, (w, h)


def tiled_sharpness(gray, grid=5):
    """分块求清晰度，取第90百分位(=最清晰区域)。这样主体不在中心、
    或浅景深背景虚化的照片，也能凭它最锐利的部分得到正确评价。"""
    gh, gw = gray.shape
    th, tw = max(1, gh//grid), max(1, gw//grid)
    vs = []
    for i in range(grid):
        for j in range(grid):
            t = gray[i*th:(i+1)*th, j*tw:(j+1)*tw]
            if t.size:
                vs.append(cv2.Laplacian(t, cv2.CV_64F).var())
    return float(np.percentile(vs, 90)) if vs else 0.0


def dhash(gray, hs=8):
    """差值感知哈希，用于连拍相似分组"""
    small = cv2.resize(gray, (hs+1, hs))
    diff = small[:, 1:] > small[:, :-1]
    return diff.flatten()


def hamming(a, b):
    return int(np.count_nonzero(a != b))


def analyze(path, args):
    im, gray, sharp_gray, (W, H) = load_cv(path)
    rgb = np.asarray(im)
    gh, gw = gray.shape
    area = gh * gw
    r = {"file": os.path.basename(path)}

    # --- 清晰度 / 虚焦(分块取最清晰区域，避免主体不在中心被误判) ---
    lap = tiled_sharpness(sharp_gray)
    r["sharp"] = round(lap, 1)

    # --- 曝光 ---
    over = 100 * float((gray > 250).mean())
    under = 100 * float((gray < 6).mean())
    mean = float(gray.mean())
    r["over%"] = round(over, 1); r["under%"] = round(under, 1); r["mean"] = round(mean, 1)

    # --- 人脸 ---
    faces = FACE.detectMultiScale(gray, 1.1, 5, minSize=(max(30, gh//25),)*2)
    r["faces"] = len(faces)
    flags = []
    primary = None
    if len(faces):
        primary = max(faces, key=lambda f: f[2]*f[3])
        fx, fy, fw, fh = primary
        r["face%"] = round(100*(fw*fh)/area, 2)
        # 主体过小
        if (fw*fh)/area < 0.01:
            flags.append("subj-small")
        # 切边(脸贴近画面边缘)
        m = 3
        if fx <= m or fy <= m or fx+fw >= gw-m or fy+fh >= gh-m:
            flags.append("face-cut")
        # 头顶空间(脸上方留白占比)
        headroom = fy / gh
        if headroom > 0.35:
            flags.append("headroom+")
        # 过于居中
        cx = (fx+fw/2)/gw; cy = (fy+fh/2)/gh
        if abs(cx-0.5) < 0.08 and abs(cy-0.5) < 0.08:
            flags.append("centered")
    else:
        r["face%"] = 0.0

    # --- 闭眼：基于眼睛关键点(EAR)，只在确信时判定，否则记"未知" ---
    closed, opened, checked = eye_states(rgb)
    r["eyes_closed"] = closed
    r["eyes_checked"] = checked       # 0 = 无法判断(脸太小/侧脸/未装mediapipe)
    if closed > 0:
        flags.append("closed-eye")    # 有真实证据才标

    # --- 地平线倾斜(长直线角度) ---
    edges = cv2.Canny(gray, 60, 180)
    lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=max(120, gw//6))
    tilt = 0.0
    if lines is not None:
        angs = []
        for l in lines[:60]:
            theta = l[0][1]
            deg = np.degrees(theta) - 90      # 水平线≈0
            if abs(deg) < 20:                 # 只看近水平的线
                angs.append(deg)
        if angs:
            tilt = float(np.median(angs))
    r["tilt"] = round(tilt, 1)
    if abs(tilt) >= 2.0:
        flags.append("tilt")

    # --- 综合评分 0~100 ---
    sharp_n = np.clip((lap - args.blur) / (args.sharp_full - args.blur), 0, 1) * 45
    # 曝光惩罚：高光死白比欠曝更难救，惩罚更重
    exp_pen = min(over, 25)/25*22 + min(under, 50)/50*10
    exp_n = max(0, 28 - exp_pen)
    face_n = 0
    if len(faces):
        face_n = np.clip(r["face%"]/8, 0, 1) * 13
        if r.get("eyes_checked", 0) > 0 and r.get("eyes_closed", 0) == 0:
            face_n += 5   # 确信睁眼才加分
    comp_n = 14
    for bad, p in [("face-cut", 6), ("tilt", 3), ("centered", 2),
                   ("headroom+", 2), ("subj-small", 6)]:
        if bad in flags:
            comp_n -= p
    comp_n = max(0, comp_n)
    score = round(float(sharp_n + exp_n + face_n + comp_n), 1)
    r["score"] = score
    r["flags"] = ",".join(flags) if flags else ""

    # --- 分类 ---
    # 这些"较重"瑕疵会挡住"推荐保留"(降到可选)，但不会单凭它们判淘汰；
    # 居中/头顶/轻微倾斜只是小瑕疵。真正判"建议淘汰"看综合分。
    severe_flags = {"face-cut", "subj-small"}
    has_severe = bool(severe_flags & set(flags))
    blurred = lap < args.blur
    severe_exp = over > 25 or under > 45 or mean < 18 or mean > 240
    if blurred or severe_exp:
        cat = "技术问题"
        why = ("虚焦/糊 " if blurred else "") + ("严重过欠曝" if severe_exp else "")
    elif score < args.cull_below:
        cat = "建议淘汰"; why = "综合偏弱(清晰度/曝光/构图都一般)"
    elif "closed-eye" in flags:
        cat = "可选"; why = f"检测到闭眼({r['eyes_closed']}人)，建议人工确认"
    elif score >= args.keep_above and not has_severe:
        cat = "推荐保留"
        why = "清晰、曝光正常" + ("(有小瑕疵)" if flags else "，无明显问题")
    else:
        cat = "可选"
        why = "主体偏小/有小问题，可留作备选" if has_severe else "有小问题，可留作备选"
    r["cat"] = cat; r["why"] = why.strip()
    r["_thumb"] = im
    r["_hash"] = dhash(gray)
    return r


def group_bursts(rows, args):
    """按相似度分连拍组，组内挑最佳张(score最高)"""
    n = len(rows)
    gid = [-1]*n
    g = 0
    for i in range(n):
        if gid[i] != -1:
            continue
        gid[i] = g
        for j in range(i+1, n):
            if gid[j] == -1 and hamming(rows[i]["_hash"], rows[j]["_hash"]) <= args.burst:
                gid[j] = g
        g += 1
    for i, r in enumerate(rows):
        r["group"] = gid[i]
    # 每组挑最佳
    for grp in set(gid):
        members = [r for r in rows if r["group"] == grp]
        best = max(members, key=lambda r: r["score"])
        for r in members:
            r["best"] = (r is best) and len(members) > 1
            r["group_size"] = len(members)
    return rows


def contact_sheet(rows, out_path, cols=5):
    tw, th = 320, 320
    pad, label_h = 6, 40
    cellw, cellh = tw+pad*2, th+pad*2+label_h
    rowsN = (len(rows)+cols-1)//cols
    sheet = Image.new("RGB", (cols*cellw, rowsN*cellh), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    for i, r in enumerate(rows):
        tag, color = CAT[r["cat"]]
        im = r["_thumb"].copy(); im.thumbnail((tw, th))
        cx = (i % cols)*cellw; cy = (i//cols)*cellh
        # 彩色边框
        bx, by = cx+pad, cy+pad
        d.rectangle([bx-3, by-3, bx+im.width+2, by+im.height+2], outline=color, width=4)
        sheet.paste(im, (bx, by))
        # 标签
        ty = by+im.height+6
        star = "★" if r.get("best") else ""
        line1 = f"{tag} {r['score']:.0f} {star}"
        grp = f"burst#{r['group']}({r['group_size']})" if r.get("group_size", 1) > 1 else ""
        line2 = (r["flags"] or "ok")[:30]
        d.text((bx, ty), line1, fill=color)
        d.text((bx, ty+14), grp, fill=(170, 170, 170))
        d.text((bx, ty+26), line2, fill=(150, 150, 150))
        d.text((bx, by+2), r["file"][:22], fill=(255, 255, 255))
    sheet.save(out_path, quality=88)


def main():
    ap = argparse.ArgumentParser(description="选片初筛 + 连拍最佳张")
    ap.add_argument("folder")
    ap.add_argument("-o", "--outdir", default=None)
    ap.add_argument("--blur", type=float, default=90, help="虚焦阈值(分块清晰度第90百分位,越小越糊)")
    ap.add_argument("--sharp-full", type=float, default=700, help="清晰满分参考")
    ap.add_argument("--keep-above", type=float, default=60, help="推荐保留分数线")
    ap.add_argument("--cull-below", type=float, default=38, help="建议淘汰分数线")
    ap.add_argument("--burst", type=int, default=8, help="连拍相似度(汉明距离≤即同组)")
    ap.add_argument("--cols", type=int, default=5)
    args = ap.parse_args()

    if not os.path.isdir(args.folder):
        sys.exit(f"不是文件夹: {args.folder}")
    files = [f for f in sorted(glob.glob(os.path.join(args.folder, "*")))
             if f.lower().endswith(EXTS)
             and not os.path.basename(f).startswith("._")
             and not os.path.basename(f).startswith("cull_")]  # 排除自身输出
    if not files:
        sys.exit("文件夹里没有找到图片")
    outdir = args.outdir or args.folder
    os.makedirs(outdir, exist_ok=True)

    print(f"分析 {len(files)} 张照片…")
    rows = []
    for k, f in enumerate(files, 1):
        try:
            rows.append(analyze(f, args))
        except Exception as e:
            print(f"  跳过 {os.path.basename(f)}: {e}")
        if k % 10 == 0:
            print(f"  …{k}/{len(files)}")
    rows = group_bursts(rows, args)

    # CSV
    csv_path = os.path.join(outdir, "cull_report.csv")
    cols = ["file", "cat", "score", "why", "sharp", "over%", "under%", "mean",
            "faces", "face%", "eyes_closed", "eyes_checked", "tilt", "flags",
            "group", "group_size", "best"]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # 拼图
    sheet_path = os.path.join(outdir, "cull_contactsheet.jpg")
    contact_sheet(rows, sheet_path, cols=args.cols)

    # 汇总
    from collections import Counter
    c = Counter(r["cat"] for r in rows)
    bursts = sum(1 for r in rows if r.get("group_size", 1) > 1)
    print("\n" + "="*46)
    print("选片初筛结果(仅建议，最终由你决定)")
    print("="*46)
    for cat in ["推荐保留", "可选", "建议淘汰", "技术问题"]:
        print(f"  {cat:6s}: {c.get(cat,0):3d} 张")
    nb = len(set(r['group'] for r in rows if r.get('group_size',1)>1))
    print(f"  连拍组  : {nb} 组(共 {bursts} 张，已标 ★ 最佳张)")
    print(f"\n📄 明细: {csv_path}")
    print(f"🖼  标注拼图: {sheet_path}  (绿=保留 黄=可选 灰=淘汰 红=技术问题, ★=连拍最佳)")
    print("\n⚠️ 这是技术初筛，不替代你的眼睛——表情/情绪/故事性请人工复核。"
          "脚本只是帮你先把明显废片和最佳张挑出来。")


if __name__ == "__main__":
    main()
