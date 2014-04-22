# -*- coding: utf-8 -*-

from django.conf.urls import patterns, include, url
from django.conf import settings

urlpatterns = patterns('',

    # Главная сервиса
    url(r'^$', 'my_uu.views.main'),

    # Регистрация логин и выход
    url(r'^register_user/$', 'my_uu.views.register_user_ajax'),
    url(r'^login_user/$', 'my_uu.views.login_user_ajax'),
    url(r'^logout_user/$', 'my_uu.views.logout_user' ),
    url(r'^begin/$', 'my_uu.views.begin'),

    # Личный кабинет отправка "улучшить" с любой страницы
    url(r'^lk/improove_ajax/$', 'my_uu.views.lk_improove_ajax'),

    # Личный кабинет начало
    url(r'^lk/beg/$', 'my_uu.views.lk_beg'),

    # Личный кабинет учет
    url(r'^lk/$', 'my_uu.views.lk_uch'),
    url(r'^lk/save_uchet_ajax/$', 'my_uu.views.lk_save_uchet_ajax'),
    url(r'^lk/delete_uchet_ajax/$', 'my_uu.views.lk_delete_uchet_ajax'),
    url(r'^lk/load_uchet_ajax/$', 'my_uu.views.lk_load_uchet_ajax'),

    # Личный кабинет анализ
    url(r'^lk/ana/$', 'my_uu.views.lk_ana'),

    # Личный кабинет счета и категории
    url(r'^lk/acc/$', 'my_uu.views.lk_acc'),
    url(r'^lk/cat/$', 'my_uu.views.lk_cat'),
    url(r'^lk/save_account_ajax/$', 'my_uu.views.lk_save_account_ajax'),
    url(r'^lk/delete_account_ajax/$', 'my_uu.views.lk_delete_account_ajax'),
    url(r'^lk/save_accounts_order_ajax/$', 'my_uu.views.lk_save_accounts_order_ajax'),
    url(r'^lk/save_category_ajax/$', 'my_uu.views.lk_save_category_ajax'),
    url(r'^lk/delete_category_ajax/$', 'my_uu.views.lk_delete_category_ajax'),
    url(r'^lk/save_categories_order_ajax/$', 'my_uu.views.lk_save_categories_order_ajax'),

    # Личный кабинет импорт
    url(r'^lk/imp/$', 'my_uu.views.lk_imp'),
    url(r'^lk/imp_ajax/$', 'my_uu.views.lk_imp_ajax'),

    # Личный кабинет экспорт
    url(r'^lk/exp/$', 'my_uu.views.lk_exp'),
    url(r'^lk/exp_csv/$', 'my_uu.views.lk_exp_csv'),

    # Личный кабинет оплата (инфо об оплате, и страница возврата после оплаты и страница отмены и страница уведомления)
    url(r'^lk/pay/$', 'my_uu.views.lk_pay'),
    url(r'^robokassa_result_url/$', 'my_uu.views.robokassa_result_url'),
    url(r'^zpayment_result_url/$', 'my_uu.views.zpayment_result_url'),
    url(r'^do_order_ajax/$', 'my_uu.views.do_order_ajax'),

    # Административная часть (Павел Войтко)
    url(r'^adm/act/$', 'my_uu.views.adm_act'),
    url(r'^adm/exp/$', 'my_uu.views.adm_exp'),
    url(r'^adm/exp_reg/$', 'my_uu.views.adm_exp_reg'),
    url(r'^adm/test/$', 'my_uu.views.adm_test'),

    # Отписаться юзеру (без регистрации)
    url(r'^unsubscr/(?P<obfuscatedUserId>\d+)/$', 'my_uu.views.unsubscr_view'),
    url(r'^unsubscr/(?P<obfuscatedUserId>\d+)/do/$', 'my_uu.views.unsubscr_do'),

    # Страница для получения ОС почему не стали пользоваться
    url(r'^feedback_request/(?P<obfuscatedUserId>\d+)/$', 'my_uu.views.feedback_request'),
    url(r'^feedback_request_ajax/$', 'my_uu.views.feedback_request_ajax'),

    # Активация магазина в Z-PAYMENT
    url(r'^ZP86478908.HTML$',  'django.views.static.serve', {'document_root': settings.PROJECT_DIR, 'path': '/static/ZP86478908.HTML' }),

)

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()