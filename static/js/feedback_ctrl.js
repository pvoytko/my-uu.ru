function FeedbackController($scope, $http){

    $scope.send = function(){
        $scope.sending = true;
        $scope.success = false;
        $scope.errorText = '';
        httpObj = $http({
            method: 'POST',
            url: '/feedback_request_ajax/',
            data: $scope._getDataDictFromScope(),
            cache: false,
            timeout: 25000
        });
        $scope._setupServerCallbacks(httpObj);
    }
    $scope._getDataDictFromScope = function(){
        return {
            'text': $scope.text,
            'oUserId': $('#oUserId').val()
        };
    }
    $scope._setupServerCallbacks = function(httpObj){
          httpObj.success(function(resp, status) {
              if (resp.status_ok){
                  $scope.errorText = "";
                  $scope.sending = false;
                  $scope.success = true;
              } else {
                  $scope.errorText = resp.response;
                  $scope.sending = false;
                  $scope.success = false;
              }
          }).
          error(function(data, status) {
              // Статус 0 приходит если нет соединения с севером.
              if (status == 0){
                  $scope.errorText = 'Отсутствует соединение с сервером.';
              } else {
                  $scope.errorText = 'Ошибка на сервере. Пожалуйста, повторите попытку позднее или уточние состояние, обратившись в службу поддержки.';
              }
              $scope.sending = false;
              $scope.success = false;
        });
    }
    $scope.sending = false;
    $scope.success = false;
}
