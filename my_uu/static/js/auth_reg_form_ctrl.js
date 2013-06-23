function AuthRegFormCtrl($scope, $http){
    $scope.email = '';
    $scope.password = '';
    $scope.loading = false;
    $scope.isValid = function(){
        return $scope.email && $scope.email.length > 0;
    }
    $scope.register = function(){
        $scope.loading = true;
        $scope.errorText = '';
        var data = {'email': $scope.email, 'password': $scope.password};
        httpObj = $http({
            method: 'POST',
            url: '/register_user/',
            data: $scope._getDataDictFromScope(),
            cache: false,
            timeout: 5000
        });
        $scope._setupServerCallbacks(httpObj);
    }
    $scope.login = function(){
        $scope.loading = true;
        $scope.errorText = '';
        httpObj = $http({
            method: 'POST',
            url: '/login_user/',
            data: $scope._getDataDictFromScope(),
            cache: false,
            timeout: 5000
        });
        $scope._setupServerCallbacks(httpObj);
    }
    $scope._getDataDictFromScope = function(){
        return {'email': $scope.email, 'password': $scope.password};
    }
    $scope._setupServerCallbacks = function(httpObj){
          httpObj.success(function(data, status) {
              if (data == 'register_exists') {
                  $scope.errorText = 'Пользователь с таким эл. адресом уже существует.'
              }
              else if (data == 'auth_email_password_incorrect') {
                  $scope.errorText = 'Пользователь с таким адресом эл. почты и паролем не найден.'
              }
              else if (data == 'ok') {
                  window.location = '/lk/';
              }
              else {
                  $scope.errorText = 'Неизвестный ответ от сервера ' +  data;
              }
              $scope.loading = false;
          }).
          error(function(data, status) {
              $scope.loading = false;
              $scope.errorText = 'Ошибка связи с сервером по HTTP. Код ошибки: ' + status;
        });
    }
}
