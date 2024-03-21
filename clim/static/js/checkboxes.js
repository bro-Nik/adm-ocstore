
// Check Count
// $("body").on("change", ".to-check", function () {
//   var $table = $(this).closest("table"),
//     $modal = $table.closest(".modal"),
//     checked_count = $table.find(".to-check:checked").length,
//     all_count = $table.find(".to-check").length;
//
//   if ($modal.length) {
//     var $box_actions = $table.closest("div[id]");
//
//     var $btns = $box_actions.find(".actions .btn");
//     $btns.prop("disabled", !checked_count > 0);
//   } else {
//     var $box_actions = $(".sticky-bottom.actions");
//     if (checked_count > 0) {
//       $box_actions.addClass("active");
//     } else {
//       $box_actions.removeClass("active");
//     }
//   }
//   $box_actions.find(".checks-count").text(checked_count + " / " + all_count);
//   $($table)
//     .find(".check-all")
//     .prop("checked", checked_count > 0);
// });

// Check All
$("body").on("change", ".check-all", function () {
  var $form = $(this).closest("form");
  $form.find(".to-check").prop("checked", $(this).is(":checked")).trigger("change");
});

// Check Group
$("body").on("change", ".check-group", function () {
  var $form = $(this).closest("form");
  $form.find(`.${this.id}`).prop("checked", $(this).is(":checked"));
  $table.find(".to-check").trigger("change");
});

// Decheck All
$("body").on("click", ".decheck-all", function () {
  var $form = $(this).closest("form");
  $form.find(".to-check").prop("checked", false).trigger("change");
});

// Check Count
$("body").on("change", ".to-check", function () {
  var $form = $(this).closest("form"),
    checked_count = $form.find(".to-check:checked").length,
    all_count = $form.find(".to-check").length,
    $box_actions = $form.find(".form-actions");

  if (checked_count > 0) {
    $box_actions.find('button').addClass("active");
  } else {
    $box_actions.find('button').removeClass("active");
  }
  $box_actions.find('button').prop("disabled", !checked_count > 0);
  $box_actions.find(".checks-count").text(`${checked_count} / ${all_count}`);
  $form.find(".check-all").prop("checked", checked_count > 0);
});
