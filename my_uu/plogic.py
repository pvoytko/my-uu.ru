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


# возвращает true елси пользователь ранее ввел корректные логин и пароль и сейчас авторизован
def isAuthorizedUser(request):
    return request.user.is_authenticated()


# возвращает модель пользователя если он авторизвоан а если нет то кинет ошибку 500
def getAuthorizedUser(request):
    if not isAuthorizedUser(request):
        raise RuntimeError(u'Попытка обратится к объекту авторизованного ползователя, '
                           u'тогда как текущий пользователь не авторизован')
    return request.user


# Функция добавляет декоратор на проверку роли при открытии каждой страницы админки (добавить удалить редактировать ...)
# для модели. Если роли нет, вернет Forbidden HTTP ответ. Использование:
#     class MyModelAdmin(admin.ModelAdmin):
#
#     # Проверка перед открытием всех страниц что имеется роль админа
#     get_urls = getDjangoAdminUrlsWithAdminCheck()
def getDjangoAdminUrlsWithAdminCheck():

    def getUrlsWrapper(model_admin):

        from django.conf.urls import url

        def wrap(view):
            from functools import update_wrapper
            @loginRequiredHttp
            @roleRequiredHttp(models.UROLE_ADMIN)
            def wrapper(*args, **kwargs):
                return model_admin.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        info = model_admin.model._meta.app_label, model_admin.model._meta.model_name

        urlpatterns = [
            url(r'^$', wrap(model_admin.changelist_view), name='%s_%s_changelist' % info),
            url(r'^add/$', wrap(model_admin.add_view), name='%s_%s_add' % info),
            url(r'^(.+)/history/$', wrap(model_admin.history_view), name='%s_%s_history' % info),
            url(r'^(.+)/delete/$', wrap(model_admin.delete_view), name='%s_%s_delete' % info),
            url(r'^(.+)/$', wrap(model_admin.change_view), name='%s_%s_change' % info),
            ]
        return urlpatterns

    return getUrlsWrapper


# Декоратор на проверку что в сессии хранится ID авторизованного юзера
# Для использования во вью которые форируют HTML-страницы, т.к. возвращает HttpResponse
def loginRequiredHttp(f):
    def loginRequiredWrapperFunc(request, *args, **kwargs):
        if isAuthorizedUser(request):
            return f(request, *args, **kwargs)
        else:
            import django.conf
            from django.http import HttpResponseRedirect
        import urllib
        from django.core.urlresolvers import reverse
        redir_url = reverse('admin:login') + '?next=' + urllib.quote(request.path + request.META['QUERY_STRING'])
        return django.http.HttpResponseRedirect(redir_url)
    return loginRequiredWrapperFunc


# Декоратор на проверку что роль нужная, иначе возвращает 503 (для view страниц)
def roleRequiredHttp(*roles):
    def roleRequiredHttpDecor(f):
        def roleRequiredHttpWrapperFunc(request, *args, **kwargs):
            u = getAuthorizedUser(request)
            uRole = getUserRole(u)

            # Юзеру с ролью админ всегда разрешено.
            if uRole in roles or uRole == models.UROLE_ADMIN:
                return f(request, *args, **kwargs)
            else:
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden("Просмотр не разрешен.")
        return roleRequiredHttpWrapperFunc
    return roleRequiredHttpDecor


# Аналогичен loginRequiredHttp только делает raise при отутствии,
# для использования в ajax-вьюхах
def loginRequiredAssert(f):
    import functools
    @functools.wraps(f)
    def loginRequiredWrapperFunc(request, **kwargs):
        if isAuthorizedUser(request):
            return f(request, **kwargs)
        else:
            raise RuntimeError(u"Требуется авторизация")
    return loginRequiredWrapperFunc


# возвращает логин авторизованного пользователя, а если не авторизован, кинет ошибку.
def getAuthorizedUsername(request):
    u = getAuthorizedUser(request)
    return getUserUsername(u)


# возвращает логин авторизованного пользователя, а если не авторизован, кинет ошибку.
def getUserUsername(user):
    return getattr(user, user.USERNAME_FIELD)


# возвращает роль авторизованного пользователя
def getUserRole(user):
    if getUserUsername(user) == 'pvoytko@gmail.com':
        return models.UROLE_ADMIN
    else:
        return models.UROLE_USER


