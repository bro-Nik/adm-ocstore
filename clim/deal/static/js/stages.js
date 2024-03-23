  $('body').on('change', '.stage input', function () {
    StegesColor();
  })

  // End of Deal
  $('body').on("change", '.end-stage', function () {

    // Перенос значения в поле стадий
    var $form = $('body').find('#DealInfo'),
      $this = $(this),
      $label = $this.parent().find('label'),
      text = $label.text(),
      val = $this.val(),
      color = $label.css('background-color');

    // Остальные кнопки
    $form.find('.stage :checked').prop('checked', false);

    // Последняя кнопка
    var $last_btn = $form.find('.stage').eq(-1);
    $last_btn.find('label').text(text);
    $last_btn.find('input').prop('checked', true).val(val);
    $last_btn.css('--deal-stage-color', color);

  StegesColor();


  $form.find('.old-stage').val($('#DealInfo').find('[name=stages]').val())
  $form.find('[name=stages]').val($(this).val())
  $form.find('.posting').val('true')


  $('#DealInfo .btn-to-submit').trigger('click');
})

function StegesColor() {
  var after_checked = false;
  $('body').find('.stage').each(function () {
    var $this = $(this),
      color = $('body').find('.stage :checked').parent().css('--deal-stage-color');

    if (!after_checked) {
      $this.find('label').css('background', color)
      $this.find('label').css('color', '#fff')
      $this.find('.deal-stage-line').addClass('visually-hidden')
    } else {
      $this.find('label').css('background', '#dfe3e8')
      $this.find('label').css('color', '#525c68')
      $this.find('.deal-stage-line').removeClass('visually-hidden')
    }

    if ($this.find('input').is(':checked')) {
      after_checked = true;
    }
  });
}
