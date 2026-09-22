from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse


class UseCase(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    industry = models.CharField(max_length=60, help_text="Groups use cases in the picker, e.g. Banking.")
    tagline = models.CharField(max_length=200, help_text="One line shown under the name.")
    description = models.TextField(blank=True, help_text="What the workflow is, in business terms.")
    business_value = models.TextField(
        blank=True, help_text="Why an executive should care: cost, speed, risk, revenue."
    )
    input_label = models.CharField(
        max_length=80, default="Customer message", help_text="Label above the text box."
    )
    is_active = models.BooleanField(default=True, help_text="Only active use cases appear in the demo.")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("demo") + f"?use_case={self.slug}"

    def schema(self):
        """The laya-mlx question schema for this use case."""
        return {f.key: f.to_question() for f in self.fields.all()}


class Field(models.Model):
    CHOICE, SCORE, YESNO = "choice", "score", "noul"
    TYPES = [
        (CHOICE, "Choice: pick one label"),
        (SCORE, "Score: place on an ordered scale"),
        (YESNO, "Yes / No: probability a statement holds"),
    ]

    use_case = models.ForeignKey(UseCase, related_name="fields", on_delete=models.CASCADE)
    key = models.SlugField(max_length=60, help_text="Machine name, e.g. department.")
    label = models.CharField(max_length=80, help_text="Display name, e.g. Department.")
    type = models.CharField(max_length=10, choices=TYPES)
    instructions = models.CharField(max_length=300, help_text="The question the model answers.")
    options = models.TextField(
        blank=True,
        help_text=(
            "One option per line.<br>"
            "<b>Choice</b>: <code>label: description</code>. Say what the label covers "
            "and how it differs from its neighbours.<br>"
            "<b>Score</b>: one level per line, lowest first.<br>"
            "<b>Yes / No</b>: optional <code>true: description</code> and "
            "<code>false: description</code> lines."
        ),
    )
    min_confidence = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text=(
            "Automation gate. When this field's confidence falls below this value, the decision "
            "escalates to System 2 (an LLM or a person). Leave blank for fields that shouldn't "
            "block automation."
        ),
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["use_case", "key"], name="unique_field_key_per_use_case")
        ]

    def __str__(self):
        return f"{self.use_case.name} / {self.label}"

    def option_lines(self):
        return [line.strip() for line in self.options.splitlines() if line.strip()]

    def parsed_options(self):
        """Choice -> {label: description}; score -> [levels]; yes/no -> {"true": .., "false": ..}."""
        lines = self.option_lines()
        if self.type == self.SCORE:
            return lines
        pairs = {}
        for line in lines:
            label, _, desc = line.partition(":")
            pairs[label.strip()] = desc.strip()
        return pairs

    def to_question(self):
        q = {"type": self.type, "instructions": self.instructions}
        opts = self.parsed_options()
        if opts:
            q["criteria"] = opts
        return q

    def clean(self):
        lines = self.option_lines()
        if self.type == self.CHOICE:
            if len(lines) < 2:
                raise ValidationError({"options": "A choice field needs at least two options."})
            labels = [line.partition(":")[0].strip() for line in lines]
            if any(not label for label in labels):
                raise ValidationError({"options": "Every option needs a label before the colon."})
            if len(set(labels)) != len(labels):
                raise ValidationError({"options": "Option labels must be unique."})
            if len(labels) > 10:
                raise ValidationError(
                    {"options": "Keep choice fields to 10 options or fewer: the model's confidence "
                                "is uncalibrated for 11 or more."}
                )
        elif self.type == self.SCORE:
            if len(lines) < 2:
                raise ValidationError({"options": "A score field needs at least two levels."})
        elif self.type == self.YESNO:
            bad = [line for line in lines if line.partition(":")[0].strip().lower() not in ("true", "false")]
            if bad:
                raise ValidationError(
                    {"options": "Yes / No options may only be 'true: …' and 'false: …' lines."}
                )


class Example(models.Model):
    use_case = models.ForeignKey(UseCase, related_name="examples", on_delete=models.CASCADE)
    title = models.CharField(max_length=60, help_text="Short chip label, e.g. Duplicate charge.")
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Prediction(models.Model):
    """Every demo run, for auditing and the server-wide latency stats."""

    use_case = models.ForeignKey(UseCase, null=True, on_delete=models.SET_NULL)
    text = models.TextField()
    answers = models.JSONField()
    decision = models.CharField(max_length=20)
    model_ms = models.FloatField(help_text="Time spent inside the model.")
    input_tokens = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.use_case} · {self.created_at:%Y-%m-%d %H:%M:%S}"
