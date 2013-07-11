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
    localizationobj.emptydatastring = "Нет ни одной записи учета для отображения.";
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