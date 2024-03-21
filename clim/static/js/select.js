var defaultSelectClass = "bg-light";

// Ajax Selects
function UpdateAjaxSelects($element = $("body")) {
  $element.find(".ajax-select").each(function () {
    $(this).select2({
      theme: "bootstrap-5",
      width: $(this).data("width") || "100%",
      dropdownAutoWidth: true,
      dropdownParent: $(this).closest(".modal"),
      selectionCssClass: $(this).data("class") || defaultSelectClass,
      language: {
        noResults: function () {
          return "Ничего не найдено";
        },
      },
      ajax: {
        delay: 250,
        url: $(this).data("url"),
        dataType: "json",
        data: function (params) {
          var query = {
            search: params.term,
            page: params.page || 1,
          };
          return query;
        },
      },
    });
  });
}

// General Select
function UpdateGeneralSelects($element = $("body")) {
  $element.find(".general-select").each(function () {
    $(this).select2({
      theme: "bootstrap-5",
      width: $(this).data("width") || "100%",
      dropdownAutoWidth: true,
      minimumResultsForSearch: 10,
      selectionCssClass: $(this).data("class") || defaultSelectClass,
    });
  });
}

// Multiple Select Names > Count
function UpdateMultipleSelectCount($element = $("body")) {
  $element.find("select.show-count-selected").each(function () {
    MultipleSelectCount($(this));
  });
}

function MultipleSelectCount($select) {
  var count = $select.val().length;

  if (count > 0) {
    $select.parent().find(".select2-selection__rendered").remove();
    var $count_span = $select.parent().find(".multiple-count");
    if ($count_span.length) {
      $count_span.html("+ " + count);
    } else {
      $select
        .parent()
        .find(".select2-selection.select2-selection--multiple")
        .append($(`<span class="multiple-count" >+ ${count}</span>`));
    }
  }
}

function UpdateScripts($element) {
  UpdateGeneralSelects($element);
  UpdateAjaxSelects($element);
  UpdateMultipleSelectCount($element);
  feather.replace();
}

UpdateAjaxSelects();
UpdateGeneralSelects();
UpdateMultipleSelectCount();


$(document).on("change", ".show-count-selected", function (e) {
  MultipleSelectCount($(this));
});

// Select Open Focus
$(document).on("select select2:open", function () {
  $(this).attr("data-test", "test");
  var single = $(this).parent().find(".select2-selection--single");
  if (single.length) {
    alert("single");
    var $search = $(".select2-search.select2-search--dropdown").find(
      ".select2-search__field",
    );
  } else {
    document.querySelector(".select2-search__field").focus();
    // $(document).find('.select2-search__field').focus();
  }
  // $search.focus();
});

