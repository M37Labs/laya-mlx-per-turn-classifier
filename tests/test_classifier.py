import pytest

import laya_mlx as laya

SCHEMA = {
    "department": {"type": "choice", "instructions": "Which team handles this?",
                   "criteria": {
                       "billing": "invoices, charges, refunds on existing accounts",
                       "technical": "bugs, errors, outages",
                       "sales": "purchases, pricing, plans, upgrades, new customers",
                   }},
    "urgency": {"type": "score", "instructions": "How urgent?",
                "criteria": ["not urgent", "soon", "critical"]},
    "refund": {"type": "noul", "instructions": "Does the customer ask for money back?"},
}

# (message, department, wants_refund, urgency: "low" | "high")
CASES = [
    ("I was billed twice. Please refund the duplicate today.", "billing", True, "high"),
    ("Can you send me a copy of last month's invoice when you get a chance?", "billing", False, "low"),
    ("I cancelled my subscription but was still charged. I want my money back.", "billing", True, None),
    ("The app crashes every time I open the settings page.", "technical", False, None),
    ("Production is down, none of our users can log in! Fix this now!", "technical", False, "high"),
    ("The export button is slightly misaligned on mobile, no rush.", "technical", False, "low"),
    ("I'd like to buy 50 more seats for my team. What's the pricing?", "sales", False, None),
    ("Do you offer an enterprise plan? Just exploring options for next year.", "sales", False, "low"),
]

URGENCY_LOW_MAX = 0.8   # score on 0..2 scale
URGENCY_HIGH_MIN = 1.2


@pytest.fixture(scope="module")
def agent():
    return laya.load("aac6fef/laya-mlx")


@pytest.fixture(scope="module")
def results(agent):
    return {msg: agent.predict(msg, SCHEMA)["answers"] for msg, *_ in CASES}


@pytest.mark.parametrize("msg,department,_refund,_urgency", CASES)
def test_department(results, msg, department, _refund, _urgency):
    assert results[msg]["department"]["choice"] == department, results[msg]["department"]


@pytest.mark.parametrize("msg,_department,wants_refund,_urgency", CASES)
def test_refund(results, msg, _department, wants_refund, _urgency):
    p = results[msg]["refund"]["noul"]
    assert (p > 0.5) == wants_refund, f"refund p={p}"


@pytest.mark.parametrize("msg,_department,_refund,urgency",
                         [c for c in CASES if c[3] is not None])
def test_urgency(results, msg, _department, _refund, urgency):
    score = results[msg]["urgency"]["score"]
    if urgency == "high":
        assert score >= URGENCY_HIGH_MIN, f"score={score}"
    else:
        assert score <= URGENCY_LOW_MAX, f"score={score}"


def test_output_shape(results):
    answers = next(iter(results.values()))
    assert set(answers) == set(SCHEMA)
    probs = answers["department"]["probabilities"]
    assert set(probs) == {"billing", "technical", "sales"}
    assert sum(probs.values()) == pytest.approx(1.0, abs=1e-3)
    assert 0.0 <= answers["refund"]["noul"] <= 1.0
    assert 0.0 <= answers["urgency"]["score"] <= 2.0
