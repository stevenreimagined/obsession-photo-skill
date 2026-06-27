#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
organize.py — Obsession 项目目录脚手架 + 统一命名 / project scaffold & batch rename

多人拍摄、后期协作时，统一的文件夹结构和文件名能省掉大量沟通成本。

两个子命令：
  scaffold  按活动生成标准目录结构
  rename    把一批素材改成统一文件名(默认只预览，加 --apply 才真正执行)

用法 / Usage:
  # 1) 建目录结构
  python3 organize.py scaffold --name "Drama Festival" --date 2026-06-27 \
         --cameras A B C -o ~/拍摄

  # 2) 统一命名(先预览)
  python3 organize.py rename 某文件夹/ --prefix OAO --event "Drama Festival" \
         --date 20260627 --camera A
  # 确认无误后真正执行：
  python3 organize.py rename 某文件夹/ --prefix OAO --event "Drama Festival" \
         --camera A --apply
  # 或复制到目标目录而不动原文件：
  python3 organize.py rename 某文件夹/ --prefix OAO --event Drama --camera A \
         --copy 目标目录/ --apply

依赖：无(纯标准库)
"""
import argparse, os, sys, shutil, datetime, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _config import cfg  # 读取 config.yaml 默认值(可选)

# 标准目录结构(参考影视/活动拍摄通用规范)
SUBDIRS = [
    "01_RAW_Photo",     # 下面再按机位分 Camera_X
    "02_RAW_Video",
    "03_Audio",
    "04_Selects",       # 选片
    "05_Edit",          # 后期工程
    "06_Export",        # 导出成片
    "07_Delivery",      # 交付(发给对方的成品)
]

MEDIA_EXTS = (".arw", ".cr2", ".cr3", ".nef", ".raf", ".rw2", ".dng", ".orf",
              ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic",
              ".mp4", ".mov", ".avi", ".mkv", ".wav", ".mp3", ".m4a")


def clean(s):
    """活动名转驼峰无空格：'Drama Festival' -> 'DramaFestival'"""
    parts = re.split(r"[\s_\-]+", s.strip())
    return "".join(p[:1].upper()+p[1:] for p in parts if p)


def scaffold(args):
    date = args.date or datetime.date.today().isoformat()
    folder = f"{date}_{clean(args.name)}"
    root = os.path.join(args.outdir, folder)
    made = []
    for sub in SUBDIRS:
        p = os.path.join(root, sub)
        os.makedirs(p, exist_ok=True); made.append(sub)
        if sub == "01_RAW_Photo":
            for cam in args.cameras:
                os.makedirs(os.path.join(p, f"Camera_{cam}"), exist_ok=True)
    # 打印结构
    print(f"✅ 已创建项目目录：{root}\n")
    print(f"{folder}/")
    for sub in SUBDIRS:
        print(f"├── {sub}")
        if sub == "01_RAW_Photo":
            for i, cam in enumerate(args.cameras):
                branch = "└──" if i == len(args.cameras)-1 else "├──"
                print(f"│   {branch} Camera_{cam}")
    print("\n命名建议：导入素材后用 `organize.py rename` 统一命名，例如")
    print(f"  {args.prefix}_{clean(args.name)}_{date.replace('-','')}_A_0001.ARW")


def file_date(path, default):
    """优先用 EXIF 拍摄时间，否则文件修改时间，格式 YYYYMMDD"""
    try:
        from PIL import Image
        ex = Image.open(path).getexif()
        dt = ex.get(36867) or ex.get(306)  # DateTimeOriginal / DateTime
        if dt:
            return dt[:10].replace(":", "").replace("-", "")
    except Exception:
        pass
    try:
        return datetime.datetime.fromtimestamp(
            os.path.getmtime(path)).strftime("%Y%m%d")
    except Exception:
        return default


def rename(args):
    if not os.path.isdir(args.folder):
        sys.exit(f"不是文件夹: {args.folder}")
    files = [f for f in sorted(os.listdir(args.folder))
             if f.lower().endswith(MEDIA_EXTS) and not f.startswith("._")]
    if not files:
        sys.exit("没有找到素材文件")
    if args.by == "time":
        files.sort(key=lambda f: os.path.getmtime(os.path.join(args.folder, f)))

    today = datetime.date.today().strftime("%Y%m%d")
    event = clean(args.event)
    dest = args.copy or args.folder
    if args.copy:
        os.makedirs(dest, exist_ok=True)

    plan = []
    seq = args.start
    for f in files:
        src = os.path.join(args.folder, f)
        ext = os.path.splitext(f)[1]
        date = (args.date if args.date and args.date != "AUTO"
                else file_date(src, today) if args.date == "AUTO" else (args.date or today))
        newname = f"{args.prefix}_{event}_{date}_{args.camera}_{seq:04d}{ext}"
        plan.append((f, newname))
        seq += 1

    print(f"{'预览(未执行)' if not args.apply else '执行'}  共 {len(plan)} 个文件"
          f"{' → 复制到 '+dest if args.copy else ''}")
    for old, new in plan[:8]:
        print(f"  {old}  →  {new}")
    if len(plan) > 8:
        print(f"  …(其余 {len(plan)-8} 个同理)")

    if not args.apply:
        print("\n这是预览。确认无误后加 --apply 真正执行"
              f"{'(将复制到目标目录)' if args.copy else '(将原地重命名)'}。")
        return
    # 执行
    for old, new in plan:
        s = os.path.join(args.folder, old)
        d = os.path.join(dest, new)
        if args.copy:
            shutil.copy2(s, d)
        else:
            os.rename(s, d)
    print(f"\n✅ 完成：{len(plan)} 个文件已{'复制并' if args.copy else ''}重命名。")


def main():
    ap = argparse.ArgumentParser(description="项目目录脚手架 + 统一命名")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scaffold", help="生成标准目录结构")
    s.add_argument("--name", required=True, help="活动名，如 'Drama Festival'")
    s.add_argument("--date", default=None, help="YYYY-MM-DD，默认今天")
    s.add_argument("--cameras", nargs="+", default=["A", "B", "C"], help="机位代号")
    s.add_argument("--prefix", default=cfg("club", "prefix", "OAO"), help="文件名前缀(组织缩写),默认读config.yaml")
    s.add_argument("-o", "--outdir", default=".", help="在哪个目录下创建")
    s.set_defaults(func=scaffold)

    r = sub.add_parser("rename", help="批量统一命名")
    r.add_argument("folder")
    r.add_argument("--prefix", default=cfg("club", "prefix", "OAO"), help="前缀(组织缩写),默认读config.yaml")
    r.add_argument("--event", required=True, help="活动名")
    r.add_argument("--date", default=None,
                   help="YYYYMMDD；填 AUTO 则按每个文件的拍摄/修改时间；默认今天")
    r.add_argument("--camera", default="A", help="机位代号")
    r.add_argument("--start", type=int, default=1, help="起始序号")
    r.add_argument("--by", choices=["name", "time"], default="name",
                   help="排序依据：文件名 或 拍摄时间")
    r.add_argument("--copy", default=None, metavar="DEST",
                   help="复制到该目录而非原地改名(更安全)")
    r.add_argument("--apply", action="store_true", help="真正执行(否则只预览)")
    r.set_defaults(func=rename)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
