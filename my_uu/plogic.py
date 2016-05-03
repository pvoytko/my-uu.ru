# -*- coding: utf-8 -*-


import models


# получая на вход кверисет записей учета, и ID счета и категории, фильтрует кверисет
# по ним (если они не None) - испольузется для фильтрации записей учета на странице
# учета.
def filterUchetRecordsByAccountAndCategory(uchet_records_qs, account_id, category_id):
    if account_id:
        uchet_records_qs = uchet_records_qs.filter(account_id = account_id)
    if category_id:
        uchet_records_qs = uchet_records_qs.filter(category_id = category_id)
    return uchet_records_qs


# получает ID счета и категории из урл вида
# /lk/period/account/category/
# /lk/
# возвращает либо ID, либо None
def getAccountIdAndCategoryIdFromUchetPageUrl(request_path):
    request_path
    parts = request_path.split('/')
    if len(parts) == 6:
        account_id = int(parts[3]) if (parts[3] and parts[3] != 'None') else None
        category_id = int(parts[4]) if (parts[4] and parts[4] != 'None') else None
        return account_id, category_id
    if len(parts) == 3:
        return None, None
    raise RuntimeError(u'Ошибка программирования. Должно быть или 3 части в пути или 6, раздеелнных "/" (слешем. '
                       u'Получено частей: {0}, путь: "{1}"'.format(len(parts), request_path))