#!/usr/bin/env python3
"""Describe each keyframe with an Ollama vision model (Qwen2.5-VL by default).

For every keyframe we ask the model to (a) describe what is shown and (b) read
back the important on-screen text verbatim (slides, documents, code, chat) --
i.e. OCR + scene description in one call. Output: visuals.json and visuals.md.
"""
import argparse
import io
import json
import os
import time

import ollama
from PIL import Image

PROMPT = (
    "Skaermbillede fra et online moede (skaermdeling og/eller webcams). "
    "Gengiv den vigtigste synlige tekst - overskrifter, afsender og emne i e-mails, "
    "navne, datoer, URLer, slide-tekst og tal - og beskriv kort hvad der vises og "
    "hvilket program. Skriv det som flydende dansk tekst i 2-4 saetninger, uden "
    "punktopstilling eller nummerering. Spring almindelige browser- og UI-knapper over. "
    "Hvis skaermen er tom eller uklar, saa skriv blot det. "
    "Ingen indledning, og gentag ikke denne instruktion."
)


def _text(r):
    return r["response"] if isinstance(r, dict) else r.response


def _mmss(t):
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


def _prep_image(path, max_width):
    """Downscale + re-encode so the vision model's image tokens stay small
    enough to fit a 6 GB GPU -- Qwen2.5-VL memory scales with input resolution,
    and full 1280px+ frames push even the 3B model onto the CPU."""
    img = Image.open(path).convert("RGB")
    if img.width > max_width:
        h = int(img.height * max_width / img.width)
        img = img.resize((max_width, h), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def describe(outdir, model="gemma3:4b", prompt=PROMPT, max_width=896, log=print):
    kfdir = os.path.join(outdir, "keyframes")
    index = json.load(open(os.path.join(kfdir, "index.json")))
    client = ollama.Client()

    results = []
    for k in index:
        path = os.path.join(kfdir, k["file"])
        t0 = time.time()
        try:
            r = client.generate(model=model, prompt=prompt,
                                 images=[_prep_image(path, max_width)],
                                 options={"temperature": 0.1, "num_predict": 320})
            desc = _text(r).strip()
        except Exception as e:
            desc = f"[fejl: {e}]"
        results.append({"t": k["t"], "file": k["file"], "description": desc})
        log(f"  [{_mmss(k['t'])}] ({time.time() - t0:4.1f}s) {desc[:88]}")

    json.dump(results, open(os.path.join(outdir, "visuals.json"), "w"),
              ensure_ascii=False, indent=2)
    with open(os.path.join(outdir, "visuals.md"), "w") as f:
        f.write("# Visuel gennemgang (skaerm)\n\n")
        for r in results:
            f.write(f"**[{_mmss(r['t'])}]** {r['description']}\n\n")
    return results


def main():
    ap = argparse.ArgumentParser(description="Describe keyframes with an Ollama vision model.")
    ap.add_argument("outdir")
    ap.add_argument("-m", "--model", default="gemma3:4b")
    ap.add_argument("--max-width", type=int, default=896)
    a = ap.parse_args()
    res = describe(a.outdir, a.model, max_width=a.max_width)
    print(f"described {len(res)} keyframes -> {os.path.join(a.outdir, 'visuals.md')}")


if __name__ == "__main__":
    main()
