"""Make CTranslate2 (faster-whisper) find the CUDA math libraries.

faster-whisper needs libcublas.so.12 and libcudnn, which are not installed
system-wide here; they come from the nvidia-cublas-cu12 / nvidia-cudnn-cu12
pip wheels in this venv. The dynamic loader only reads LD_LIBRARY_PATH at
process start, so the first time we set it and re-exec the interpreter once.
"""
import importlib
import os
import sys


def ensure_cuda_libs():
    """Prepend the venv's bundled CUDA libs to LD_LIBRARY_PATH and re-exec once.

    `nvidia` is a namespace package (its __file__ is None), so resolve each
    sub-package (nvidia.cublas, nvidia.cudnn) individually to find its lib dir.
    """
    if os.environ.get("_CT_CUDA_READY"):
        return
    os.environ["_CT_CUDA_READY"] = "1"
    libdirs = []
    for sub in ("cublas", "cudnn"):
        try:
            mod = importlib.import_module(f"nvidia.{sub}")
            for base in list(getattr(mod, "__path__", []) or []):
                d = os.path.join(base, "lib")
                if os.path.isdir(d):
                    libdirs.append(d)
        except Exception:
            pass  # CPU-only, or libs provided elsewhere on the system
    if not libdirs:
        return
    os.environ["LD_LIBRARY_PATH"] = ":".join(libdirs + [os.environ.get("LD_LIBRARY_PATH", "")])
    os.execv(sys.executable, [sys.executable] + sys.argv)
