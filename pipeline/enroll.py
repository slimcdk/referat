#!/usr/bin/env python3
"""Save enrolled voiceprints.

Name the prepared clips from enroll_prepare.py:
    <torch-venv> enroll.py enroll_clips 00=Christian 01=Thomas

...or enroll directly from a clean single-speaker clip:
    <torch-venv> enroll.py --clip Christian sample.wav
"""
import json
import os
import sys

from diar_common import diarize, load_voiceprints, save_voiceprints


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return
    vps = load_voiceprints()
    if a[0] == "--clip":
        name, wav = a[1], a[2]
        _, label_emb, dur = diarize(wav)
        dom = max(dur, key=dur.get)
        vps[name] = label_emb[dom].tolist()
        print(f"enrolled {name} (fra dominerende taler i {os.path.basename(wav)})")
    else:
        clipdir = a[0]
        pending = json.load(open(os.path.join(clipdir, "pending.json")))
        by_id = {lab.split("_")[-1]: lab for lab in pending}
        for pair in a[1:]:
            sid, name = pair.split("=", 1)
            lab = by_id.get(sid, "SPEAKER_" + sid)
            vps[name] = pending[lab]["embedding"]
            print(f"enrolled {name} <- {lab}")
    save_voiceprints(vps)
    print("voiceprints:", ", ".join(vps))


if __name__ == "__main__":
    main()
