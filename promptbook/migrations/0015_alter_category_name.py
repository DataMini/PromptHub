# Generated by Django 4.1.7 on 2024-02-18 13:52

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("promptbook", "0014_alter_category_help_text"),
    ]

    operations = [
        migrations.AlterField(
            model_name="category",
            name="name",
            field=models.CharField(max_length=255, unique=True),
        ),
    ]
