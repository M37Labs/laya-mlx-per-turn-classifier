"""Process-wide laya-mlx model: loaded once in the background, one prediction at a time."""

import platform
import subprocess
import threading
import time
import warnings

from django.conf import settings

_lock = threading.Lock()  # guards the model: MLX inference isn't safe to run concurrently
_state_lock = threading.Lock()
_loaded = threading.Event()  # set once loading has finished, successfully or not
_state = {"status": "idle", "error": None, "load_seconds": None, "warmup_seconds": None}
_agent = None


def hardware():
    try:
        chip = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True, timeout=2
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        chip = ""
    return chip or platform.machine()


HARDWARE = hardware()


def _load():
    global _agent
    import laya_mlx

    started = time.perf_counter()
    try:
        with warnings.catch_warnings():
            # Only affects choice fields with 11+ options, which the admin forbids.
            warnings.filterwarnings("ignore", message="laya-mlx: this checkpoint ships temperatures")
            # Padding to a multiple of 32 keeps the number of distinct input shapes small, so
            # MLX compiles kernels for a handful of shapes rather than for every message length.
            agent = laya_mlx.load(settings.LAYA_MODEL_ID, pad_to_multiple=32)
        agent.predict("warm up", {"q": {"type": "noul", "instructions": "Is this a test?"}})
    except Exception as exc:  # surfaced to the UI via status()
        _state.update(status="error", error=f"{type(exc).__name__}: {exc}")
        raise
    _agent = agent
    _state.update(status="ready", load_seconds=round(time.perf_counter() - started, 2))
    _loaded.set()  # unblock waiting requests now; they interleave with warm-up via _lock
    _warm_up()


def _warm_up():
    """Run every demo example once so the first click in a live demo isn't a cold, compiling call."""
    from .models import UseCase

    started = time.perf_counter()
    try:
        for uc in UseCase.objects.filter(is_active=True).prefetch_related("fields", "examples"):
            schema = uc.schema()
            for example in uc.examples.all():
                with _lock:
                    _agent.predict(example.text, schema)
    except Exception:  # warm-up is best effort; real requests still work
        pass
    _state["warmup_seconds"] = round(time.perf_counter() - started, 2)


def start_loading():
    """Kick off a background load; safe to call repeatedly."""
    with _state_lock:
        if _state["status"] in ("loading", "ready"):
            return
        _state.update(status="loading", error=None)
        _loaded.clear()

    def run():
        try:
            _load()
        except Exception:
            pass
        finally:
            _loaded.set()

    threading.Thread(target=run, name="laya-load", daemon=True).start()


def status():
    return {**_state, "model_id": settings.LAYA_MODEL_ID, "hardware": HARDWARE}


def predict(text, schema):
    """Returns (result, model_ms). Blocks until the model is loaded."""
    if _agent is None:
        start_loading()
        _loaded.wait()
        if _agent is None:
            raise RuntimeError(_state["error"] or "Model failed to load")
    with _lock:
        started = time.perf_counter()
        result = _agent.predict(text, schema)
        model_ms = (time.perf_counter() - started) * 1000
    return result, model_ms
