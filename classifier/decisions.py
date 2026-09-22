"""Turns raw model answers into a business decision: automate, or send to a human."""


def decide(use_case, answers):
    """Returns {"decision": "automate" | "review", "reasons": [...]}, one reason per gate missed."""
    reasons = []
    for field in use_case.fields.all():
        answer = answers.get(field.key)
        if field.min_confidence is None or answer is None:
            continue
        if answer["confidence"] < field.min_confidence:
            reasons.append(
                {
                    "field": field.key,
                    "label": field.label,
                    "confidence": answer["confidence"],
                    "required": field.min_confidence,
                }
            )
    return {"decision": "review" if reasons else "automate", "reasons": reasons}


def percentile(values, pct):
    if not values:
        return None
    values = sorted(values)
    k = (len(values) - 1) * pct / 100
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)
