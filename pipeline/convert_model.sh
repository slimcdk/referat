#!/usr/bin/env bash
# One-time: convert the Danish Whisper (syvai/hviske-v2, already in the HF cache)
# to CTranslate2 int8 format so faster-whisper can use it.
#
# The converter needs torch + transformers, which already live in the existing
# ../transscribe/venv, so we reuse that venv and only add ctranslate2 to it.
# The int8-quantized model still runs as float32 on the Maxwell card (CT2
# upcasts at load), so one converted model works on both GPUs.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
TORCH_VENV="$HERE/../transscribe/venv"
OUT="$HERE/models/hviske-v2-ct2"

if [[ ! -x "$TORCH_VENV/bin/python" ]]; then
  echo "ERROR: torch venv not found at $TORCH_VENV" >&2
  exit 1
fi

echo ">> ensuring ctranslate2 in the torch venv"
# NB: this venv's pip/console-script shebangs are broken, but bin/python works,
# so drive everything via `python -m ...`.
"$TORCH_VENV/bin/python" -m pip install -q ctranslate2

echo ">> converting syvai/hviske-v2 -> $OUT (int8)"
"$TORCH_VENV/bin/python" -m ctranslate2.converters.transformers \
  --model syvai/hviske-v2 \
  --output_dir "$OUT" \
  --quantization int8 \
  --copy_files tokenizer.json preprocessor_config.json \
  --force

echo ">> done:"
ls -la "$OUT"
