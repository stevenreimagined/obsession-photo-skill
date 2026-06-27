#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
triage.py — Obsession 快速素材初检 / fast media triage

不是完整选片，只做**技术层面的初步标记**，帮摄影师快速定位问题素材。
**只标记，绝不删除**——最终判断永远在人。

照片检测：文件损坏、可能失焦/抖动、高光大面积溢出、合照有人闭眼、连拍重复过多。
视频检测(需 ffprobe)：文件无法读取、没有音频轨道、片段异常短。
另：扫描素材时间戳，提示明显不连续的时间断点。

输出：贴近人话的定位报告，例如
  · 第124–138号为同一组高速连拍(15张)，其中第131号最清晰，其余可作备份。
  · 第402号 可能严重失焦/抖动。
  · 视频 C0032.MP4 无可识别音频轨道。

用法 / Usage:
  python3 triage.py 素材文件夹/
  python3 triage.py 素材文件夹/ --csv 报告.csv      # 另存明细CSV
依赖：opencv-python(-headless)+pillow+numpy；视频检测需系统 ffprobe；
      闭眼判断需 mediapipe(可选)。RAW 需 rawpy(可选)，缺失则跳过其技术检测。
"""
import argparse, os, sys, glob, json, subprocess, datetime, csv as csvmod
import numpy as np

try:
    import cv2
except ImportError:
    sys.exit("需要 opencv：pip install opencv-python-headless --break-system-packages")
from PIL import Image, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from eyestate import eye_states
except Exception:
    def eye_states(_rgb):
        return 0, 0, 0
from _config import cfg  # 读取 config.yaml 默认值(可选)

CASC = cv2.data.haarcascades
FACE = cv2.CascadeClassifier(CASC + "haarcascade_frontalface_default.xml")

PHOTO = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".webp")
RAW = (".arw", ".cr2", ".cr3", ".nef", ".raf", ".rw2", ".dng", ".orf")
VIDEO = (".mp4", ".mov", ".avi", ".mkv", ".m4v")


def tiled_sharp(gray, grid=5):
    gh, gw = gray.shape; th, tw = max(1, gh//grid), max(1, gw//grid)
    vs = [cv2.Laplacian(gray[i*th:(i+1)*th, j*tw:(j+1)*tw], cv2.CV_64F).var()
          for i in range(grid) for j in range(grid)]
    return float(np.percentile(vs, 90)) if vs else 0.0


def dhash(gray, hs=8):
    small = cv2.resize(gray, (hs+1, hs))
    return (small[:, 1:] > small[:, :-1]).flatten()


def ham(a, b):
    return int(np.count_nonzero(a != b))


def capture_time(path):
    try:
        ex = Image.open(path).getexif()
        dt = ex.get(36867) or ex.get(306)
        if dt:
            return datetime.datetime.strptime(dt[:19], "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    try:
        return datetime.datetime.fromtimestamp(os.path.getmtime(path))
    except Exception:
        return None


def probe_video(path):
    """用 ffprobe 取时长与音频轨道。返回 dict 或 None(无法读取)。"""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", path],
            capture_output=True, text=True, timeout=30)
        data = json.loads(out.stdout)
        dur = float(data.get("format", {}).get("duration", 0) or 0)
        has_audio = any(s.get("codec_type") == "audio"
                        for s in data.get("streams", []))
        return {"duration": dur, "audio": has_audio}
    except Exception:
        return None


def analyze_photo(path, args):
    r = {"file": os.path.basename(path), "kind": "photo", "issues": [], "sharp": "",
         "hash": None, "time": capture_time(path)}
    ext = os.path.splitext(path)[1].lower()
    # 损坏 / RAW 解码
    try:
        im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        im.load()
    except Exception:
        if ext in RAW:
            r["issues"].append("RAW未解码(跳过技术检测)")
            return r
        r["issues"].append("文件损坏/无法打开")
        return r
    w, h = im.size
    sc = 1600/max(w, h)
    work = im.resize((int(w*sc), int(h*sc))) if sc < 1 else im
    rgb = np.asarray(work)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    # 清晰度
    s = tiled_sharp(gray); r["sharp"] = round(s, 1)
    if s < args.blur:
        r["issues"].append("可能失焦/抖动")
    # 高光溢出
    over = 100*float((gray > 250).mean())
    if over > args.over:
        r["issues"].append(f"高光大面积溢出({over:.0f}%)")
    # 合照闭眼
    faces = FACE.detectMultiScale(gray, 1.1, 5, minSize=(max(30, gray.shape[0]//25),)*2)
    if len(faces) >= 2:
        closed, _o, checked = eye_states(rgb)
        if closed > 0:
            r["issues"].append(f"合照疑似有人闭眼({closed}人)")
    # 连拍哈希
    r["hash"] = dhash(cv2.resize(gray, (320, 240)))
    return r


def analyze_video(path, args):
    r = {"file": os.path.basename(path), "kind": "video", "issues": [],
         "sharp": "", "hash": None, "time": capture_time(path)}
    info = probe_video(path)
    if info is None:
        r["issues"].append("视频无法读取/可能损坏")
        return r
    if not info["audio"]:
        r["issues"].append("无可识别音频轨道")
    if 0 < info["duration"] < args.minvid:
        r["issues"].append(f"片段异常短({info['duration']:.1f}s)")
    return r


def main():
    ap = argparse.ArgumentParser(description="快速素材初检(只标记不删除)")
    ap.add_argument("folder")
    ap.add_argument("--blur", type=float, default=cfg("triage", "blur", 70), help="失焦阈值(分块清晰度,越小越糊)")
    ap.add_argument("--over", type=float, default=cfg("triage", "over", 15), help="高光溢出占比阈值(%)")
    ap.add_argument("--burst", type=int, default=cfg("triage", "burst", 8), help="连拍相似度(汉明距离≤即同组)")
    ap.add_argument("--burst-min", type=int, default=cfg("triage", "burst_min", 4), help="多少张以上才提示'重复过多'")
    ap.add_argument("--minvid", type=float, default=cfg("triage", "minvid", 2.0), help="视频最短秒数")
    ap.add_argument("--gap", type=float, default=30, help="时间断点提示阈值(分钟)")
    ap.add_argument("--csv", default=None, help="另存明细CSV")
    args = ap.parse_args()

    if not os.path.isdir(args.folder):
        sys.exit(f"不是文件夹: {args.folder}")
    files = [f for f in sorted(glob.glob(os.path.join(args.folder, "*")))
             if f.lower().endswith(PHOTO+RAW+VIDEO)
             and not os.path.basename(f).startswith("._")]
    if not files:
        sys.exit("没有找到素材")

    print(f"初检 {len(files)} 个素材…(只标记，不删除)")
    rows = []
    for k, f in enumerate(files, 1):
        ext = os.path.splitext(f)[1].lower()
        r = analyze_video(f, args) if ext in VIDEO else analyze_photo(f, args)
        r["idx"] = k
        rows.append(r)
        if k % 20 == 0:
            print(f"  …{k}/{len(files)}")

    # 连拍分组(仅照片，有hash的)
    photos = [r for r in rows if r["hash"] is not None]
    gid = {}
    g = 0
    for i, ri in enumerate(photos):
        if ri["file"] in gid:
            continue
        gid[ri["file"]] = g
        for rj in photos[i+1:]:
            if rj["file"] not in gid and ham(ri["hash"], rj["hash"]) <= args.burst:
                gid[rj["file"]] = g
        g += 1
    groups = {}
    for r in photos:
        groups.setdefault(gid[r["file"]], []).append(r)

    # ---------- 生成定位报告 ----------
    print("\n" + "="*52)
    print("📋 快速初检报告 / Triage (仅技术标记，最终由你决定)")
    print("="*52)

    # 连拍重复过多
    burst_lines = []
    for grp, mem in groups.items():
        if len(mem) >= args.burst_min:
            mem_sorted = sorted(mem, key=lambda r: r["idx"])
            idxs = [m["idx"] for m in mem_sorted]
            best = max(mem, key=lambda r: (r["sharp"] or 0))
            burst_lines.append(
                f"  · 第{idxs[0]}–{idxs[-1]}号为同一组连拍({len(mem)}张)，"
                f"其中第{best['idx']}号({best['file']})最清晰，其余可作备份。")
    if burst_lines:
        print("\n【连拍分组】")
        for l in burst_lines:
            print(l)

    # 问题素材
    problem = [r for r in rows if r["issues"]
               and not (len(r["issues"]) == 0)]
    # 把"连拍内重复"不算问题；只列真正的技术问题
    prob_lines = []
    for r in problem:
        prob_lines.append(f"  · 第{r['idx']}号 {r['file']}：{('；'.join(r['issues']))}")
    if prob_lines:
        print("\n【需要注意的素材】")
        for l in prob_lines:
            print(l)
    else:
        print("\n【需要注意的素材】无明显技术问题 👍")

    # 时间断点
    timed = [r for r in rows if r["time"]]
    timed.sort(key=lambda r: r["time"])
    gaps = []
    for a, b in zip(timed, timed[1:]):
        dt = (b["time"]-a["time"]).total_seconds()/60
        if dt >= args.gap:
            gaps.append(f"  · 第{a['idx']}号之后到第{b['idx']}号之间间隔 {dt:.0f} 分钟"
                        f"(可能是不同场次/机器时间未同步)。")
    if gaps:
        print("\n【时间戳不连续】")
        for l in gaps[:8]:
            print(l)

    # 汇总
    n_prob = len(prob_lines)
    n_burstframes = sum(len(m) for m in groups.values() if len(m) >= args.burst_min)
    print("\n" + "-"*52)
    print(f"共 {len(files)} 个素材：{n_prob} 个有技术问题待复核，"
          f"{len([g for g in groups.values() if len(g)>=args.burst_min])} 组连拍"
          f"(含 {n_burstframes} 张)。")
    print("⚠️ 这是技术初筛，不替代人工选片；表情/情绪/构图请你定夺。")

    # CSV
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8-sig") as fp:
            w = csvmod.writer(fp)
            w.writerow(["idx", "file", "kind", "sharp", "burst_group", "issues"])
            for r in rows:
                w.writerow([r["idx"], r["file"], r["kind"], r["sharp"],
                            gid.get(r["file"], ""), " / ".join(r["issues"])])
        print(f"\n📄 明细CSV：{args.csv}")


if __name__ == "__main__":
    main()
