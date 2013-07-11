function AuthRegFormCtrl($scope, $http){

    // Тут значения полей хранятся
    $scope.email = '';
    $scope.password = '';

    // Эти 2 флага используются для отображения блока "Загрузка".
    // Флаг redirecting необходим чтобы продолжать показывать блок "Загрузка"
    // уже после того как ответ от сервера пришел об аутентификации и браузер редиректится в кабинет
    // в этот момент чтобы пользователь продолжал видеть "Загрузка".
    $scope.loading = false;
    $scope.redirecting = false;
    $scope.form_errors = {
        password: { required: false},
        email: { required: false }
    }

    $scope.register = function(){
        if ($scope.validate())
        {
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
    }

    $scope.login = function(){
        if ($scope.validate())
        {
            $scope.loading = true;
            $scope.errorText = '';
            httpObj = $http({
                method: 'POST',
                url: '/login_user/',
                data: $scope._getDataDictFromScope(),
                cache: false,
                timeout: 15000
            });
            $scope._setupServerCallbacks(httpObj);
        }
    }

    $scope.validate = function(){

        var wasErrors = false;

        if (($scope.email == undefined) || ($scope.email.length == 0)){
            $scope.form_errors.email.required = true;
            wasErrors = true;
        };

        if (($scope.password == undefined) || ($scope.password.length == 0)){
            $scope.form_errors.password.required = true;
            wasErrors = true;
        };

        return !wasErrors;
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
                  $scope.errorText = 'Неверный пароль или адрес эл. почты.'
              }
              else if (data == 'ok') {
                  $scope.redirecting = true;
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

    $scope.hideEmailErrors = function(){
        $scope.form_errors.email.required = false;
    }
    $scope.hidePasswordErrors = function(){
        $scope.form_errors.password.required = false;
    }
}