# Получая на вход модель шаблона письма и адрес получателя, эта функция высылает письмо.
# disable_render=True - блокирет подстановку переменных, высылает плейхолденры.
# ИСпользуется в разделе тестовой отправки емейла.
def sendEmailByTemplate(kemailtemplate_model_id, to_address, context, disable_render=False):

    import django.template
    import django.core.mail
    import pvl_send_email.models

    # Рендерим шаблон, получаем HTML тело сообщения
    kemailtemplate_model = pvl_send_email.models.KEmailTemplate.objects.get(id=kemailtemplate_model_id)
    subj = kemailtemplate_model.ket_subject
    htmlContent = replaceUlrsWithLinks(kemailtemplate_model.ket_html)
    if not disable_render:
        htmlContent = django.template.Template(htmlContent).render(django.template.Context(context))

    # Отправляем HTML тело сообщения и текстовую версию тоже.
    # Тут отпрваляется две версии, т.к. иначе сервис http://www.mail-tester.com/web-zbUSCp
    # выдает минус 1 балл. скрин http://pvoytko.ru/jx/5GMrRyngzu
    # html версия добавляется последней, т.к. вэ том случае она предпочтительная, что
    # сказано в по этой ссылке http://stackoverflow.com/a/882770/1412586 скрин http://pvoytko.ru/jx/KmXz2OmyEf
    import html2text
    text_content = html2text.html2text(htmlContent)
    msg = django.core.mail.EmailMultiAlternatives(subj, text_content, 'support2@my-uu.ru', [to_address])
    msg.attach_alternative(htmlContent, "text/html")
    msg.send()


# получая текст, форматирует его как HTML (используется при отправке писчем на основе текстового шаблона)
def replaceUlrsWithLinks(text):

    # Замера урлов на ссылки
    # word-break:break-all; для того чтобы длиные ссылки
    # не расширяли страницу а обрезались посредине
    # скобки.
    # Для этого перебор всех урлов.
    # И если урл кончается символов знака препинания его выносим за ссылку.
    import re
    urls_pat = re.compile(r"((https?):((//)|(\\\\))+[\w\d:#@%/;$~_?\+-=\\\.&\[\]]*)([)]?)", re.MULTILINE|re.UNICODE|re.IGNORECASE)
    new_text = u""
    last_pos = 0
    for url_mo in re.finditer(urls_pat, text):
        url = url_mo.group()
        url_last = u""
        while url.endswith(')') or url.endswith('.') or url.endswith(':'):
            url_last += url[-1]
            url = url[0:-1]
        a_elem = u'<a style="word-break:break-all;" href="{0}" class="underline" target="_blank">{0}</a>{1}'.format(url, url_last)
        new_text += text[last_pos:url_mo.start()] + a_elem
        last_pos = url_mo.end()
    new_text += text[last_pos:]
    text = new_text

    # Вставляем br, переводы строки оставляем, т.к. на них ориентируется следующее рег. выражение.
    # \u2823 - это юникод-символ line separator http://www.fileformat.info/info/unicode/char/2028/index.htm
    # с какого-то момента Скайп стал их присылать (в сообщениях dJON клиента) например 6193:
    # http://pvoytko.ru/dj-admin/pvoytko/clientcontact/6193/?_changelist_filters=p%3D1
    # если их не заменять то строки сливаются.
    text = text.replace("\n", '<br />\n')
    text = text.replace(u"\u2028", u'<br />\n')

    # Заменяем пустрые строки. Например, текст может быть таким:
    # --
    # Пример списка<br />
    #      Пример итема<br />
    #      Пример итема<br />
    # --
    # Если такой текст вставить в DIV в HTML, то пробелы до итемов удалятся и он отобразится так:
    # --
    # Пример списка<br />
    # Пример итема<br />
    # Пример итема<br />
    # --
    # Чтобы сохранить пробелы - заменяем все пробелы в количстве 2 и более таким же кол-вом неразрывных пробелов.
    # А вначале строки заменяем один и более пробел неразрывными.
    # Не заменяем все пробелы т.к. пробелы между словами пусть остаются разрывными, чтобы нормально строки
    # отображались.
    text = re.sub('(\s{2,})', lambda s: '&nbsp;' * len(s.group(1)), text)
    text = re.sub('^(\s{1,})', lambda s: '&nbsp;' * len(s.group(1)), text)

    return text

