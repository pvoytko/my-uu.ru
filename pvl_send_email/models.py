# -*- coding: utf-8 -*-
from django.db import models
from django.contrib import admin
import django.conf
import my_uu.plogic


class KEmailTemplate(models.Model):

    ket_descr = models.TextField(verbose_name=u'Когда высылается', )
    ket_caption = models.CharField(verbose_name=u'Название', max_length=255, unique=True)
    ket_subject = models.CharField(verbose_name=u'Тема письма', max_length=255)
    ket_html = models.TextField(verbose_name=u'Текст письма', )

    class Meta:
        verbose_name=u'Шаблон письма'
        verbose_name_plural=u'Шаблоны писем'

    # используется для отображения какой шаблон отправить
    def __unicode__(self):
        return self.ket_caption


class KEmailTemplateAdmin(admin.ModelAdmin):

    # Только с ролью админа можно входить на эту страницу
    get_urls = my_uu.plogic.getDjangoAdminUrlsWithAdminCheck()

    list_display = (
        'ket_caption',
        'ket_subject',
        'ket_descr',
    )

    # Тут задаем порядок - описание выше
    fields = [
        'ket_descr',
        'ket_caption',
        'ket_subject',
        'ket_html',
    ]

    # В основной копии только для чтения описание (редаить может только программмист)
    readonly_fields = [ ] if django.conf.settings.INSTANCE_SPECIFIC_ADD_EMAIL_TEMPLATES else [ 'ket_descr' ]

    # Удалякм из стандартного интерфейса джанго-админки пакетное удаление
    def get_actions(self, request):
        actions = admin.ModelAdmin.get_actions(self, request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    # Удалякм из стандартного интерфейса джанго-админки кнопку добавлкения и удаления
    def has_add_permission(self, request, obj=None):
        return django.conf.settings.INSTANCE_SPECIFIC_ADD_EMAIL_TEMPLATES
    def has_delete_permission(self, request, obj=None):
        return django.conf.settings.INSTANCE_SPECIFIC_ADD_EMAIL_TEMPLATES

    # Ширину поля задаем больше чем стандартная
    def formfield_for_dbfield(self, db_field, **kwargs):
        f = super(KEmailTemplateAdmin, self).formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'ket_html':
            f.widget.attrs['rows'] = 10
        return f


admin.site.register(KEmailTemplate, KEmailTemplateAdmin)

