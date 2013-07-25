# -*- coding: utf-8 -*-
from django.core.mail.message import EmailMessage
from django.core.urlresolvers import reverse



# 10 = 27652776 (pvoytko@gmail.com)
def obfuscateId(id):
    return ((id << 5) ^ 3456789) << 3# Отправка письма
def restoreId(id):# Код взят из https://docs.djangoproject.com/en/dev/topics/email/
    return (((id >> 3) ^ 3456789) >> 5)


def sendHtmlEmailFromSupport(toEmail, subj, emailTemplateName, emailTemplateContextDict = {}):

    # Рендерим шаблон, получаем HTML тело сообщения
    from django.template.loader import get_template
    from django.template import Context
    htmly = get_template(emailTemplateName)
    c = Context(emailTemplateContextDict)
    htmlContent = htmly.render(c)

    # Отправляем HTML тело сообщения (BCC=pvoytko@gmail.com)
    msg = EmailMessage(subj, htmlContent, "support@my-uu.ru", [toEmail], ['pvoytko@gmail.com'])
    msg.content_subtype = "html"
    msg.send()


# Отправляет Email что регистрация завершена.
def sendEmailRegistrationPerformed(userEmail, userPassword):
    sendHtmlEmailFromSupport(
        userEmail,
        u'[my-uu.ru] Регистрация в сервисе Мой Удобный Учет',
        'email_registration_performed.html',
        {
            'userEmail': userEmail,
            'userPassword': userPassword
        }
    )


# Отправляет запрос на ОС
def sendFeedbackRequest(user):
    userEmail = user.email
    userObfuscatedId = obfuscateId(user.id)
    unsubscrUrl = 'http://my-uu.ru' + reverse('my_uu.views.unsubscr_view', kwargs={'obfuscatedUserId': userObfuscatedId})
    sendHtmlEmailFromSupport(
        'pvoytko@gmail.com',
        u'[my-uu.ru] Понравился ли Вам этот сервис?',
        'email_feedback_request.html',
        { 'unsubscrUrl': unsubscrUrl }
    )
