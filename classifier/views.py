import json
import time

from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from . import engine
from .decisions import decide, percentile
from .models import Field, Prediction, UseCase

MAX_INPUT_CHARS = 4000
# Measured from the aac6fef/laya-mlx checkpoint; see README.
MODEL_INFO = {"params": "421M", "size": "843 MB", "encoder": "ModernBERT-large", "precision": "float16"}
STATS_WINDOW = 500


def _use_cases():
    qs = UseCase.objects.filter(is_active=True).prefetch_related(
        Prefetch("fields", queryset=Field.objects.order_by("order", "id")), "examples"
    )
    return [
        {
            "slug": uc.slug,
            "name": uc.name,
            "industry": uc.industry,
            "tagline": uc.tagline,
            "description": uc.description,
            "business_value": uc.business_value,
            "input_label": uc.input_label,
            "fields": [
                {
                    "key": f.key,
                    "label": f.label,
                    "type": f.type,
                    "instructions": f.instructions,
                    "min_confidence": f.min_confidence,
                    "options": f.parsed_options(),
                }
                for f in uc.fields.all()
            ],
            "examples": [{"title": e.title, "text": e.text} for e in uc.examples.all()],
        }
        for uc in qs
    ]


def _stats():
    rows = list(Prediction.objects.values_list("model_ms", "answers")[:STATS_WINDOW])
    recent = [ms for ms, _ in rows]
    total_ms = sum(recent)
    return {
        "total_predictions": Prediction.objects.count(),
        "p50_ms": percentile(recent, 50),
        "p95_ms": percentile(recent, 95),
        "window": len(recent),
        # questions answered per second of model time
        "decisions_per_second": sum(len(a) for _, a in rows) / (total_ms / 1000) if total_ms else None,
    }


@ensure_csrf_cookie
@require_GET
def index(request):
    engine.start_loading()
    return render(
        request,
        "classifier/index.html",
        {
            "use_cases": _use_cases(),
            "initial": request.GET.get("use_case", ""),
            "autorun": request.GET.get("run", ""),
            "model_info": MODEL_INFO,
        },
    )


@require_GET
def api_status(request):
    engine.start_loading()
    return JsonResponse({**engine.status(), "stats": _stats()})


@require_POST
def api_classify(request):
    received = time.perf_counter()
    try:
        body = json.loads(request.body)
        slug, text = body["use_case"], body["text"].strip()
    except (ValueError, KeyError, AttributeError):
        return JsonResponse({"error": "Send JSON with use_case and text."}, status=400)
    if not text:
        return JsonResponse({"error": "Enter a message to classify."}, status=400)
    if len(text) > MAX_INPUT_CHARS:
        return JsonResponse({"error": f"Keep messages under {MAX_INPUT_CHARS} characters."}, status=400)
    try:
        use_case = UseCase.objects.prefetch_related("fields").get(slug=slug, is_active=True)
    except UseCase.DoesNotExist:
        return JsonResponse({"error": "Unknown use case."}, status=404)

    schema = use_case.schema()
    try:
        result, model_ms = engine.predict(text, schema)
    except Exception as exc:
        return JsonResponse({"error": f"Model error: {exc}"}, status=503)

    answers = result["answers"]
    decision = decide(use_case, answers)
    tokens = result.get("usage", {}).get("input_tokens", 0)
    Prediction.objects.create(
        use_case=use_case,
        text=text,
        answers=answers,
        decision=decision["decision"],
        model_ms=model_ms,
        input_tokens=tokens,
    )
    return JsonResponse(
        {
            "answers": answers,
            **decision,
            "metrics": {
                "model_ms": round(model_ms, 1),
                "server_ms": round((time.perf_counter() - received) * 1000, 1),
                "input_tokens": tokens,
                "fields": len(schema),
            },
            "stats": _stats(),
        }
    )
