#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
eyestate.py — 基于面部关键点的睁/闭眼判断 (eye open/closed via EAR)

原则(重要)：闭眼**只在拿到真实眼睛关键点、算出眼睛纵横比(EAR)确实很低时**才判定。
拿不到关键点(脸太小/侧脸/遮挡/没装 mediapipe)→ 返回"未知"，绝不靠"没检测到眼睛"
反推闭眼。这样避免对没有清晰人脸的照片误报闭眼。

用 mediapipe FaceMesh(若可用)。没装 mediapipe 时所有结果为"未知"，不影响主流程。

接口：
  eye_states(rgb_uint8) -> (closed, open_, checked)
     closed  : EAR 低于阈值的脸数(确信闭眼)
     open_   : EAR 正常的脸数(确信睁眼)
     checked : 成功取到眼睛关键点的脸数；0 = 无法判断(不要据此下结论)
"""
import os, math
os.environ.setdefault("GLOG_minloglevel", "3")   # 压制 mediapipe 日志

# 左右眼的 6 个关键点(mediapipe FaceMesh 468 点索引)
_L = [33, 160, 158, 133, 153, 144]
_R = [263, 387, 385, 362, 380, 373]

_mesh = None
_unavailable = False


def _get_mesh():
    """惰性创建并复用一个 FaceMesh 实例；不可用时返回 None。"""
    global _mesh, _unavailable
    if _unavailable:
        return None
    if _mesh is None:
        try:
            import warnings
            warnings.filterwarnings("ignore")
            import mediapipe as mp
            _mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=True, max_num_faces=12,
                refine_landmarks=True, min_detection_confidence=0.4)
        except Exception:
            _unavailable = True
            return None
    return _mesh


def _ear(lm, idx, w, h):
    p = [(lm[i].x*w, lm[i].y*h) for i in idx]
    d = lambda a, b: math.dist(a, b)
    return (d(p[1], p[5]) + d(p[2], p[4])) / (2*d(p[0], p[3]) + 1e-6)


def available():
    return _get_mesh() is not None


def eye_states(rgb, ear_thresh=0.15):
    """对整张图判断各人脸睁/闭眼。返回 (closed, open_, checked)。"""
    mesh = _get_mesh()
    if mesh is None:
        return 0, 0, 0
    h, w = rgb.shape[:2]
    try:
        res = mesh.process(rgb)
    except Exception:
        return 0, 0, 0
    if not res.multi_face_landmarks:
        return 0, 0, 0
    closed = open_ = 0
    for f in res.multi_face_landmarks:
        e = (_ear(f.landmark, _L, w, h) + _ear(f.landmark, _R, w, h)) / 2
        if e < ear_thresh:
            closed += 1
        else:
            open_ += 1
    return closed, open_, closed + open_
