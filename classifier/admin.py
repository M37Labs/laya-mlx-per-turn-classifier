from django import forms
from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import Example, Field, Prediction, UseCase


class FieldInline(admin.StackedInline):
    model = Field
    extra = 0
    fields = [("label", "key", "type"), "instructions", "options", ("min_confidence", "order")]
    prepopulated_fields = {"key": ["label"]}
    formfield_overrides = {
        Field._meta.get_field("options").__class__: {
            "widget": forms.Textarea(attrs={"rows": 5, "cols": 90, "style": "font-family: monospace"})
        }
    }


class ExampleInline(admin.TabularInline):
    model = Example
    extra = 1
    fields = ["title", "text", "order"]
    formfield_overrides = {
        Example._meta.get_field("text").__class__: {"widget": forms.Textarea(attrs={"rows": 2, "cols": 80})}
    }


@admin.register(UseCase)
class UseCaseAdmin(admin.ModelAdmin):
    list_display = ["name", "industry", "field_count", "example_count", "is_active", "order", "demo_link"]
    list_editable = ["is_active", "order"]
    list_filter = ["industry", "is_active"]
    search_fields = ["name", "industry", "tagline"]
    prepopulated_fields = {"slug": ["name"]}
    inlines = [FieldInline, ExampleInline]
    fieldsets = [
        (None, {"fields": [("name", "slug"), ("industry", "order", "is_active"), "tagline"]}),
        ("Story for the audience", {"fields": ["description", "business_value", "input_label"]}),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            n_fields=Count("fields", distinct=True), n_examples=Count("examples", distinct=True)
        )

    @admin.display(description="Fields", ordering="n_fields")
    def field_count(self, obj):
        return obj.n_fields

    @admin.display(description="Examples", ordering="n_examples")
    def example_count(self, obj):
        return obj.n_examples

    @admin.display(description="Demo")
    def demo_link(self, obj):
        return format_html('<a href="{}" target="_blank">Open ↗</a>', obj.get_absolute_url())


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ["created_at", "use_case", "short_text", "decision", "model_ms_display", "input_tokens"]
    list_filter = ["use_case", "decision"]
    search_fields = ["text"]
    date_hierarchy = "created_at"
    readonly_fields = [f.name for f in Prediction._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Message")
    def short_text(self, obj):
        return obj.text if len(obj.text) <= 80 else obj.text[:77] + "…"

    @admin.display(description="Model ms", ordering="model_ms")
    def model_ms_display(self, obj):
        return f"{obj.model_ms:.1f}"
