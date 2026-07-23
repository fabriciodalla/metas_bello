from django.db import migrations


def backfill_email(apps, schema_editor):
    """Login passou a ser por e-mail (unique=True na próxima migration) — usuários já existentes
    sem e-mail (bancos de dev seedados antes dessa mudança) ganham um placeholder óbvio derivado
    do username, não uma tentativa de e-mail real."""
    User = apps.get_model("accounts", "User")
    for user in User.objects.filter(email=""):
        user.email = f"{user.username}@bello.local"
        user.save(update_fields=["email"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_alter_user_managers_remove_user_hierarchy_node_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_email, noop_reverse),
    ]
