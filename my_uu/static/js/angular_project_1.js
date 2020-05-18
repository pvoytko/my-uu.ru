projectModule = angular.module('myNgApp',[]);

// Для Angular меняем две фигурные скобки на скобку и бакс (чтоб с шаблонами джанги различаться)
//angular.module('myNgApp').config(function($interpolateProvider) {
//    $interpolateProvider.startSymbol('{$');
//    $interpolateProvider.endSymbol('$}');
//});


// Ш-7226 Директива pv-tooltip-directive элемента с тултипом при наведении
angular.module('myNgApp').directive('pvTooltipDirective', function($sce) {
    return {
        restrict: "A",
        scope: {
            pvTooltipDirective: '='
        },
        link: function link($scope, element, attrs, controller, transcludeFn) {

            $scope.ptd_is_inited = false;

            //the $watch method also works because the '@' binding already does the interpolation
            //see: http://stackoverflow.com/a/12976630/582917 & http://stackoverflow.com/a/17224886/582917
            //this only works because it's in an isolate scope, therefore myDirective is part of the scope
            $scope.$watch('pvTooltipDirective', function(value){

                // Если передали пустую строку то удаление
                // источник - https://stackoverflow.com/a/13414592
                // Эта фича нужна что ссылка была неактивна и была подсказка
                // а когда стала активна то подсказка уже не нужна.
                if ($scope.ptd_is_inited){
                    element.tooltip('destroy');
                    $scope.ptd_is_inited = false;
                };

                if(value){

                    element.tooltip({
                        placement: "top",
                        title: value,
                        html: true
                    });
                    $(element).removeAttr('title');
                    $scope.ptd_is_inited = true;

                };
            });
        }
    }
});



/* Ш-9 Контроллер всей страницы. */
angular.module('myNgApp').controller('FinCalcCtrl', function($scope, $http){

    // Для месяца 1 выодит 1 год, для месяца 13 выводит 2 год и т.п.
    // для остальных месяцев - возвращает 0. Использется дя формирования вывода.
    $scope.getYearForMonth = function(m_num){
        if (((m_num - 1) % 12) == 0){
            return (m_num - 1) / 12 + 1;
        }
        return 0;
    }

    // Доинвестирование
    $scope.getAddRubStr = function(m_num){
        return pvlNumberWithRoubles($scope.msi_add_rub_val);
    }

    // Функция заполенния расчета
    $scope.fccUpdateRaschet = function(){

        // Когда достигнута цель, пустое - значит не достигнута
        $scope.msi_goal1_reached_str = "";
        $scope.msi_goal2_reached_str = "";

        // Заполняет месяцы
        $scope.fcc_months_array = [];
        for (var m_num=1; m_num<=$scope.msi_srok_let_val*12; ++m_num){

            // Очередной месяц и год
            var cmo = {};
            cmo.fcc_month_total_num = m_num;
            cmo.fcc_month_year_num = ((m_num-1) % 12)+1;
            cmo.fcc_year_num = parseInt((m_num - 1) / 12);

            // Надо ли годовой заголовок
            cmo.fcc_year_header_num = $scope.getYearForMonth(m_num);

            // Полное накопление на начало месяца считается как
            // прошлое на конец месяца (а если его нет то начальная сумма)
            cmo.fcc_full_nakop_begin_month_val = m_num == 1 ? $scope.msi_start_rub_val : $scope.fcc_months_array[m_num-1-1].fcc_full_nakop_end_month_val;
            cmo.fcc_full_nakop_begin_month_str = pvlNumberWithRoubles(cmo.fcc_full_nakop_begin_month_val);

            // Проценты в этот мес, считаются на ту сумму что была на началом
            cmo.fcc_month_proc_val = parseInt(cmo.fcc_full_nakop_begin_month_val * $scope.msi_proc_doh_val / 100 / 12);
            cmo.fcc_month_proc_str = pvlNumberWithRoubles(cmo.fcc_month_proc_val);

            // доинвестирование делается только заданное число первых лет
            cmo.fcc_doinvest_val = (m_num <= $scope.msi_add_let_val*12) ? $scope.msi_add_rub_val : 0;
            cmo.fcc_doinvest_str = pvlNumberWithRoubles(cmo.fcc_doinvest_val);

            // А затем лишь доля, а остальное изымается. Так же присваиваем ноль чтобы не было
            // пустых клеток первое время.
            cmo.fcc_dodod_izym_val = 0;
            cmo.fcc_dodod_izym_str = pvlNumberWithRoubles(cmo.fcc_dodod_izym_val);
            if (m_num > $scope.msi_reinvest_let_val*12){

                cmo.fcc_dodod_izym_val = parseInt($scope.msi_vivod_proc_val / 100 * cmo.fcc_month_proc_val);
                cmo.fcc_dodod_izym_str = pvlNumberWithRoubles(cmo.fcc_dodod_izym_val);
            }

            // Как только доход превысил цель, этот месяц запоминаем
            if (!$scope.msi_goal1_reached_str && (cmo.fcc_month_proc_val > $scope.msi_goal1_rub_val)){
                $scope.msi_goal1_reached_str = cmo.fcc_year_num + "-й год, " + cmo.fcc_month_year_num + "-й месяц" ;
            }
            if (!$scope.msi_goal2_reached_str && (cmo.fcc_month_proc_val > $scope.msi_goal2_rub_val)){
                $scope.msi_goal2_reached_str = cmo.fcc_year_num + "-й год, " + cmo.fcc_month_year_num + "-й месяц" ;
            }


            // На конец месяца считается как значение на началом + проценты + доинвестирование
            cmo.fcc_full_nakop_end_month_val = cmo.fcc_full_nakop_begin_month_val + cmo.fcc_month_proc_val - cmo.fcc_dodod_izym_val + cmo.fcc_doinvest_val;
            cmo.fcc_full_nakop_end_month_str = pvlNumberWithRoubles(cmo.fcc_full_nakop_end_month_val);

            $scope.fcc_months_array.push(cmo);
        }

    };

    // Переменнеы (заполняются значениями в директивах)
    // $scope.msi_srok_let_val = 0;

    // Обновление таблицы при измении любой величины
    $scope.$watch('msi_start_rub_val', $scope.fccUpdateRaschet);
    $scope.$watch('msi_add_rub_val', $scope.fccUpdateRaschet);
    $scope.$watch('msi_add_let_val', $scope.fccUpdateRaschet);
    $scope.$watch('msi_proc_doh_val', $scope.fccUpdateRaschet);
    $scope.$watch('msi_reinvest_let_val', $scope.fccUpdateRaschet);
    $scope.$watch('msi_vivod_proc_val', $scope.fccUpdateRaschet);
    $scope.$watch('msi_srok_let_val', $scope.fccUpdateRaschet);
    $scope.$watch('msi_goal1_rub_val', $scope.fccUpdateRaschet);
    $scope.$watch('msi_goal2_rub_val', $scope.fccUpdateRaschet);
    $scope.fccUpdateRaschet();

});
