#!/usr/bin/env python3
"""Process many recordings sequentially, then rebuild the cross-meeting corpus.

Sequential by design: Whisper runs on CPU and Ollama on GPU, but within one
meeting the steps are ordered, so meetings are processed one at a time. Already
-processed meetings (output/<name>/meeting.json present) are skipped, so the
batch is resumable after an interruption.

Usage:
  ./batch.py                          # every *.mp4 in ../recordings
  ./batch.py --limit 5                # first 5 by name
  ./batch.py "REC1.mp4" "REC2.mp4"    # specific files
  ./batch.py --vision-model gemma3:4b --text-model gemma3:4b   # faster
  ./batch.py --force                  # reprocess even if already done
"""
import argparse
import glob
import os
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REC = os.path.normpath(os.path.join(HERE, "..", "recordings"))
PY = os.path.join(HERE, ".venv", "bin", "python")


def main():
    ap = argparse.ArgumentParser(description="Batch-process meeting recordings.")
    ap.add_argument("files", nargs="*", help="specific recordings (default: all in ../recordings)")
    ap.add_argument("--limit", type=int, default=None, help="only the first N")
    ap.add_argument("--vision-model", default="gemma3:12b")
    ap.add_argument("--text-model", default="gemma3:12b")
    ap.add_argument("--beam", type=int, default=5, help="Whisper beam size (1 faster, 5 accurate)")
    ap.add_argument("--newest-first", action="store_true", help="process newest recordings first")
    ap.add_argument("--force", action="store_true", help="reprocess even if meeting.json exists")
    a = ap.parse_args()

    files = a.files or sorted(glob.glob(os.path.join(REC, "*.mp4")))
    if a.newest_first:
        files = list(reversed(files))
    if a.limit:
        files = files[:a.limit]
    print(f"== batch: {len(files)} recordings · vision={a.vision_model} · text={a.text_model}\n")

    ok, skipped, failed = 0, 0, []
    t_all = time.time()
    for i, f in enumerate(files, 1):
        name = os.path.splitext(os.path.basename(f))[0]
        done = os.path.join(HERE, "output", name, "meeting.json")
        if os.path.exists(done) and not a.force:
            print(f"[{i}/{len(files)}] skip (done): {name}")
            skipped += 1
            continue
        print(f"[{i}/{len(files)}] === {name} ===", flush=True)
        t = time.time()
        r = subprocess.run([PY, "-u", "process_meeting.py", f,
                            "--vision-model", a.vision_model,
                            "--text-model", a.text_model,
                            "--beam", str(a.beam)], cwd=HERE)
        if r.returncode == 0:
            ok += 1
            print(f"           done in {int(time.time() - t)}s\n")
        else:
            failed.append(name)
            print(f"           FAILED (exit {r.returncode})\n")

    print("== rebuilding corpus + todos ==")
    subprocess.run([PY, "corpus.py"], cwd=HERE)
    subprocess.run([PY, "todos.py"], cwd=HERE)
    mins = int((time.time() - t_all) / 60)
    print(f"\n== done in {mins} min: {ok} processed, {skipped} skipped, {len(failed)} failed")
    if failed:
        print("   failed:", ", ".join(failed))


if __name__ == "__main__":
    main()
