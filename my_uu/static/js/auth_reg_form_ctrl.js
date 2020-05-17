/* Ш-9 Контроллер всей страницы. */
angular.module('myNgApp').controller('AuthRegFormCtrl', function($scope, $http){

    // Тут значения полей хранятся
    $scope.email = '';
    $scope.password = '';

    // Флаг используются для отображения блока "Загрузка".
    // Флаг остается установленным уже после того как ответ от сервера пришел успешный
    // и браузер редиректится в кабинет в этот момент пользователь продолжает видеть "Загрузка" (флаг установлен).
    $scope.loading = false;

    $scope.myUuRegister = function(){

        $scope.loading = true;
        $scope.errorText = '';

        // Ш-140
        backendAjaxPostStatu2({
            baps_http: $http,
            baps_ajax_url: '/register_user/',
            baps_dj_errors: false,
            baps_response_dj_errors_field: false,
            baps_loading_status: false,
            baps_post_parameters: $scope._getDataDictFromScope(),
            baps_success_callback: function(server_response){
              if (server_response.status_ok){

                  // Регистрация события-цели
                  ga('send', 'event', 'goal', 'GOAL_REGISTERED');
                  yaCounter22867360.reachGoal('GOAL_REGISTERED');
                  window.location = '/lk/';

              } else {
                  $scope.errorText = server_response.response;
                  $scope.loading = false;
              };
            },
            baps_error_callback: function(server_response){
               $scope.loading = false;
            }
        });
    }

    $scope._getDataDictFromScope = function(){
        return {'email': $scope.email, 'password': $scope.password};
    }

});
