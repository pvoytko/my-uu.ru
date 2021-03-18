# -*- coding: utf-8 -*-


# Возвращает True для Питона версии 3.N
# Возвращает False для Питона версии 2.N
# Ш-7578
def isPython3AndGreater():
    import sys
    return not(sys.version_info < (3,))


# Возвращает True для Джанго версии 2.N и выше
# Возвращает False для Джанго версии до 2.N (1.11, 1.9 и т.п)
# Ш-7578
def isDjango2AndGreater():
    import django
    if django.VERSION[0:2] < (2, 0):
        return False
    else:
        return True


# УРЛ по имени независимо от версии джанго - 2 или ниже
def getUrlByName(url_name, **kwargs):
    if isDjango2AndGreater():
        from django.urls import reverse
    else:
        from django.core.urlresolvers import reverse

    return reverse(url_name, **kwargs)


# И в 3 и 2 версии питона вернет юникод, во 2-й - с преобразованием, в 3-й - просто как есть.
# источник - http://python3porting.com/noconv.html
# На вход принимает:
# str - строка
# unicode - юникод
# а так же типы к которым применим вызов str или unicode например int,
#     это нужно для того, что например если печатаем и хотим преобразовать к юникоду последовательность
#     аргументов rpint, то среди них может быть как int, так и float, так и строки,
#     а нам надо все преобразовать к строке,
#     чтобы не было ткой ошибки http://pvoytko.ru/jx/nzpknkMdZT
#     вот в таком коде http://pvoytko.ru/jx/Fvge4SwE5S
# Ш-7572
def pvlUnicode2and3(x):
    import sys
    if sys.version_info < (3,):

        # В svir из формы приходит тип unicode уже
        # если его пытаться преобразовать к строке, то ошибка,
        # выглядит так, http://pvoytko.ru/jx/4ZKm95Cav9
        # поэтому проверка.

        if type(x) == unicode:
            return x
        else:

            # Раньше был такой код
            # но он давал ошибку. В KSEA2 проекте, при оптравке формы заявки.
            # import codecs
            # return codecs.unicode_escape_decode(unicode(x))[0]
            # Пример ошибки: http://pvoytko.ru/jx/UUjczy2sCh
            # поэтому переделано.
            return unicode(x)

    else:
        return str(x)
