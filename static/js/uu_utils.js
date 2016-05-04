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
