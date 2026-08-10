# Generated manually for Decisão 14 (docs/decisions.md) — remoção do nível Coordenador Regional.
# Ambiente sem dado real de nó REGIONAL a preservar (banco de dev resetado para o novo cliente).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hierarchy", "0003_feristacoverage"),
    ]

    operations = [
        migrations.AlterField(
            model_name="hierarchynode",
            name="level",
            field=models.CharField(
                choices=[
                    ("GERENTE", "Gerente"),
                    ("LOCAL", "Coordenador Local"),
                    ("SUPERVISOR", "Supervisor"),
                    ("VENDEDOR", "Vendedor"),
                ],
                max_length=20,
            ),
        ),
    ]
