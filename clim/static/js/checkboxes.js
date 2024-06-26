// Check All
$("body").on("change", ".check-all", function () {
  // var $form = $(this).closest("form");
  var $form = $(this).closest("div[id]");
  $form.find(".to-check").prop("checked", $(this).is(":checked")).first().trigger("change");
});

// Check Group
$("body").on("change", ".check-group", function () {
  var $form = $(this).closest("form");
  $form.find(`.${this.id}`).prop("checked", $(this).is(":checked"));
  $form.find(".to-check").trigger("change");
});

// Decheck All
$("body").on("click", ".decheck-all", function () {
  var $form = $(this).closest("form");
  $form.find(".to-check").prop("checked", false).trigger("change");
});

// Check Count
$("body").on("change", ".to-check", function () {
  // var $form = $(this).closest("form"),
  var $form = $(this).closest("div[id]"),
    checked_count = $form.find(".to-check:checked").length,
    all_count = $form.find(".to-check").length,
    $box_actions = $form.find(".form-actions");

  if (checked_count > 0) {
    $box_actions.addClass("active");
  } else {
    $box_actions.removeClass("active");
  }
  $box_actions.find('button').prop("disabled", !checked_count > 0);
  $box_actions.find(".checks-count").text(`${checked_count} / ${all_count}`);
  $form.find(".check-all").prop("checked", checked_count > 0);
  if (checked_count > 0) $box_actions.addClass("active");
  else $box_actions.removeClass("active");
});

