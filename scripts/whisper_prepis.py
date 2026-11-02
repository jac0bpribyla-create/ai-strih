"""Whisper s časem každého slova: mlx-whisper na Macu s Apple Silicon, jinde faster-whisper (Windows, Intel Mac, Linux).

prepis(wav, jazyk) bere wav 16 kHz mono 16 bit (ffmpeg -ac 1 -ar 16000) a vrací tvar jako mlx_whisper.transcribe –
{"segments": [{"start", "end", "text", "no_speech_prob", "words": [{"word", "start", "end", "probability"}]}]} –
takže skripty neřeší, který Whisper zrovna běží.
Model z nastaveni.json ("whisper_model", prázdné = large-v3-turbo, ~1,6 GB, stáhne se při prvním přepisu).
"""
import os
import sys
import wave
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nastaveni import nacti  # noqa: E402

try:
    import mlx_whisper
except ImportError:
    mlx_whisper = None

NAZEV = "mlx-whisper" if mlx_whisper else "faster-whisper"


def model_name() -> str:
    m = nacti()["whisper_model"]
    if mlx_whisper:
        return m or "mlx-community/whisper-large-v3-turbo"
    # faster-whisper zná zkratky tiny, base, small, medium, large-v3, large-v3-turbo; modely MLX načíst neumí.
    return "large-v3-turbo" if not m or m.startswith("mlx-community/") else m


@lru_cache(maxsize=1)
def _faster_model(name: str, device: str):
    from faster_whisper import WhisperModel
    return WhisperModel(name, device=device, compute_type="float16" if device == "cuda" else "int8",
                        cpu_threads=max(4, (os.cpu_count() or 8) // 2))


def prepis(wav, jazyk: str = None, no_speech_threshold: float = None) -> dict:
    kw = {"language": jazyk or None, "word_timestamps": True, "condition_on_previous_text": False,
          "hallucination_silence_threshold": 1.0}
    if no_speech_threshold is not None:
        kw["no_speech_threshold"] = no_speech_threshold
    if mlx_whisper:
        return mlx_whisper.transcribe(str(wav), path_or_hf_repo=model_name(), **kw)
    import numpy as np
    # wav (16 kHz mono, 16 bit z ffmpeg) načíst sám: dekodér faster-whisperu (PyAV) se s novými verzemi av rozbíjí.
    with wave.open(str(wav)) as f:
        audio = np.frombuffer(f.readframes(f.getnframes()), np.int16).astype(np.float32) / 32768
    model = _faster_model(model_name(), nacti()["whisper_zarizeni"] or "cpu")
    segments, _ = model.transcribe(audio, **kw)
    return {"segments": [{"start": s.start, "end": s.end, "text": s.text, "no_speech_prob": s.no_speech_prob,
                          "words": [{"word": w.word, "start": w.start, "end": w.end, "probability": w.probability}
                                    for w in (s.words or [])]} for s in segments]}
