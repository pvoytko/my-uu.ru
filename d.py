# -*- coding: utf-8 -*-

from subprocess import call, Popen, PIPE
import os

def isNonVersioned(ll):
    for l in ll:
        if l.startswith('?'):
            return True
    return False

def cs(ustr):
    return ustr.encode('cp866')

# Добавление если надо
res = Popen("hg status", stdout=PIPE, shell=True).stdout.read()
print 'd>> hg status'
print res.strip()
if isNonVersioned(res):
    a = raw_input(cs(u'd>> Добавить в репозиторий (y/N)?'))
    if a == 'y':
        os.system("hg add")
else:
    print cs(u'd>> Все файлы под управлением СКВ.')

# Коммит
a = raw_input(cs(u'd>> Введите сообщение для коммита: '))
if a:
    os.system("hg commit -m '{0}'".format(a))