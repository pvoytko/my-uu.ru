# -*- coding: utf-8 -*-

from subprocess import call, Popen, PIPE
import os

def isNonVersioned(ll):
    for l in ll:
        if l.startswith('?'):
            return True
    return False

def isForCommit(ll):
    return len(ll) > 0

def cs(ustr):
    return (u'd>> {0}'.format(ustr)).encode('cp866')

# Добавление если надо
res = Popen("hg status", stdout=PIPE, shell=True).stdout.read().strip()
print 'd>> hg status'
if res:
    print res
if isNonVersioned(res):
    a = raw_input(cs(u'Добавить в репозиторий (y/N)?'))
    if a == 'y':
        os.system("hg add")
        print cs(u'Добавление сделано.')
else:
    print cs(u'Все файлы под управлением СКВ.')

# Коммит
if isForCommit(res):
    a = raw_input(cs(u'Введите сообщение для коммита: '))
    if a:
        os.system("hg commit -m '{0}'".format(a))
        print cs(u'Комит сделан.')
else:
    print cs(u'Комитить нечего.')
