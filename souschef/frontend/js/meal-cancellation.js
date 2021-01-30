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
        $('#cancel_meal_dates').multiDatesPicker('addDates', JSON.parse($('#id_cancel_meal_dates').val()));

    }
    $('#cancel_meal_dates').bind('DOMSubtreeModified', function(){
        var dates = $('#cancel_meal_dates').multiDatesPicker('getDates');
        $('#id_cancel_meal_dates').val(JSON.stringify(dates));
      });
});