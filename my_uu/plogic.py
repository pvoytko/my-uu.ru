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
# 2014-02 и т.п., last3, last30,
def filterUchetByViewPeriod(uchetRecords, period_id):

    import datetime
    import dateutil.relativedelta

    # Спец. значения
    if period_id in (models.UserProfile.VIEW_PERIOD_CODE_LAST3, models.UserProfile.VIEW_PERIOD_CODE_LAST30):
        lastIndex = 3 if period_id == models.UserProfile.VIEW_PERIOD_CODE_LAST3 else 30
        lastDates = list(uchetRecords.values_list('date', flat=True).distinct().order_by('-date')[0:lastIndex])

        # Тут важно возвращать не пустой список а пустой квери сет, т.к. к нему применяются ордер бай потом и пр.
        # а если пустой список будем возвращать то эксепшен там получим.
        if len(lastDates) == 0:
            return uchetRecords

        return uchetRecords.filter(date__gte = lastDates[-1])

    # Месяц
    else:
        year, month = period_id.split('-')
        year, month = int(year), int(month)
        d1 = datetime.date(year, month, 1)
        d2 = d1 + dateutil.relativedelta.relativedelta(months=1) - datetime.timedelta(days=1)
        return uchetRecords.filter(date__gte = d1, date__lte = d2)


# Возвращает все UchetRecords для этого юзера
# Используется для получения записей учета для отображения на станице учета.
def getUserUchetRecords(user):
    urecs = models.Uchet.objects.filter(user=user).order_by('date', '-utype', 'id')
    return urecs

