# -*- coding: utf-8 -*-
from django.db import models
import django.contrib.auth.models
from django.core.validators import MinLengthValidator

class Account(models.Model):
    user = models.ForeignKey(django.contrib.auth.models.User)
    name = models.CharField(max_length=255, unique=True, error_messages={
        'unique': u'Такое название счета уже есть в системе.',
        'blank': u'Название счета не должно быть пустым.',
        'max_length': u'Название счета не должно быть более 255 символов длинной.'
    })

class Category(models.Model):
    user = models.ForeignKey(django.contrib.auth.models.User)
    name = models.CharField(max_length=255, unique=True)

class UType(models.Model):
    name = models.CharField(max_length=255, unique=True)

class Uchet(models.Model):

    user = models.ForeignKey(django.contrib.auth.models.User)
    date = models.DateField()
    utype = models.ForeignKey(UType)
    sum = models.DecimalField(max_digits=11, decimal_places=2)
    account = models.ForeignKey(Account)
    category = models.ForeignKey(Category)
    comment = models.CharField(max_length=1024)

    def dateDDMMYYYY(self):
        return self.date.strftime('%d.%m.%Y')