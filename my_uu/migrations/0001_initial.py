# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-06-28 00:15
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(error_messages={b'blank': '\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u0441\u0447\u0435\u0442\u0430 \u043d\u0435 \u0434\u043e\u043b\u0436\u043d\u043e \u0431\u044b\u0442\u044c \u043f\u0443\u0441\u0442\u044b\u043c.', b'max_length': '\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u0441\u0447\u0435\u0442\u0430 \u043d\u0435 \u0434\u043e\u043b\u0436\u043d\u043e \u0431\u044b\u0442\u044c \u0431\u043e\u043b\u0435\u0435 255 \u0441\u0438\u043c\u0432\u043e\u043b\u043e\u0432 \u0434\u043b\u0438\u043d\u043d\u043e\u0439.'}, max_length=255)),
                ('balance_start', models.DecimalField(decimal_places=2, default=0, max_digits=11)),
                ('visible', models.BooleanField(default=True)),
                ('position', models.PositiveIntegerField(default=1000)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(error_messages={b'blank': '\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u0438 \u043d\u0435 \u0434\u043e\u043b\u0436\u043d\u043e \u0431\u044b\u0442\u044c \u043f\u0443\u0441\u0442\u044b\u043c.', b'max_length': '\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u0438 \u043d\u0435 \u0434\u043e\u043b\u0436\u043d\u043e \u0431\u044b\u0442\u044c \u0431\u043e\u043b\u0435\u0435 255 \u0441\u0438\u043c\u0432\u043e\u043b\u043e\u0432 \u0434\u043b\u0438\u043d\u043d\u043e\u0439.'}, max_length=255)),
                ('visible', models.BooleanField(default=True)),
                ('position', models.PositiveIntegerField(default=1000)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='EventLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime', models.DateTimeField(auto_now_add=True)),
                ('event2', models.IntegerField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='FeedbackRequested',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ManualSteps',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime_subscribe', models.DateTimeField(null=True)),
                ('datetime_cancel', models.DateTimeField(null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sum', models.DecimalField(decimal_places=2, max_digits=5)),
                ('date_created', models.DateTimeField()),
                ('date_payment', models.DateTimeField(null=True)),
                ('days', models.PositiveIntegerField()),
                ('date_from', models.DateField(null=True)),
                ('date_to', models.DateField(null=True)),
                ('zpayment_type_code', models.CharField(max_length=50, null=True)),
                ('sum_seller', models.DecimalField(decimal_places=2, max_digits=5, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='TestModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tm_cap', models.CharField(max_length=128)),
                ('tm_cap2', models.CharField(max_length=128, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Uchet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('sum', models.DecimalField(decimal_places=2, max_digits=11)),
                ('comment', models.CharField(max_length=1024)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='my_uu.Account')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='my_uu.Category')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Unsubscribe',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('http_referer', models.CharField(blank=True, max_length=1024, null=True)),
                ('view_period_code', models.CharField(default=b'last3', max_length=10)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
            ],
        ),
        migrations.AddField(
            model_name='uchet',
            name='utype',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='my_uu.UType'),
        ),
        migrations.AlterUniqueTogether(
            name='category',
            unique_together=set([('user', 'name')]),
        ),
        migrations.AlterUniqueTogether(
            name='account',
            unique_together=set([('user', 'name')]),
        ),
    ]
