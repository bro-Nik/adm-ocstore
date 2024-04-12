  // Show inputs
  $("body").on("click", ".deal-info-edit-link", function () {
    var $this = $(this);
    $this.addClass("visually-hidden");

    var $input = $this.next();
    $input.removeClass("visually-hidden");

    if ($input.is("input")) {
      data = $input.val();
      //$input.focus().val("").val(data);
      $input.val(data).focus();
    }
  });
