from django.db import migrations


def seed(apps, schema_editor):
    from classifier import seed as demo

    demo.load(
        apps.get_model("classifier", "UseCase"),
        apps.get_model("classifier", "Field"),
        apps.get_model("classifier", "Example"),
    )


class Migration(migrations.Migration):
    dependencies = [("classifier", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
