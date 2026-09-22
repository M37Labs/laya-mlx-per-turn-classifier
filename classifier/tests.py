import json
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase

from .decisions import decide, percentile
from .models import Field, Prediction, UseCase


def fake_answers(confidence=0.9):
    return {
        "department": {"type": "choice", "confidence": confidence, "choice": "billing",
                       "probabilities": {"billing": 0.97, "technical": 0.02, "sales": 0.01},
                       "action": {"act_probability": 1.0}},
        "urgency": {"type": "score", "confidence": 0.14, "score": 1.45,
                    "legend": {"0": "not urgent", "1": "soon", "2": "critical"},
                    "probabilities": {"0": 0.15, "1": 0.26, "2": 0.59},
                    "action": {"act_probability": 1.0}},
        "refund": {"type": "noul", "confidence": 0.82, "noul": 0.82, "action": {"act_probability": 1.0}},
    }


class SeedTests(TestCase):
    def test_seed_migration_creates_valid_use_cases(self):
        self.assertGreaterEqual(UseCase.objects.count(), 8)
        for field in Field.objects.all():
            field.full_clean()

    def test_schema_matches_laya_format(self):
        schema = UseCase.objects.get(slug="support-triage").schema()
        self.assertEqual(list(schema), ["department", "urgency", "refund"])
        self.assertEqual(schema["department"]["criteria"]["technical"], "bugs, errors, outages")
        self.assertEqual(schema["urgency"]["criteria"], ["not urgent", "soon", "critical"])
        self.assertNotIn("criteria", schema["refund"])


class FieldValidationTests(TestCase):
    def setUp(self):
        self.uc = UseCase.objects.get(slug="support-triage")

    def field(self, type_, options):
        return Field(use_case=self.uc, key="x", label="X", type=type_, instructions="?", options=options)

    def test_choice_needs_two_unique_labels(self):
        with self.assertRaises(ValidationError):
            self.field("choice", "only: one").full_clean()
        with self.assertRaises(ValidationError):
            self.field("choice", "a: 1\na: 2").full_clean()

    def test_choice_capped_at_ten(self):
        with self.assertRaises(ValidationError):
            self.field("choice", "\n".join(f"o{i}: d" for i in range(11))).full_clean()

    def test_yes_no_only_true_false_lines(self):
        self.field("noul", "true: yes\nfalse: no").full_clean()
        with self.assertRaises(ValidationError):
            self.field("noul", "maybe: hmm").full_clean()

    def test_option_description_may_contain_colons(self):
        f = self.field("choice", "conduct: behaviour: harassment\nother: x")
        self.assertEqual(f.parsed_options()["conduct"], "behaviour: harassment")


class DecisionTests(TestCase):
    def test_automate_when_gated_fields_are_confident(self):
        uc = UseCase.objects.get(slug="support-triage")
        self.assertEqual(decide(uc, fake_answers())["decision"], "automate")

    def test_review_lists_fields_below_gate(self):
        uc = UseCase.objects.get(slug="support-triage")
        result = decide(uc, fake_answers(confidence=0.1))
        self.assertEqual(result["decision"], "review")
        self.assertEqual([r["field"] for r in result["reasons"]], ["department"])

    def test_percentile(self):
        self.assertIsNone(percentile([], 50))
        self.assertEqual(percentile([10, 20, 30], 50), 20)
        self.assertEqual(percentile([10, 20], 50), 15)


