# -*- coding: utf-8 -*-

from django.conf.urls import patterns, include, url

urlpatterns = patterns('',

    # Главная сервиса
    url(r'^$', 'my_uu.views.main'),

    # Регистрация логин и выход
    url(r'^register_user/$', 'my_uu.views.register_user_ajax'),
    url(r'^login_user/$', 'my_uu.views.login_user_ajax'),
    url(r'^logout_user/$', 'my_uu.views.logout_user' ),
    url(r'^begin/$', 'my_uu.views.begin'),

    # Личный кабинет учет
    url(r'^lk/$', 'my_uu.views.lk_uch'),
    url(r'^lk/save_uchet_ajax/$', 'my_uu.views.lk_save_uchet_ajax'),
    url(r'^lk/delete_uchet_ajax/$', 'my_uu.views.lk_delete_uchet_ajax'),

    # Личный кабинет анализ
    url(r'^lk/ana/$', 'my_uu.views.lk_ana'),

    # Личный кабинет настройки
    url(r'^lk/set/$', 'my_uu.views.lk_set'),
    url(r'^lk/save_account_ajax/$', 'my_uu.views.lk_save_account_ajax'),
    url(r'^lk/delete_account_ajax/$', 'my_uu.views.lk_delete_account_ajax'),
    url(r'^lk/save_category_ajax/$', 'my_uu.views.lk_save_category_ajax'),
    url(r'^lk/delete_category_ajax/$', 'my_uu.views.lk_delete_category_ajax'),
    url(r'^lk/imp/$', 'my_uu.views.lk_imp'),
    url(r'^lk/imp_ajax/$', 'my_uu.views.lk_imp_ajax'),

    # Административная часть
    url(r'^adm/act/$', 'my_uu.views.adm_act'),
    url(r'^adm/exp/$', 'my_uu.views.adm_exp'),
)

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()