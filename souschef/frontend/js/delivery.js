function enableGeneratedOrdersCancelButton() {
  $('.ui.order.cancel.button').click(function () {
    var self = this;
    var modalCtntURL = $(self).attr('data-url');
    $.get(modalCtntURL, {status:'C'}, function(data, modalCtntURL){
        $('.ui.modal.status').html(data).modal("setting", {
            closable: false,
            // When approving modal, submit form
            onApprove: function($element, modalCtntURL) {
                var data = $('#change-status-form').serializeArray();

                $.ajax({
                     type: 'POST',
                     url: $(self).attr('data-url'),
                     data: data,
                     success: function (xhr, ajaxOptions, thrownError) {
                         if ( $(xhr).find('.errorlist').length > 0 ) {
                             $('.ui.modal.status').html(xhr);
                         } else {
                             $('.ui.modal.status').modal("hide");
                             location.reload();
                         }
                     },
                 });
                return false; // don't hide modal until we have the response
            },
            // When denying modal, restore default value for status dropdown
            onDeny: function($element) {
                $('.ui.modal.status').modal("hide");
            }
        }).modal('setting', 'autofocus', false).modal("show");
    });
  });
}

$(function() {
    // Javascript of the delivery application
    // ****************************************

    enableGeneratedOrdersCancelButton();

    $('.ui.dropdown.maindish.selection').dropdown('setting', 'onChange', function(value, text, $selectedItem) {
        $url = $(".field.dish.selection").data('url');
        var deliveryDate = $("input[name=delivery_date]").val();
        window.location.replace($url+value+"?delivery_date="+deliveryDate);
    });

    $('.ui.dropdown.mainingredients.selection').dropdown('setting', 'onChange', function(value, text, $selectedItem) {
        $('.button.confirmingredients').removeClass('disabled');
        $('.button.nextkitchencount').addClass('disabled');
        $('.button.restorerecipe').removeClass('disabled');
    });

    $('.ui.dropdown.sidesingredients.selection').dropdown('setting', 'onChange', function(value, text, $selectedItem) {
        $('.button.confirmingredients').removeClass('disabled');
        $('.button.nextkitchencount').addClass('disabled');
    });

    $('.button.orders').click(function(){
        $('.button.orders i').addClass('loading');
        var csrfToken = $("[name=csrfmiddlewaretoken]").val();
        var generateOrderDate = $("[name=generate_order_date]").val();
        $.ajax({
            type: 'POST',
            url: $(this).attr('data-url'),
            headers: {
              'X-CSRFToken': csrfToken,
            },
            data: {
              'generateOrderDate': generateOrderDate,
            },
            success: function (xhr, ajaxOptions, thrownError) {
              $('#generate-orders-error-message-content').text('');
              $('#generate-orders-error-message').hide();
              $("#generated-orders").html(xhr);
              enableGeneratedOrdersCancelButton();
              var count = $("#generated-orders-table tbody tr").length;
              $('.orders-count span').html(count);
              $('.orders-count').attr('data-order-count', count);
              $('.button.orders i').removeClass('loading');
            },
            error: function (xhr, textStatus, errorThrown) {
              console.log('error!');
              console.log(textStatus);
              console.log(errorThrown);
              $('#generate-orders-error-message-content').text(errorThrown);
              $('#generate-orders-error-message').show();
              $('.button.orders i').removeClass('loading');
            }
        });
    });

    $('input[name=include_a_bill]').change(function () {
        var self = this;
        var url = $(self).data('url');
        var checked = $(self).is(':checked');
        $.ajax({
            type: (checked) ? 'POST' : 'DELETE',
            url: url,
            success: function (xhr, ajaxOptions, thrownError) {
                $(self).removeAttr('disabled');
            }
        });
        $(self).attr('disabled', 'disabled');
    });

    var today = new Date();

    $('#generate_order_date_calendar').calendar({
      type: 'date',
      minDate: today,
      formatter: {
          date: function (date, settings) {
              return date ? dateFormat(date, 'yyyy-mm-dd') : '';
          }
      },
      onChange: function(date, text, mode) {
        if (date) {
          window.location = "/delivery/order/?delivery_date=" + dateFormat(date, 'yyyy-mm-dd');
        }
      },
    });
});
