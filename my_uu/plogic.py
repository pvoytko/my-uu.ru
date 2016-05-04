# -*- coding: utf-8 -*-


import models


# получая на вход кверисет записей учета, и ID счета и категории, фильтрует кверисет
# по ним (если они не None) - испольузется для фильтрации записей учета на странице
# учета.
def filterUchetRecordsByPeriodAndAccountAndCategory(uchet_records_qs, period_id, account_id, category_id):
    if account_id:
        uchet_records_qs = uchet_records_qs.filter(account_id = account_id)
    if category_id:
        uchet_records_qs = uchet_records_qs.filter(category_id = category_id)
    if period_id:
        uchet_records_qs = filterUchetByViewPeriod(uchet_records_qs, period_id)
    return uchet_records_qs


# получает ID периода счета и категории из урл вида
# /lk/period/account/category/
# /lk/
# возвращает либо ID, либо None. А для периода всегда ID (last30, last3, 2014-02 и т.п.)
def getAccountIdAndCategoryIdFromUchetPageUrl(request_path):
    request_path
    parts = request_path.split('/')
    if len(parts) == 6:
        account_id = int(parts[3]) if (parts[3] and parts[3] != 'None') else None
        category_id = int(parts[4]) if (parts[4] and parts[4] != 'None') else None
        period_id = parts[2]
        return period_id, account_id, category_id
    if len(parts) == 3:
        return 'last30', None, None
    raise RuntimeError(u'Ошибка программирования. Должно быть или 3 части в пути или 6, раздеелнных "/" (слешем. '
                       u'Получено частей: {0}, путь: "{1}"'.format(len(parts), request_path))


# Фильтрует записи учета согласно выбранному фильтру дат
# Получает кверисет и код периода.
# Примеры кодов периода - см. convertPeriodCodeAndStartDateToPeriodId а так же, last3, last30
def filterUchetByViewPeriod(uchetRecords, period_id):

    import datetime
    import dateutil.relativedelta

    # Последние 3 дня, 30 дней
    if period_id in (models.UserProfile.VIEW_PERIOD_CODE_LAST3, models.UserProfile.VIEW_PERIOD_CODE_LAST30):
        lastIndex = 3 if period_id == models.UserProfile.VIEW_PERIOD_CODE_LAST3 else 30
        lastDates = list(uchetRecords.values_list('date', flat=True).distinct().order_by('-date')[0:lastIndex])

        # Тут важно возвращать не пустой список а пустой квери сет, т.к. к нему применяются ордер бай потом и пр.
        # а если пустой список будем возвращать то эксепшен там получим.
        if len(lastDates) == 0:
            return uchetRecords

        return uchetRecords.filter(date__gte = lastDates[-1])

    # День
    elif period_id.startswith('d'):
        date_parsed = datetime.datetime.strptime(period_id[1:], '%d.%m.%Y').date()
        return uchetRecords.filter(date = date_parsed)

    # Неделя
    elif period_id.startswith('w'):
        year, week = period_id[1:].split('-')
        year, week = int(year), int(week)

        # Сегодня 4 мая 2016
        # Это 18 неделя если использовать функцию getWeekNumberOfYear
        # Если использовать strptime то для 18-й недли возвращет дату 2016-05-02 00:00:00 т.е. 2 мая, то что надо

        # ИСточник - http://stackoverflow.com/questions/17087314/get-date-from-week-number
        d1 = datetime.datetime.strptime('{y}-{w}-0'.format(y = year, w = week), "%Y-%U-%w")
        d2 = d1 + datetime.timedelta(days=6)
        return uchetRecords.filter(date__gte = d1, date__lte = d2)

    # Месяц
    elif period_id.startswith('m'):
        year, month = period_id[1:].split('-')
        year, month = int(year), int(month)
        d1 = datetime.date(year, month, 1)
        d2 = d1 + dateutil.relativedelta.relativedelta(months=1) - datetime.timedelta(days=1)
        return uchetRecords.filter(date__gte = d1, date__lte = d2)

    # Квартал
    elif period_id.startswith('q'):
        year, quart = period_id[1:].split('-')
        year, quart = int(year), int(quart)
        d1 = datetime.date(year, (quart-1)*3 + 1, 1)
        d2 = datetime.date(year, (quart)*3 + 1, 1) - datetime.timedelta(days=1)
        return uchetRecords.filter(date__gte = d1, date__lte = d2)

    raise RuntimeError(u'Ошибка. Неподдерживаемый ID периода "{id}"'.format(id = period_id))





# Возвращает все UchetRecords для этого юзера
# Используется для получения записей учета для отображения на станице учета.
def getUserUchetRecords(user):
    urecs = models.Uchet.objects.filter(user=user).order_by('date', '-utype', 'id')
    return urecs


# Получая дату, возвращает номер недели.
def getWeekNumberOfYear(date):
    return date.isocalendar()[1]


# получая на вход дату и код периода (quart, week, month, day) - на их основе вычисляет id периода)
# примеры
#     "Неделя 14 2016" (урл - w2016-14)
#     или
#     "24 апр Вс 2016" (d2016.12.01)
#     или
#     "Февраль 2016" (m2013-02)
#     или
#     "I - 2016" (q2013-1)
def convertPeriodCodeAndStartDateToPeriodId(period_code, start_date):

    import views

    if period_code == u'day':
        return start_date.strftime('d%d.%m.%Y')
    elif period_code == u'week':
        return "w{0}-{1}".format(start_date.strftime('%Y'), getWeekNumberOfYear(start_date))
    elif period_code == u'month':
        return "m{0}-{1:02}".format(start_date.year, start_date.month)
    elif period_code == u'quart':
        return "q{0}-{1}".format(start_date.year, views.getQuartNumber(start_date))

    raise RuntimeError(u'Неизвестный код периода')


# Для группировки в анализе - преобразовать имя категории к имени группы.
# "Еда -- Столовая" станет "[Еда]"
# "Жилье" станет "Жилье"
def convertCategoryNameToGroupNameIfGrouping(cat_name, is_grouping):
    if is_grouping and '--' in cat_name:
        cat_name = cat_name.split('--', 1)[0].strip()
        return u"[{0}]".format(cat_name)
    return cat_name