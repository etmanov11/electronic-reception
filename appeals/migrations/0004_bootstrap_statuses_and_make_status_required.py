from django.db import migrations, models
import django.db.models.deletion


def bootstrap_statuses_and_fill_nulls(apps, schema_editor):
    Status = apps.get_model('appeals', 'Status')
    Appeal = apps.get_model('appeals', 'Appeal')

    defaults = [
        ('new', 'Новое', 'secondary', 10),
        ('in_progress', 'В работе', 'warning', 20),
        ('on_review', 'На проверке', 'info', 30),
        ('revision', 'На доработке', 'primary', 40),
        ('approved', 'Удовлетворено', 'success', 50),
        ('rejected', 'Отказано', 'danger', 60),
        ('closed', 'Закрыто', 'dark', 70),
    ]

    for code, name, color, order in defaults:
        Status.objects.update_or_create(
            code=code,
            defaults={'name': name, 'color': color, 'order': order},
        )

    new_status = Status.objects.get(code='new')
    Appeal.objects.filter(status__isnull=True).update(status=new_status)


class Migration(migrations.Migration):

    dependencies = [
        ('appeals', '0003_alter_appeal_status'),
    ]

    operations = [
        migrations.RunPython(bootstrap_statuses_and_fill_nulls, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='appeal',
            name='status',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='appeals.status', verbose_name='Текущий статус'),
        ),
    ]
