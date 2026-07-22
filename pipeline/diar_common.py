"""Shared pyannote diarization helpers.

pyannote runs on **CPU** here: torch 2.5's bundled cuDNN 9 requires GPU compute
capability >= 7.5, and both cards are older (980 Ti 5.2, 1060 6.1). Diarization
is ~0.7x realtime on CPU, which is fine for offline processing.

pyannote 4.0 returns a DiarizeOutput with:
  * .speaker_diarization  -> Annotation (who spoke when)
  * .speaker_embeddings   -> array [n_speakers, dim], row i ~ sorted label i
"""
import functools
import json
import os

import numpy as np
import torch
from pyannote.audio import Pipeline

VOICEPRINTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voiceprints.json")


@functools.lru_cache(maxsize=1)
def get_pipeline():
    p = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
    p.to(torch.device("cpu"))
    return p


def diarize(audio_path, log=print):
    """Return (annotation, {label: embedding}, {label: total_speech_seconds})."""
    out = get_pipeline()(audio_path, return_embeddings=True)
    diar = out.speaker_diarization
    emb = np.asarray(out.speaker_embeddings)
    labels = diar.labels()
    label_emb = {lab: emb[i] for i, lab in enumerate(labels) if i < len(emb)}
    dur = {lab: 0.0 for lab in labels}
    for turn, _, lab in diar.itertracks(yield_label=True):
        dur[lab] += turn.duration
    return diar, label_emb, dur


def cosine(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def load_voiceprints():
    return json.load(open(VOICEPRINTS)) if os.path.exists(VOICEPRINTS) else {}


def save_voiceprints(vps):
    json.dump(vps, open(VOICEPRINTS, "w"), ensure_ascii=False, indent=2)
