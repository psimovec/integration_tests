# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2018-03-05 16:47


from django.db import migrations, models


def add_type_to_appliance_pool(apps, schema_editor):
    AppliancePool = apps.get_model("appliances", "AppliancePool")  # noqa
    # So, not container, VM as usual
    AppliancePool.objects.using(schema_editor.connection.alias)\
        .filter(is_container=False)\
        .update(template_type='virtual_machine')
    # container == True - docker
    AppliancePool.objects.using(schema_editor.connection.alias)\
        .filter(is_container=True)\
        .update(template_type='docker_vm')


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0050_template_template_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliancepool',
            name='template_type',
            field=models.CharField(choices=[(b'virtual_machine', b'Virtual Machine'),
                                            (b'docker_vm', b'VM-based Docker container'),
                                            (b'openshift_pod', b'Openshift pod')],
                                   default=b'virtual_machine', max_length=24),
        ),
        migrations.RunPython(add_type_to_appliance_pool),
    ]
