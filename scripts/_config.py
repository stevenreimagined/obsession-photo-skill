#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_config.py — 读取 config.yaml 的小工具（被各脚本调用）

设计：配置**完全可选**。找不到 config.yaml 或没装 pyyaml，就用内置默认值，
不影响任何脚本运行。命令行参数永远优先于配置文件。

用法：
  from _config import cfg
  cfg("club", "prefix", "OAO")        # 取 club.prefix，缺省 "OAO"
  cfg("cull", "blur", 60)
"""
import os

DEFAULTS = {
    "club": {"prefix": "OAO", "default_camera": None, "region": 50,
             "watermark_text": ""},
    "cull": {"blur": 90, "sharp_full": 700, "keep_above": 60,
             "cull_below": 38, "burst": 8},
    "triage": {"blur": 70, "over": 15, "burst": 8, "burst_min": 4, "minvid": 2.0},
    "eyes": {"ear_thresh": 0.15},
}

_loaded = None


def _find_config():
    """从脚本目录与当前目录向上找 config.yaml。"""
    here = os.path.dirname(os.path.abspath(__file__))
    for base in (here, os.path.dirname(here), os.getcwd()):
        p = os.path.join(base, "config.yaml")
        if os.path.exists(p):
            return p
    return None


def load():
    global _loaded
    if _loaded is not None:
        return _loaded
    data = {k: dict(v) for k, v in DEFAULTS.items()}
    path = _find_config()
    if path:
        try:
            import yaml
            with open(path, encoding="utf-8") as f:
                user = yaml.safe_load(f) or {}
            for sec, vals in user.items():
                if isinstance(vals, dict):
                    data.setdefault(sec, {}).update(
                        {k: v for k, v in vals.items() if v is not None})
                else:
                    data[sec] = vals
        except Exception:
            pass   # 解析失败就用默认值，绝不让配置拖垮主流程
    _loaded = data
    return data


def cfg(section, key, default=None):
    d = load().get(section, {})
    v = d.get(key, default)
    return default if v is None else v
