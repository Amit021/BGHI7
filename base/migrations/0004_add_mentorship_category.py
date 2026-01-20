from django.db import migrations


def add_mentorship_category(apps, schema_editor):
    """Add the Mentorship category for the landing page."""
    Topic = apps.get_model("base", "Topic")
    Topic.objects.get_or_create(slug='mentorship', defaults={'name': 'Mentorship'})


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0003_remove_old_topics"),
    ]

    operations = [
        migrations.RunPython(add_mentorship_category, migrations.RunPython.noop),
    ]
