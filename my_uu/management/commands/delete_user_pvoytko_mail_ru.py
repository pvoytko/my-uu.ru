# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

class Command(BaseCommand):

    def handle(self, *args, **options):
        u = User.objects.get(username='pvoytko@mail.ru')
        uId = u.id
        u.delete()
        print u'User pvoytko@mail.ru (#{0}) deleted'.format(uId)