@mock.patch("classifier.engine.start_loading")
class ApiTests(TestCase):
    def post(self, payload):
        return self.client.post("/api/classify", json.dumps(payload), content_type="application/json")

    def test_index_renders_active_use_cases(self, _):
        UseCase.objects.filter(slug="hr-helpdesk").update(is_active=False)
        resp = self.client.get("/")
        self.assertContains(resp, "Customer Support Triage")
        self.assertNotContains(resp, "Employee Helpdesk")

    @mock.patch("classifier.engine.predict")
    def test_classify_returns_answers_metrics_and_logs(self, predict, _):
        predict.return_value = ({"answers": fake_answers(), "usage": {"input_tokens": 140}}, 48.2)
        resp = self.post({"use_case": "support-triage", "text": "I was billed twice."})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["decision"], "automate")
        self.assertEqual(data["metrics"]["model_ms"], 48.2)
        self.assertEqual(data["metrics"]["input_tokens"], 140)
        self.assertEqual(data["metrics"]["fields"], 3)
        self.assertEqual(data["stats"]["total_predictions"], 1)
        self.assertEqual(Prediction.objects.get().decision, "automate")
        text, schema = predict.call_args.args
        self.assertEqual(text, "I was billed twice.")
        self.assertEqual(set(schema), {"department", "urgency", "refund"})

    def test_classify_rejects_bad_input(self, _):
        self.assertEqual(self.post({"use_case": "support-triage", "text": "  "}).status_code, 400)
        self.assertEqual(self.post({"use_case": "nope", "text": "hi"}).status_code, 404)
        self.assertEqual(self.post({"text": "hi"}).status_code, 400)
        self.assertEqual(self.post({"use_case": "support-triage", "text": "x" * 5000}).status_code, 400)

    def test_inactive_use_case_is_not_classifiable(self, _):
        UseCase.objects.filter(slug="support-triage").update(is_active=False)
        self.assertEqual(self.post({"use_case": "support-triage", "text": "hi"}).status_code, 404)

    @mock.patch("classifier.engine.predict", side_effect=RuntimeError("boom"))
    def test_model_failure_is_503(self, *_):
        resp = self.post({"use_case": "support-triage", "text": "hi"})
        self.assertEqual(resp.status_code, 503)
        self.assertFalse(Prediction.objects.exists())


class AdminTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        self.uc = UseCase.objects.get(slug="support-triage")

    def test_pages_render(self):
        for url in ["/admin/classifier/usecase/", f"/admin/classifier/usecase/{self.uc.pk}/change/",
                    "/admin/classifier/usecase/add/", "/admin/classifier/prediction/"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def _form(self, **overrides):
        """The change form as the admin renders it, with every inline row filled in."""
        data = {
            "name": self.uc.name, "slug": self.uc.slug, "industry": self.uc.industry,
            "order": self.uc.order, "is_active": "on", "tagline": self.uc.tagline,
            "description": self.uc.description, "business_value": self.uc.business_value,
            "input_label": self.uc.input_label,
        }
        fields, examples = list(self.uc.fields.all()), list(self.uc.examples.all())
        data.update({"fields-TOTAL_FORMS": len(fields), "fields-INITIAL_FORMS": len(fields),
                     "examples-TOTAL_FORMS": len(examples), "examples-INITIAL_FORMS": len(examples)})
        for i, f in enumerate(fields):
            data.update({f"fields-{i}-id": f.pk, f"fields-{i}-use_case": self.uc.pk,
                         f"fields-{i}-key": f.key, f"fields-{i}-label": f.label,
                         f"fields-{i}-type": f.type, f"fields-{i}-instructions": f.instructions,
                         f"fields-{i}-options": f.options, f"fields-{i}-order": f.order,
                         f"fields-{i}-min_confidence": "" if f.min_confidence is None else f.min_confidence})
        for i, e in enumerate(examples):
            data.update({f"examples-{i}-id": e.pk, f"examples-{i}-use_case": self.uc.pk,
                         f"examples-{i}-title": e.title, f"examples-{i}-text": e.text,
                         f"examples-{i}-order": e.order})
        data.update(overrides)
        return data

    def test_edit_options_inline(self):
        url = f"/admin/classifier/usecase/{self.uc.pk}/change/"
        new = "billing: invoices\ntechnical: bugs\nsales: pricing\nlegal: contracts, compliance"
        resp = self.client.post(url, self._form(**{"fields-0-options": new}))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(list(self.uc.schema()["department"]["criteria"]), ["billing", "technical", "sales", "legal"])

    def test_invalid_options_show_error(self):
        url = f"/admin/classifier/usecase/{self.uc.pk}/change/"
        resp = self.client.post(url, self._form(**{"fields-0-options": "only: one"}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "at least two options")
