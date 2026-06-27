#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exif_info.py — Obsession EXIF 参数教学脚本 / read EXIF & teach

读取一张照片的拍摄参数(快门/光圈/ISO/焦距/相机镜头),并生成"为什么这组参数
拍出这个效果"的通俗教学解读，帮新社员学会看参数。

用法 / Usage:
  python3 exif_info.py 照片.jpg
  python3 exif_info.py 文件夹/            # 批量,输出每张一行 + 参数

依赖: pillow
"""
import sys, os, glob
from fractions import Fraction
from PIL import Image, ExifTags

TAGS = {v: k for k, v in ExifTags.TAGS.items()}  # name -> id


def get(exif, name):
    return exif.get(TAGS.get(name, -1))


def fmt_shutter(v):
    try:
        v = float(v)
    except Exception:
        return None
    if v <= 0:
        return None
    if v >= 1:
        return f"{v:.1f}s"
    return f"1/{round(1/v)}s"


def read(path):
    im = Image.open(path)
    exif = im.getexif()
    # 部分参数在 ExifIFD 子目录
    try:
        sub = exif.get_ifd(0x8769)
        merged = dict(exif); merged.update(sub)
    except Exception:
        merged = dict(exif)

    def g(name):
        return merged.get(TAGS.get(name, -1))

    data = {
        "相机 Camera": f"{g('Make') or ''} {g('Model') or ''}".strip() or None,
        "镜头 Lens": g("LensModel"),
        "快门 Shutter": fmt_shutter(g("ExposureTime")),
        "光圈 Aperture": (f"f/{float(g('FNumber')):.1f}" if g("FNumber") else None),
        "ISO": g("ISOSpeedRatings") or g("PhotographicSensitivity"),
        "焦距 Focal": (f"{float(g('FocalLength')):.0f}mm" if g("FocalLength") else None),
        "等效35mm": (f"{int(g('FocalLengthIn35mmFilm'))}mm"
                    if g("FocalLengthIn35mmFilm") else None),
        "曝光补偿 EV": (f"{float(g('ExposureBiasValue')):+.1f}"
                      if g("ExposureBiasValue") not in (None, 0) else None),
        "拍摄时间 Date": g("DateTimeOriginal") or g("DateTime"),
        "尺寸 Size": f"{im.size[0]}x{im.size[1]}",
    }
    return data, merged


def teach(data, merged):
    """根据参数生成教学解读"""
    notes = []

    def g(name):
        return merged.get(TAGS.get(name, -1))

    # 快门
    st = g("ExposureTime")
    if st:
        st = float(st)
        if st >= 1/60 and st < 1:
            notes.append(f"快门 {fmt_shutter(st)} 偏慢——拍静物/夜景可以，但拍动作容易糊，"
                         "手持低于约 1/(焦距) 秒要小心抖动。")
        elif st >= 1:
            notes.append(f"快门 {fmt_shutter(st)} 是长曝光——必须三脚架，常用于流水/光轨/星空。")
        elif st <= 1/500:
            notes.append(f"快门 {fmt_shutter(st)} 很快——能凝固跳跃、奔跑、泼水等瞬间，"
                         "适合运动/抓拍。")
        else:
            notes.append(f"快门 {fmt_shutter(st)} 适中——日常抓拍、活动纪实的常用区间。")
    # 光圈
    fn = g("FNumber")
    if fn:
        fn = float(fn)
        if fn <= 2.8:
            notes.append(f"光圈 f/{fn:.1f} 很大——背景虚化强、进光多，适合人像/暗光；"
                         "但景深浅，对焦要准(人像对眼睛)。")
        elif fn >= 8:
            notes.append(f"光圈 f/{fn:.1f} 较小——景深大、全画面实，适合风光/建筑/合影。")
        else:
            notes.append(f"光圈 f/{fn:.1f} 中等——通用，兼顾虚化与清晰。")
    # ISO
    iso = g("ISOSpeedRatings") or g("PhotographicSensitivity")
    if iso:
        try:
            iso = int(iso)
            if iso >= 3200:
                notes.append(f"ISO {iso} 偏高——说明现场较暗，注意噪点；"
                             "纪实片可容忍一些噪点，后期适度降噪即可。")
            elif iso <= 200:
                notes.append(f"ISO {iso} 很低——光线充足，画质最干净。")
            else:
                notes.append(f"ISO {iso} 适中——画质与亮度的平衡区间。")
        except Exception:
            pass
    # 焦距
    fl = g("FocalLengthIn35mmFilm") or (
        float(g("FocalLength")) if g("FocalLength") else None)
    if fl:
        fl = float(fl)
        if fl <= 35:
            notes.append(f"等效约 {fl:.0f}mm 广角——视野宽、有纵深和现场感，"
                         "纪实/活动/风光常用('离得近'用广角更有代入感)。")
        elif fl >= 85:
            notes.append(f"等效约 {fl:.0f}mm 中长焦——压缩感强、能远距离抓特写，"
                         "适合人像和不打扰被摄者的抓拍。")
        else:
            notes.append(f"等效约 {fl:.0f}mm 标准——接近人眼视角，最自然百搭。")
    # 曝光补偿
    ev = g("ExposureBiasValue")
    if ev not in (None, 0):
        try:
            ev = float(ev)
            d = "减(压暗)" if ev < 0 else "加(提亮)"
            notes.append(f"曝光补偿 {ev:+.1f} EV——拍摄时主动{d}，"
                         "说明摄影者在控制明暗，不是全交给相机。")
        except Exception:
            pass

    if not notes:
        notes.append("这张没读到完整的拍摄参数(可能被导出/截图/微信压缩抹掉了 EXIF)。")
    return notes


def main():
    if len(sys.argv) < 2:
        sys.exit("用法: python3 exif_info.py 照片.jpg | 文件夹/")
    target = sys.argv[1]
    if os.path.isdir(target):
        files = [f for f in sorted(glob.glob(os.path.join(target, "*")))
                 if f.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff"))
                 and not os.path.basename(f).startswith("._")]
        for f in files:
            try:
                data, _ = read(f)
                line = " · ".join(f"{v}" for k, v in data.items()
                                  if k in ("快门 Shutter", "光圈 Aperture", "ISO",
                                           "焦距 Focal") and v)
                print(f"{os.path.basename(f):40s} {line or '无EXIF'}")
            except Exception as e:
                print(f"{os.path.basename(f)}  读取失败: {e}")
        return

    data, merged = read(target)
    print("="*48)
    print("📷 拍摄参数 / EXIF —", os.path.basename(target))
    print("="*48)
    for k, v in data.items():
        if v:
            print(f"  {k:14s}: {v}")
    print("-"*48)
    print("🎓 参数解读 / What these settings mean")
    print("-"*48)
    for n in teach(data, merged):
        print(" •", n)


if __name__ == "__main__":
    main()
