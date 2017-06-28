#-*- coding: utf-8 -*-

import django.template
import django.core.urlresolvers
import my_uu.plogic


register = django.template.Library()


# возвращает true если юзер авторизован
@register.simple_tag(takes_context=True)
def seom_is_user_authorized(context):
    request = context['request']
    return my_uu.plogic.isAuthorizedUser(request)


@register.simple_tag(takes_context=True)
def seom_main_menu(context):
    request = context['request']

    # Список всех пунктов меню - админа
    admin_menu_itesm = [
        {
            'smm_caption': u'Тестовая страница',
            'smm_url': django.core.urlresolvers.reverse('my_uu.views.page_mtestempty'),
        },
        {
            'smm_caption': u'Тест модели',
            'smm_url': django.core.urlresolvers.reverse('admin:my_uu_testmodel_changelist'),
        },
        {
            'smm_caption': u'Тестовый емейл',
            'smm_url': django.core.urlresolvers.reverse('pvl_send_email.views.page_vtestemail'),
        },
        {
            'smm_caption': u'Шаблоны писем',
            'smm_url': '/lk/pvl_send_email/kemailtemplate/',
            'smm_url': django.core.urlresolvers.reverse('admin:pvl_send_email_kemailtemplate_changelist'),
        },
    ]

    # Выставляем флак что пункт текущий если текущий урл начинается с его урла
    for mi in admin_menu_itesm:
        mi['smm_is_current_now'] = request.path.startswith(mi['smm_url'])

    return admin_menu_itesm