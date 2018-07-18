// Принимая на вход дробное значение добавляет в него группы, запятую и символ р.
function uuFormatCurrency(currencyValue, digitsAfterPoint) {
    function numberWithGroups(x) {
        return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    }
    var digits = ((digitsAfterPoint == undefined ) || (digitsAfterPoint == true)) ? 2 : 0;
    var withGroupsValue = numberWithGroups(currencyValue.toFixed(digits));
    var withCommaValue = withGroupsValue.replace('.', ',');
    var withRoubleValue = withCommaValue + " р.";
    return withRoubleValue;
}


// Полчая на вход ID грида подменяет в нем строки на русскоязычные
function uuLocalizeJqxGrid(jqxGridElemId) {
    var localizationobj = {};
    localizationobj.emptydatastring = "Не найдено операций учета для отображения. Для добавления кликните кнопку «Внести» ниже (или «Ins» на клавиатуре).  ";
    localizationobj.loadtext = "Загрузка...";
    $("#" + jqxGridElemId).jqxGrid('localizestrings', localizationobj);
}


// При загрузке модуля меняем строки в moment и теперь он форматирует даты так как надо нам.
moment.lang('en', {
    weekdays : [
        "Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"
    ],
    monthsShort : [
        "янв", "фев", "мар", "апр", "май", "июн",
        "июл", "авг", "сен", "окт", "ноя", "дек"
    ]
});


// Получая номер недели, возвращает дату. Примеры возвратов:
// 8 - 14 июл
// 29 июл - 4 авг
function uuFormatWeekNumberToDates(weekNumber) {
    var m1 = moment().isoWeek(weekNumber).day(1);
    var m2 = moment().isoWeek(weekNumber).day(7);
    var startDate = (m1.month() == m2.month()) ? m1.format('D') : m1.format('D MMM');
    var endDate = m2.format('D MMM');
    return startDate + "–" + endDate;
}


// Проверяет строковое значение суммы, если ошибка ввода, вернет ее текст.
// === true если корректно
function uuValidateSum(floatStr) {
    floatVal = parseFloat(String(floatStr).replace(',', '.'));
    if (isNaN(floatVal)){
        return "Сумма должна иметь формат (+-NNN или +-NNN.,NN)";
    }
    return true;
}


// Проверяет строковое значение даты, если ошибка ввода, вернет ее текст.
// === true если корректно
function uuValidateDate(dateStr) {

    if (!(dateStr.match(/\d\d.\d\d.\d\d\d\d/))) {
        return "Дата должна иметь формат ДД.ММ.ГГГГ";
    }
    if (!moment(dateStr, 'DD.MM.YYYY').isValid()) {
        return "Указанное значение не является верной датой в формате ДД.ММ.ГГГГ";
    }
    return true;
}


// Делает редирект браузера на страницу анализа или учета, с переданными значениями фильтров.
// Для примера см. метса использования функции.
function goToUchOrAnaUrl(url_part2, url_part3, url_part4, is_ana){

    if (is_ana){
        var url_part1_init = 'lk/ana';
        var url_part2_init = 'rashod';
        var url_part3_init = 'day';
        var url_part4_init = 'nogroup';
    }else{
        var url_part1_init = 'lk';
        var url_part2_init = 'last30';
        var url_part3_init = 'None';
        var url_part4_init = 'None';
    }

    // Изначально None
    var parts = new Array(url_part1_init, url_part2_init, url_part3_init, url_part4_init);

    var max_parts = is_ana ? 7 : 6;
    var min_parts = is_ana ? 4 : 3;
    var start_part = is_ana ? 3 : 2;

    // Если естьв урл, берем из урл.
    // урл вида /lk/period/acc/cat/
    var parts_url = window.location.pathname.split('/');
    if (parts_url.length == max_parts){
        parts[1] = parts_url[start_part];
        parts[2] = parts_url[start_part+1];
        parts[3] = parts_url[start_part+2];

    // урл вида /lk/ - ничего не делаем.
    } else if (parts_url.length == min_parts){

    // других урл для старницы учяета быть не дожно.
    } else {
        alert('Ошибка программирования 1.');
    };

    // Если они указаны в аргументе, берем их оттуда.
    parts[1] = url_part2 ? url_part2 : parts[1];
    parts[2] = url_part3 ? url_part3 : parts[2];
    parts[3] = url_part4 ? url_part4 : parts[3];

    // Итог
    var new_url = '/' + parts.join('/') + '/';

    // Переход
    window.location.href = new_url;
}


/*
Ш-7338 Добавляет параметр к УРЛ
Источник http://stackoverflow.com/a/13064060/1412586
Было
    http://95.213.159.169:8001/dashboard/make_request/?test=test1&a=3
1. Вызываем:
    url = pvlGetUrlReplaceParam(url, 'test', 'test2');
    Стало
    http://95.213.159.169:8001/dashboard/make_request/?test=test2&a=3
2. Вызываем:
    url = pvlGetUrlReplaceParam(url, 'test', '');
    Стало
    http://95.213.159.169:8001/dashboard/make_request/?test=&a=3
3. Вызываем:
    url = pvlGetUrlReplaceParam(url, 'test', '', true);
    Стало
    http://95.213.159.169:8001/dashboard/make_request/?a=3
*/
function pvlGetUrlReplaceParam(url, param_name, new_value, is_del_if_empty) {

    // Если оно null, то пустая стрка, а не значение "null"
    // Тут важно использовать encodeURIComponent т.к. если new_value содержит например % то урл будет  не верным без этого.
    var new_value_or_empty = new_value ? encodeURIComponent(new_value) : "";

    var hash = location.hash;
    url = url.replace(hash, '');

    // параметра уже есть в УРЛ
    if (url.indexOf(param_name + "=") >= 0)
    {
        var prefix = url.substring(0, url.indexOf(param_name));
        var suffix = url.substring(url.indexOf(param_name));
        suffix = suffix.substring(suffix.indexOf("=") + 1);
        suffix = (suffix.indexOf("&") >= 0) ? suffix.substring(suffix.indexOf("&")) : "";

        // Если при пустом значнии удалить праметр, то
        if (!new_value_or_empty && is_del_if_empty){

            // Случай когда урл остается такой
            // http://95.213.159.169:8001/dashboard/?
            // то удаляем последний знак вопроса
            if (prefix[prefix.length-1] == '?'){
                prefix = prefix.substr(0, prefix.length-1);
            }
            url = prefix + suffix;

        // Если при пустом значнии оставить праметр, то
        } else {
            url = prefix + param_name + "=" + new_value_or_empty + suffix;
        }

    }

    // параметра еще нет в УРЛ
    else
    {

        // Если при пустом значнии удалить праметр, то
        if (!new_value_or_empty && is_del_if_empty){

            // ничего не делаем, т.к. его итак нет.

        // Если при пустом значнии оставить праметр, то
        } else {

            // добавляем параметр
            if (url.indexOf("?") < 0)
                url += "?" + param_name + "=" + new_value_or_empty;
            else
                url += "&" + param_name + "=" + new_value_or_empty;
        }
    }
    return url + hash;
}


// Источник http://stackoverflow.com/a/901144/1412586
// Ш-7338
function getParameterByName(name, url) {
    if (!url) url = window.location.href;
    name = name.replace(/[\[\]]/g, "\\$&");
    var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
        results = regex.exec(url);
    if (!results) return null;
    if (!results[2]) return '';
    return decodeURIComponent(results[2].replace(/\+/g, " "));
}