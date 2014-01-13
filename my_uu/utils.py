# -*- coding: utf-8 -*-
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse
from django.conf import settings



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

    # На отладческой машине в качестве емейл бекенда установлена запись в файл.

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
    feedbackRequestUrl = 'http://my-uu.ru' + reverse('my_uu.views.feedback_request', kwargs={'obfuscatedUserId': userObfuscatedId})
    sendHtmlEmailFromSupport(
        userEmail,
        u'[my-uu.ru] Просьба сообщить Ваш отзыв о сервисе',
        'email_feedback_request.html',
        { 'unsubscrUrl': unsubscrUrl }
    )


# Отправляет запрос на улучшение
def sendImprooveEmail(userId, userEmailFrom, improoveText):
    sendHtmlEmailFromSupport(
        'pvoytko@gmail.com',
        u'[my-uu.ru] Запрос на улучшение сервиса',
        'email_improove.html',
        {
            'userId': userId,
            'userEmail': userEmailFrom,
            'improoveText': improoveText
        }
    )


# Отправляет запрос на улучшение
def sendFeedbackEmail(userId, userEmailFrom, text):
    sendHtmlEmailFromSupport(
        'pvoytko@gmail.com',
        u'[my-uu.ru] Что искали и не нашли',
        'email_feedback.html',
        {
            'userId': userId,
            'userEmail': userEmailFrom,
            'text': text
        }
    )

# Получая число возвращает строку
def formatMoneyValue(mval):
    def group(number):
        s = '%d' % number
        groups = []
        while s and s[-1].isdigit():
            groups.append(s[-3:])
            s = s[:-3]
        return s + ' '.join(reversed(groups))
    return "{0} р.".format(group(round(mval, 0)))
