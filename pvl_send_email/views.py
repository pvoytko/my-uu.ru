#-*- coding: utf-8 -*-


import my_uu.models
import my_uu.plogic
import annoying.decorators
import django.forms
import django.contrib.messages
import models


# Страница для отправки тестового емейла
@my_uu.plogic.loginRequiredHttp
@my_uu.plogic.roleRequiredHttp(my_uu.models.UROLE_ADMIN)
@annoying.decorators.render_to('page_vtestemail.html')
def page_vtestemail(request):

    # Проверка валидности ввода
    class SiliSendEmailForm(django.forms.Form):
        ssef_email = django.forms.EmailField(label=u'Адрес эл. почты')
        ssef_template = django.forms.ModelChoiceField(label=u'Шаблон', queryset=models.KEmailTemplate.objects.all())

    form = SiliSendEmailForm()

    if request.POST:

        form = SiliSendEmailForm(request.POST)
        if form.is_valid():

            my_uu.plogic.sendEmailByTemplate(
                form.cleaned_data['ssef_template'].id,
                form.cleaned_data['ssef_email'],
                { },
                disable_render=True,
                )

            txt = u"Отправка произведена успешно."
            django.contrib.messages.add_message(request, django.contrib.messages.INFO, txt)

    return {
        'pse_form': form
    }


