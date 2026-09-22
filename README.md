# laya-mlx per-turn classifier

A starting point for trying out [`laya-mlx`](https://pypi.org/project/laya-mlx/) as a **per-turn classifier** for customer messages. You describe what you want to know in a schema (which team, how urgent, is it a refund request?). The model answers every field in a single pass on Apple Silicon, in about 50 ms.

```python
import laya_mlx as laya

agent = laya.load("aac6fef/laya-mlx")
result = agent.predict(
    "I was billed twice. Please refund the duplicate today.",
    {
        "department": {"type": "choice", "instructions": "Which team handles this?",
                       "criteria": {
                           "billing": "invoices, charges, refunds on existing accounts",
                           "technical": "bugs, errors, outages",
                           "sales": "purchases, pricing, plans, upgrades, new customers",
                       }},
        "urgency": {"type": "score", "instructions": "How urgent?",
                    "criteria": ["not urgent", "soon", "critical"]},
        "refund": {"type": "noul", "instructions": "Does the customer ask for money back?"},
    },
)
print(result["answers"])
```

## Quick start

Requirements: a Mac with Apple Silicon (MLX doesn't run on Intel or Linux), [uv](https://docs.astral.sh/uv/), and about 1 GB of free disk and RAM.

```bash
git clone https://github.com/M37Labs/laya-mlx-per-turn-classifier-.git
cd laya-mlx-per-turn-classifier-
uv sync               # creates .venv, installs laya-mlx + pytest
uv run main.py        # runs the example above
uv run pytest -v      # runs the test suite
```

## Demo app for executives

A Django web app that shows the model working across eight enterprise workflows, with live latency figures. It's built for walking CTOs and executives through what a per-turn classifier can do.

```bash
uv run python manage.py migrate            # creates db.sqlite3 and loads the 8 demo use cases
uv run python manage.py createsuperuser    # an account for the admin panel
uv run python manage.py runserver          # http://127.0.0.1:8000
```

The model loads in the background when the server starts (about 1 s once cached). The server then runs every demo example once (about 2.5 s) so the first click in a live demo isn't slow.

**What the audience sees**

- A **use-case picker** grouped by industry. Each use case explains the workflow and its business impact in plain language.
- A **message box** with one-click examples, plus free text: let the audience type their own.
- **One card per question the model answers:** a probability bar for each choice, a scale for ordered levels, a yes/no meter, and the confidence against the automation gate. Hover any chart for the details.
- An **Automate / Send to human review** decision. A use case can require a minimum confidence on some fields; if any of those falls short, the message goes to a person, and the banner says which field and by how much.
- **Run all examples:** a batch table with every example's answers, decision and latency, plus an automation rate.
- **Live technical figures:** model inference time, server processing time, browser round trip, input tokens, decisions per second, p50/p95 across all logged runs, the hardware, and model load time.

Presenter shortcuts: `/?use_case=banking-servicing` opens a specific use case, `&run=1` classifies the first example as soon as the model is ready, and `&run=all` runs the batch.

**Demo use cases**

| Industry | Use case | Questions answered |
|---|---|---|
| Customer Experience | Customer Support Triage | department, urgency, refund requested |
| Banking | Card & Account Servicing | request type, unauthorised activity, customer financial risk |
| Healthcare | Patient Portal Messages | route, clinical urgency, new/worsening symptoms |
| Human Resources | Employee Helpdesk | topic (incl. conduct complaints), sentiment |
| Retail & E-commerce | Order Feedback | issue, customer sentiment |
| Insurance | Claims First Notice of Loss | line of business, severity, injury reported |
| Telecom | Churn & Retention | main reason, churn risk, asks to cancel |
| Compliance | Communications Surveillance | promises returns, off-channel request, message type, sales pressure |

**Admin panel (`/admin`)**

Super-admins can change everything the audience sees without touching code:

- **Use cases:** name, industry, tagline, workflow description, business impact, input label, display order, and whether it's shown (`is_active`). The list page has an "Open ↗" link to preview each one in the demo.
- **Questions (inline on each use case):** label, machine key, type, the question itself, and the options, one per line:
  - Choice: `label: description`, e.g. `fraud: charges the customer did not make`
  - Scale: one level per line, lowest first
  - Yes / No: optional `true: …` and `false: …` lines
- **Automation gate (`min_confidence`):** when a field's confidence falls below this value, the decision goes to human review. Leave it blank for fields that are informational only.
- **Examples:** the one-click example messages.
- **Predictions:** a read-only audit log of every demo run, with message, answers, decision, latency and tokens.

The form rejects invalid option lists: fewer than two options, duplicate labels, more than 10 choice options (confidence isn't calibrated at 11 or more), and malformed yes/no lines.

To restore the default demo content after experiments: `uv run python manage.py seed_use_cases --reset` (this replaces the eight default use cases and keeps any you added).

**Configuration (environment variables)**

| Variable | Default | |
|---|---|---|
| `DJANGO_SECRET_KEY` | dev-only placeholder | **set this for anything shared** |
| `DJANGO_DEBUG` | `1` | set `0` outside local demos |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | comma-separated |
| `LAYA_MODEL_ID` | `aac6fef/laya-mlx` | any laya-mlx checkpoint |
| `LAYA_PRELOAD` | `1` | load the model at server start |

The app runs one prediction at a time (MLX inference is serialised behind a lock) and the model runs on the server, so the server must be an Apple Silicon Mac. It's built for live demos and small pilots, not production traffic.

Django tests (the model is stubbed, so they take under a second): `uv run python manage.py test classifier`.

The first run downloads the model (~843 MB) from Hugging Face into `~/.cache/huggingface/hub/`. Later runs load it from that cache.

> If your shell has `VIRTUAL_ENV` set (pyenv, conda, …), uv prints a warning and ignores it. Run `unset VIRTUAL_ENV` to silence the warning.

## The model

| | |
|---|---|
| Hugging Face repo | [`aac6fef/laya-mlx`](https://huggingface.co/aac6fef/laya-mlx), an MLX conversion of [`convaiinnovations/laya`](https://huggingface.co/convaiinnovations/laya) |
| Architecture | [ModernBERT-large](https://huggingface.co/answerdotai/ModernBERT-large) encoder (28 layers, hidden 1024) + small task heads |
| Parameters | **421 M** total |
| Weights | float16, one `model.safetensors` of **843 MB** (plus a ~3.6 MB tokenizer) |
| Context | 512 tokens max input |

How the parameters break down:

| Component | Params | Share | What it does |
|---|---:|---:|---|
| `encoder` | 394.8 M | 93.7% | ModernBERT-large, reads the message and schema |
| `head` | 25.2 M | 6.0% | 2-layer head that reads each field's instructions/criteria |
| `scorer` | 1.05 M | 0.25% | scores each option |
| `act_head` | 0.26 M | 0.06% | `act_probability`: should we act or escalate? |
| `type_emb`, `temperature` | ~3 K | – | field-type embeddings, calibration temperatures |

Measured on an **Apple M1 Pro**, using the 3-field schema above:

| | |
|---|---|
| Model load (cached) | ~2.8 s |
| `predict()` latency | **~48 ms** median (warm) |
| Peak memory | ~1.05 GB |

This is an encoder classifier, not an LLM. It doesn't generate text, so each call costs one forward pass no matter how many fields you ask for. For comparison, the weights are about a fifth the size of a 4-bit 7B LLM (~4 GB).

## Schema reference

Each key in the schema is a field you want answered. There are three field types:

| `type` | `criteria` | Output keys | Meaning |
|---|---|---|---|
| `choice` | `{label: description}` dict | `choice`, `probabilities` | Pick one label |
| `score` | ordered list, low → high | `score` (float, 0 … n-1), `probabilities`, `legend` | Place the message on an ordinal scale |
| `noul` | none | `noul` (float 0–1) | Yes/no probability |

Every field also returns `confidence` (0–1) and `action.act_probability`.

Example output:

```python
{
  'department': {'choice': 'billing', 'confidence': 0.87,
                 'probabilities': {'billing': 0.97, 'technical': 0.02, 'sales': 0.01}, ...},
  'urgency':    {'score': 1.45, 'confidence': 0.14,
                 'probabilities': {'0': 0.15, '1': 0.26, '2': 0.59},
                 'legend': {'0': 'not urgent', '1': 'soon', '2': 'critical'}, ...},
  'refund':     {'noul': 0.82, 'confidence': 0.82, ...},
}
```

## Tests

[`tests/test_classifier.py`](tests/test_classifier.py) runs 8 sample messages through the schema and checks:

- **department:** the model picks the expected team
- **refund:** `noul > 0.5` only when the customer asks for money back
- **urgency:** clearly urgent messages score ≥ 1.2 and clearly non-urgent ones ≤ 0.8 (messages that could go either way aren't checked)
- **output shape:** all fields are present, probabilities sum to 1, values stay in range

The model loads once per run, so the whole suite takes about 2 s.

**Current status: 22/22 pass.**

An earlier version described the labels in one word each (`"billing": "invoices, refunds"`, `"technical": "bugs"`, `"sales": "purchases"`). With that wording, "Do you offer an enterprise plan? Just exploring options for next year." went to **billing** (0.47) over sales (0.39). Describing each label with a few concrete examples fixed it: sales now wins at 0.58. The current wording is in `main.py` and the tests.

Department results with the current wording:

| Message | Choice | p | confidence |
|---|---|---:|---:|
| I was billed twice. Please refund the duplicate today. | billing | 0.97 | 0.87 |
| Can you send me a copy of last month's invoice… | billing | 0.98 | 0.88 |
| I cancelled my subscription but was still charged… | billing | 0.97 | 0.84 |
| The app crashes every time I open the settings page. | technical | 0.89 | 0.62 |
| Production is down, none of our users can log in! | technical | 0.94 | 0.76 |
| The export button is slightly misaligned on mobile… | technical | 0.64 | 0.17 |
| I'd like to buy 50 more seats for my team… | sales | 0.63 | 0.19 |
| Do you offer an enterprise plan? … | sales | 0.58 | 0.14 |

The labels are all right, but **sales answers still have low confidence** (0.14–0.19), and so does the low-key technical message. Improving these is a good first experiment: try more wording variants, or add more sales-style messages to `CASES`.

To add a case, append a tuple to `CASES`: `(message, department, wants_refund, "high" | "low" | None)`.

## Things we've learned

- **Latency in the web app is about 60 ms per message** (3–4 questions) on an M1 Pro. Standalone Python is about 50 ms, and the gap is mostly the dev server's autoreloader. The first message of a new input length is slower (up to about 110 ms) while MLX compiles kernels for that length. The app pads inputs to multiples of 32 and warms up on the examples to keep this rare.

- **Criteria wording matters a lot.** The model can only go by what the descriptions say. With `"sales": "purchases"`, an enterprise-plan question lost to billing's `"invoices, refunds"`. Adding `"pricing, plans, upgrades, new customers"` fixed it. Describe each label with a few concrete examples, and say what separates it from its neighbours (for example, billing is for *existing* accounts).
- **Use `confidence` to route.** Low-confidence answers (the urgency above is 0.14, the enterprise-plan miss is 0.10) are good candidates for a human or a fallback. Don't treat the argmax as ground truth.
- **Calibration warning.** On load you'll see
  `RuntimeWarning: ... clamping choice:11+=0.1006. Treat confidence from the affected buckets as uncalibrated.`
  The checkpoint's temperature for `choice` fields with **11 or more options** is out of range. Fields with fewer options aren't affected. If you build a large choice field, don't rely on its `confidence`. Consider splitting it into two levels instead. pytest hides this warning (see `pyproject.toml`).

## What the model is and isn't good at (from building the demo)

Every demo example was run through the model before it went in. Where a field kept getting things wrong, we changed the wording or dropped the field:

| Attempt | Result | What we did |
|---|---|---|
| Banking `fraud` vs `dispute` with short descriptions | foreign charges on a card the customer still has → *dispute* | Described fraud as "charges the customer did not make" and dispute as "a purchase they did make". Fixed. |
| Compliance "promises returns" yes/no with `true`/`false` descriptions | false positives of 0.82–0.83 on paperwork and WhatsApp messages | A plain question with no descriptions: 1.00 on the real case, ≤ 0.11 on the others |
| **Sales lead qualification** (demo / pricing / partnership / vendor pitch) | Can't tell "wants to buy from us" from "is selling to us". A pricing question scored 0.08 on "interested in buying". | **Dropped**, and replaced with Retail Order Feedback. Treat sender-perspective tasks as a weak spot. |
| HR "sensitive case" yes/no (harassment, discrimination) | Missed subtle cases: comments about an employee's accent scored 0.09–0.44 | Put the escalation on the Topic choice (`conduct: …`), which got 6 of 6 test tickets right |
| Retail "wants a return" yes/no | Fired on late deliveries (0.84) | Dropped. The Issue choice alone (defect / delivery / size / nothing) gets 4 of 4 right. |
| Compliance "off-channel" | Catches WhatsApp (1.00). Misses "send it to my gmail" (0.12). | Kept, with this gap noted |

General lessons:

- **Plain yes/no questions often beat yes/no questions with `true`/`false` descriptions.**
- **Choice confidence runs low** (0.1–0.9) even when the label is right, so gates for choice fields sit at 0.3 and yes/no gates at 0.7. Scale fields rarely go above 0.5 confidence, so they don't gate anything by default.
- Always test on your own examples before trusting a field. The admin makes this quick: edit the wording, then click "Run all examples".

## Ideas to experiment with

- Real transcripts: replace `CASES` with labelled turns from actual support conversations and measure accuracy per field.
- Conversation context: classify each turn with or without the previous turns and compare.
- Criteria A/B testing: compare description wordings on the same labelled set.
- Confidence thresholds: find the confidence cutoff that gives, say, 95% precision, and escalate everything below it.
- More fields: sentiment, language, churn risk, PII present. Latency barely changes as you add fields.

## Layout

```
manage.py                 # Django entry point
laya_demo/                # Django project settings and URLs
classifier/
  models.py               # UseCase, Field, Example, Prediction
  admin.py                # super-admin panel
  engine.py               # loads the model once, background warm-up, timed predictions
  decisions.py            # automate vs human-review rule
  views.py                # page + JSON API (/api/status, /api/classify)
  seed.py                 # the 8 demo use cases (migration 0002 and seed_use_cases)
  templates/, static/     # the frontend (plain HTML/CSS/JS, no build step)
  tests.py                # Django tests (model stubbed)
main.py                   # the example script
tests/test_classifier.py  # labelled cases + pytest checks
pyproject.toml            # deps (laya-mlx; pytest in dev group) + pytest config
uv.lock                   # pinned versions, commit changes to this
```
