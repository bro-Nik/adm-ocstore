// Ajax Select// General Select
function UpdateGeneralSelects($element=$("body")) {
  $element.find(".general-select").each(function () {
    UpdateSelect($(this));
  });
}

// Multiple Select Names > Count
function UpdateMultipleSelectCount($element=$("body")) {
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
      $select.parent().find(".select2-selection.select2-selection--multiple")
        .append($(`<span class="multiple-count" >+ ${count}</span>`));
    }
  }
}

function UpdateSelects($element) {
  UpdateGeneralSelects($element);
  UpdateMultipleSelectCount($element);
  UpdateContactSelect($element)
}

UpdateSelects($("body"))


$(document).on("change", ".show-count-selected", function (e) {
  MultipleSelectCount($(this));
});


function UpdateSelect($select, url_args={}) {
  // var $select = $tr.find("select");

  var ajax = null;
  if ($select.data("url")) {
    ajax = {
      delay: 250,
      url: $select.data("url"),
      dataType: "json",
      data: function (params) {
        var query = {
          search: params.term,
          page: params.page || 1,
        };
        $.extend(query, url_args);
        return query;
      },
    }
  }


  $select
    .select2({
      theme: "bootstrap-5",
      width: $select.data("width"),
      dropdownParent: $select.data("parent") || $select.closest("div[id]"),
      dropdownAutoWidth: true,
      selectionCssClass: $select.data("class") || "bg-light",
      templateResult: formatOption,
      language: {
        noResults: function () {
          return "Ничего не найдено";
        },
      },
      escapeMarkup: function (markup) {
        return markup;
      },
      ajax,
    })
}


function formatOption(option) {
  return $(`<span class="text">${option.text}<small class="text-muted">${option.subtext || ""}</small></span>`)
}


// Инициализировать селект контакта
function UpdateContactSelect($element=$("body")) {
  $element.find("select.contact-select").each(function () {
    var $contactSelect = $(this);
    UpdateSelect($contactSelect);

    $contactSelect.on("select2:open", () => {
      var $box = $(".select2-results:not(:has(button))");
      if (!$box.find('.select-new-container').length) {
        // Кнопка создания нового
        var role = getUrlArg($contactSelect.data("url"), "role");
        var url = `${url_contact_info}${url_contact_info.indexOf("?") > 0 ? "&" : "?"}role=${role}`;
        $box.append(
          `<div class='select-new-container' data-modal-id="ContactInfoModal" data-url="${url}">
            <div class='select-new-text'>создать новый контакт</div>
          </div>`,
        );
      }
    });
  });
}
