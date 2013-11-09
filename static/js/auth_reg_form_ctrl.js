function AuthRegFormCtrl($scope, $http){

    // Тут значения полей хранятся
    $scope.email = '';
    $scope.password = '';

    // Флаг используются для отображения блока "Загрузка".
    // Флаг остается установленным уже после того как ответ от сервера пришел успешный
    // и браузер редиректится в кабинет в этот момент пользователь продолжает видеть "Загрузка" (флаг установлен).
    $scope.loading = false;

    $scope.register = function(){
        $scope.loading = true;
        $scope.errorText = '';
        var data = {'email': $scope.email, 'password': $scope.password};
        httpObj = $http({
            method: 'POST',
            url: '/register_user/',
            data: $scope._getDataDictFromScope(),
            cache: false,
            timeout: 15000
        });
        $scope._setupServerCallbacks(httpObj);
    }

    $scope._getDataDictFromScope = function(){
        return {'email': $scope.email, 'password': $scope.password};
    }

    $scope._setupServerCallbacks = function(httpObj){
          httpObj.success(function(resp, status) {
              if (resp.status_ok){

                  // Регистрация события-цели
                  ga('send', 'event', 'goal', 'GOAL_REGISTERED');
                  yaCounter22867360.reachGoal('GOAL_REGISTERED');
                  window.location = '/lk/';

              } else {
                  $scope.errorText = resp.response;
                  $scope.loading = false;
              };
          }).
          error(function(data, status) {
              // Статус 0 приходит если нет соединения с севером.
              if (status == 0){
                  $scope.errorText = 'Отсутствует соединение с сервером.';
              }else{
                  $scope.errorText = 'Ошибка на сервере. Пожалуйста, повторите попытку позднее или уточние состояние обратившись в службу поддержки.';
              }
              $scope.loading = false;
        });
    }
}
