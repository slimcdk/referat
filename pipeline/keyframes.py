#!/usr/bin/env python3
"""Extract keyframes from a meeting recording.

Two sources, merged:
  1. a periodic sample every `interval` seconds -- so a visually static meeting
     (a fixed Teams view / one unchanging shared screen) still gets snapshots;
  2. ffmpeg scene-change detection -- slide flips, screen-share switches.

Frames are downscaled, timestamped, de-duplicated by a minimum gap, and capped.
Output: keyframes/frame_XXXX.png and keyframes/index.json.
"""
import argparse
import json
import os
import re
import subprocess


def _ffmpeg(args):
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args], check=False)


def _scale_vf(width):
    # rgb24 + PNG is robust; mjpeg/JPEG chokes on some captures' full-range YUV.
    return f"scale='min({width},iw)':-2,format=rgb24"


def extract(video, outdir, scene_threshold=0.25, interval=75, min_gap=8.0,
            max_frames=60, width=896):
    kfdir = os.path.join(outdir, "keyframes")
    os.makedirs(kfdir, exist_ok=True)
    for f in os.listdir(kfdir):  # clean slate
        if f.endswith(".png"):
            os.remove(os.path.join(kfdir, f))

    pairs = []  # (filename, seconds)

    # 1) periodic sample every `interval` seconds (i-th frame ~ i*interval)
    _ffmpeg(["-i", video, "-vf", f"fps=1/{interval},{_scale_vf(width)}",
             os.path.join(kfdir, "int_%05d.png")])
    for i, f in enumerate(sorted(x for x in os.listdir(kfdir) if x.startswith("int_"))):
        pairs.append((f, float(i * interval)))

    # 2) scene-change frames (+ timestamps via metadata=print)
    meta = os.path.join(outdir, "_scene_meta.txt")
    if os.path.exists(meta):
        os.remove(meta)
    _ffmpeg(["-i", video, "-vf",
             f"select='gt(scene,{scene_threshold})',metadata=print:file={meta},{_scale_vf(width)}",
             "-fps_mode", "vfr", os.path.join(kfdir, "raw_%05d.png")])
    times = []
    if os.path.exists(meta):
        for line in open(meta):
            m = re.search(r"pts_time:([0-9.]+)", line)
            if m:
                times.append(float(m.group(1)))
    raw = sorted(x for x in os.listdir(kfdir) if x.startswith("raw_"))
    pairs += list(zip(raw, times)) if len(times) == len(raw) else \
        [(f, i * min_gap) for i, f in enumerate(raw)]

    # 3) always a t=0 baseline
    base = "base_00000.png"
    _ffmpeg(["-ss", "0", "-i", video, "-frames:v", "1", "-vf", _scale_vf(width),
             os.path.join(kfdir, base)])
    if os.path.exists(os.path.join(kfdir, base)):
        pairs.append((base, 0.0))

    # merge: sort by time, enforce min gap, cap count
    kept, last = [], -1e9
    for f, t in sorted(pairs, key=lambda x: x[1]):
        if t - last >= min_gap:
            kept.append((f, t))
            last = t
    if len(kept) > max_frames:
        step = len(kept) / max_frames
        kept = [kept[int(i * step)] for i in range(max_frames)]

    index = []
    for i, (f, t) in enumerate(kept):
        dst = f"frame_{i:04d}.png"
        os.replace(os.path.join(kfdir, f), os.path.join(kfdir, dst))
        index.append({"i": i, "t": round(t, 2), "file": dst})

    for f in os.listdir(kfdir):  # remove unkept int_/raw_/base_ leftovers
        if f.startswith(("raw_", "int_", "base_")):
            os.remove(os.path.join(kfdir, f))
    if os.path.exists(meta):
        os.remove(meta)

    json.dump(index, open(os.path.join(kfdir, "index.json"), "w"), indent=2)
    return index


def main():
    ap = argparse.ArgumentParser(description="Extract keyframes (periodic + scene-change).")
    ap.add_argument("video")
    ap.add_argument("-o", "--outdir", default=".")
    ap.add_argument("--scene", type=float, default=0.25, help="scene-change threshold 0..1")
    ap.add_argument("--interval", type=float, default=75, help="periodic sample every N seconds")
    ap.add_argument("--min-gap", type=float, default=8.0, help="min seconds between kept frames")
    ap.add_argument("--max-frames", type=int, default=60)
    a = ap.parse_args()
    idx = extract(a.video, a.outdir, a.scene, a.interval, a.min_gap, a.max_frames)
    print(f"{len(idx)} keyframes -> {os.path.join(a.outdir, 'keyframes')}")


if __name__ == "__main__":
    main()
