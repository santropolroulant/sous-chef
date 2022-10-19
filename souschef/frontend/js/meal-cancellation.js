$(function() {

    // Javascript of the meal cancellation.
    // **************************************

    var config = {
        dateFormat: "yy-mm-dd",
        separator: "|"
    };

    $('#id_cancel_meal_dates').hide();
    $('#cancel_meal_dates').multiDatesPicker(config);
    if($('#id_cancel_meal_dates').val()){
        var existing_dates = JSON.parse($('#id_cancel_meal_dates').val());
        if(existing_dates.length > 0){
            $('#cancel_meal_dates').multiDatesPicker('addDates', existing_dates);
        };

    }
    $('#cancel_meal_dates').bind('DOMSubtreeModified', function(){
        var dates = $('#cancel_meal_dates').multiDatesPicker('getDates');
        $('#id_cancel_meal_dates').val(JSON.stringify(dates));
      });
});