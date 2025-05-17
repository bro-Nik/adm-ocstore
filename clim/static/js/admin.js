const $modalsBox = $("#Modals");

$(function () {
  // Modals
  //
  // Open modal to confirm
  $("body").on("click", "[data-modal-confirm]", function () {
    var $modal = $("#ModalConfirmation"),
      $btn = $(this);
    var $modal_btn = $modal.find("[type=submit]");

    if ($btn.data("form")) $modal_btn.attr("form", $btn.data("form"));
    else $modal_btn.attr("form", `${$btn.closest("form").attr("id")}`);

    // if modal then update
    // var pre_modal_id = $btn.closest(".modal").attr("id");
    // if (pre_modal_id) $modal.data("pre-modal-id", pre_modal_id);
    // else $modal.removeAttr("data-pre-modal-id");

    // var pre_need_clean = $btn.data("pre-need-clean") || false;
    // $modal.data("pre-need-clean", pre_need_clean);

    // to modal action
    $modal.find(".modal-title").text($btn.data("title"));
    $modal.find(".modal-text").text($btn.data("text") || "");

    $modal_btn.data("action", $btn.data("action") || "");
    $modal_btn.data("after", $btn.data("after") || "");
    $modal_btn.data("id", $btn.data("id") || "");
    $modal_btn.data("modal", $btn.closest(".modal").attr("id") || "");
    if ($btn.attr("formaction"))
      $modal_btn.attr("formaction", $btn.attr("formaction"));
    $modal.modal({ backdrop: false }).modal("show");
  });

  $("body").on("click", "[data-content-id]", function () {
    var url = $(this).data("url"),
      $modal = $(this).closest(".modal-body");

    $.get(OnlyContentUrl(url)).done(function (data) {
      LoadTo($modal, data);
    });
  });

  $("body").on("click", "[data-modal-id]", function () {
    var modal_id = $(this).data("modal-id"),
      url = $(this).data("url"),
      pre_modal_id = $(this).closest(".modal").attr("id");

    // Не обновлять предыдущее при закрытии
    if ($(this).hasClass("not-update")) pre_modal_id = false;
    LoadToModal(modal_id, url, false, pre_modal_id);
  });

  // Close modal
  $("body").mousedown(function (e) {
    if ($(e.target).is(".modal")) {
      $(e.target).modal("hide");
    }
  });

  // Open Modal
  $("body").on("show.bs.modal", ".modal", function () {
    var $modal = $(this);

    $modal.css("height", $(window).height());
    var $active_modals = $("body").find(".modal.show"),
      z_index = parseInt($modal.css("z-index"));

    $active_modals.each(function () {
      if ($(this).index() !== $modal.index()) {
        var this_z_index = parseInt($(this).css("z-index"));
        if ($modal.find(".modal-fullscreen").length) {
          $(this).find(".modal-close-label").css("top", "+=60");
        }
        if ((this_z_index) => z_index) {
          z_index = this_z_index + 1;
        }
      }
    });
    $modal.css("z-index", z_index);

    // Fade
    if (!$modal.find(".modal-fullscreen").length) {
      $("body").append(
        `<div class="modal-backdrop fade show" style="z-index: ${z_index - 1};"></div>`,
      );
    }
  });

  $("body").on("shown.bs.modal", function () {
    var $modal = $(this);
    $("body .modal-backdrop").css(
      "z-index",
      parseInt($modal.css("z-index")) - 1,
    );

    UpdateFocus($modal);
  });

  // Close Modal
  $("body").on("hide.bs.modal", ".modal", function () {
    var $modal = $(this);

    if (!$(".modal.show").length > 1) return false;

    var z_index = parseInt($modal.css("z-index"));
    var max_z_index = 0;

    $("body")
      .find(".modal.show")
      .each(function () {
        var this_z_index = parseInt($(this).css("z-index"));
        if (this_z_index !== z_index && this_z_index > max_z_index) {
          max_z_index = this_z_index;
        }
      });

    if ($modal.find(".modal-fullscreen").length) {
      $("body")
        .find(".modal.show")
        .each(function () {
          if ($(this).index() !== $modal.index()) {
            $(this).find(".modal-close-label").css("top", "-=60");
          }
        });
    }
  });

  $("body").on("hidden.bs.modal", ".modal", function () {
    var $modal = $(this);
    // Fade
    if (!$modal.find(".modal-fullscreen").length)
      $("body .modal-backdrop").eq(-1).remove();
  });

  $("body").on("hide.bs.modal", ".modal", function () {
    var $modal = $(this);
    // if $modal.data('')
    if (
      $modal.attr("id") != "ModalConfirmation" &&
      !$modal.hasClass("not-update")
    ) {
      PageUpdate($modal);
    }
  });

  // Form
  $("body").on("submit", function (event) {
    var $form = $(event.target),
      $modal = $form.closest(".modal"),
      $btn = $(event.originalEvent.submitter);

    // стандартная отправка формы
    if ($form.hasClass('default-form-action')) return;

    event.preventDefault();

    // Если кнопка меняет Action
    let url = $btn.attr("formaction") || $form.attr("action");

    var data = {};
    if ($btn.data("action")) data.action = $btn.data("action");

    // Данные
    if ($form.find("[data-to-server]").length) {
      // Несколько элементов с даннымы
      $form.find("[data-to-server]").each(function (index, element) {
        // Ключ данных
        var data_name = $(element).data("to-server");

        if (element.tagName === "DIV") {
          // if (data[data_name] === undefined) data[data_name] = {}
          // Проходим по полям
          data[data_name] = Serialize($(element));
        } else if (element.tagName === "TABLE") {
          if (data[data_name] === undefined) data[data_name] = [];

          $(element)
            .find("tr.product")
            .each(function (index, tr) {
              var item = Serialize($(tr), (required = true));
              // Если не пусто - добавляем
              if (!$.isEmptyObject(item)) data[data_name].push(item);
            });
        }
      });
    }

    // Остальные поля
    // Объединить данные формы и кнопки
    $.extend(data, Serialize($form));

    if ($btn.attr("name")) {
      var btn_data = {};
      btn_data[$btn.attr("name")] = $btn.attr("value");
      $.extend(data, btn_data);
    }

    // Если нужно собрать ID
    var ids = [];
    if ($btn.data("id")) ids.push($btn.data("id"));
    else {
      $form.find(".to-check:checked").each(function () {
        ids.push($(this).val());
      });
    }
    if (!$.isEmptyObject(ids)) data.ids = ids;

    SendingData(url, data, $btn);

    // $.post(action, data).done(function (response) {
    //   UpdateAfterLoad(response, $modal);
    // });
  });

  // Show more content
  $("body").on("click", ".show-more", function () {
    $(this).next(".show-more-content").slideToggle(500);
  });

  // Paste into input
  $("body").on("click", ".paste-into-input", function () {
    var $input = $(this).closest("div").find("input");
    $input.val($(this).data("value")).trigger("input");
  });
});

// Load to Page
function LoadToPage(url) {
  if (!url) url = $(location).attr("href");
  $("#content").load(OnlyContentUrl(url), function () {
    UpdateScripts($("#content"));
    UpdateFocus($("#content"));
  });
}

// Load to Modal
function LoadToModal(modal_id, url, pre_need_update, pre_modal_id) {
  var $modal = $(`#${modal_id}`),
    $loadIn = $modal;

  // нужно для обновления контента в модульном
  if ($modal.length) {
    // load only content
    if ($modal.find(".modal-fullscreen").length) {
      $loadIn = $modal.find(".modal-body");
      url += `${url.indexOf("?") > 0 ? "&" : "?"}only_content=true`;
    }
  } else {
    // create and load full modal
    $loadIn = $modal = $("<div>", {
      id: modal_id,
      class: "modal fade",
      tabindex: "-1",
    })
      .attr("aria-hidden", "false")
      .appendTo($modalsBox);
  }

  $modal.data("pre-need-update", pre_need_update || false);
  if (pre_modal_id) {
    $modal.data("pre-modal-id", pre_modal_id);
  }

  $loadIn.empty().load(url, function () {
    UpdateScripts($modal);
    $modal.modal({
      backdrop: false,
      keyboard: true,
    });
    $modal.data("url", url);
    if (!$modal.hasClass("show")) {
      $modal.modal("show");
    } else {
      $modal.trigger("show.bs.modal");
      UpdateFocus($modal);
    }
  });
}

function PageUpdate($modal) {
  var this_need_update = $modal.data("after-update"),
    pre_need_update = $modal.data("pre-need-update"),
    pre_need_clean = $modal.data("pre-need-clean"),
    pre_modal_id = $modal.data("pre-modal-id"),
    $pre_modal = $(`#${pre_modal_id}`);

  if (pre_need_clean == "true") {
    $pre_modal.data("pre-need-update", true);
    $pre_modal.modal("hide");
    // } else if (pre_need_update == 'true') {
  } else {
    if (pre_modal_id !== undefined) {
      LoadToModal(pre_modal_id, $pre_modal.data("url"), true);
    } else {
      LoadToPage();
    }
  }
}

// Focus
function UpdateFocus($element = $("body")) {
  if ($element.find(".focus").length) $element.find(".focus").focus();
  else $element.find(".search-input").focus();
}

// Update Page
function UpdateScripts($element = $("body")) {
  UpdateSelects($element);
  GetFlashedMessages($element);
  UpdateProductItems($element);
  UpdateDatepicker($element);
  // feather.replace();
  UpdateSortable($element)
}

UpdateScripts();

function UpdateProductItems($element = $("body")) {
  // Посчитать общие суммы во вкладках
  $element.find(".all-sum").each(function () {
    $(this).closest(".tab-pane").find(".sum").eq(-1).trigger("change");
  });

  // Посчитать суммы в товарах
  $element.find(".tr.product").each(function () {
    $(this).find("[name=quantity]").trigger("change");
  });

  // Иницилизировать селекты
  $element.find("tr.product").each(function () {
    UpdateProductSelect($(this));
    UpdateStockSelect($(this));
  });

  // Сброс изменений
  $element.on("reset", function () {
    var $modal = $(this).closest(".modal");
    if ($modal.length) LoadToModal($modal.attr("id"), $modal.data("url"), true);
  });

  // Пересчитать чекбоксы
  $element.find(".check-all:checkbox").trigger("change");

  // Показать панель действий при изменениях
  $element.on("change", function (event) {
    if (event.target.type !== "checkbox" && event.target.nodeName !== "SPAN") {
      $element.find(".sticky-bottom.change").addClass("active");
      $element.find(".sticky-bottom").addClass("active");
    }
  });
}

function SendingData(url, data, $btn) {
  $.ajax({
    type: "POST",
    url: url,
    data: JSON.stringify(data),
    contentType: "application/json; charset=utf-8",
  }).done(function (response) {
    UpdateAfterLoad(response, $btn);
  });
}

function UpdateAfterLoad(response, $btn) {
  var url = "",
    $modal;

  // Поиск модульного, если передано через кнопку
  if ($btn.data("modal")) $modal = $(`#${$btn.data("modal")}`);

  // Поиск модульного, в котором нажата кнопка
  if ($modal === undefined && $btn.closest(".modal") !== undefined) {
    if ($btn.closest(".modal").attr("id") !== "ModalConfirmation")
      $modal = $btn.closest(".modal");
  }

  if (response.url) url = response.url;
  else if (response.close) url = "";
  else if ($modal !== undefined) url = $modal.data("url");

  if ($btn.data("after") === "update" && url) {
    if ($modal !== undefined && $modal.length)
      LoadToModal($modal.attr("id"), url, true);
    else LoadToPage(url);
  } else if ($modal !== undefined && $modal.length) $modal.modal("hide");
  else LoadToPage();
}

function GetFlashedMessages($element = $("body")) {
  var $messages_box = $element.find(
    'script[data-selector="flashed-messages-page-data-js"]',
  );
  if ($messages_box.length) NewToasts(JSON.parse($messages_box.html()));
}

// Data To Server
$("body").on("click", ".btn-to-submit", function () {
  var $btn = $(this),
    $form = $btn.closest("form");

  var data = {};
  // Действие
  if ($btn.data("action")) data.action = $btn.data("action");

  // Данные
  if ($form.find("[data-to-server]").length) {
    // Несколько элементов с даннымы
    $form.find("[data-to-server]").each(function (index, element) {
      // Ключ данных
      var data_name = $(element).data("to-server");

      if (element.tagName === "DIV") {
        // if (data[data_name] === undefined) data[data_name] = {}
        // Проходим по полям
        data[data_name] = Serialize($(element));
      } else if (element.tagName === "TABLE") {
        if (data[data_name] === undefined) data[data_name] = [];

        $(element)
          .find("tr.product")
          .each(function (index, tr) {
            var item = Serialize($(tr), (required = true));
            // Если не пусто - добавляем
            if (!$.isEmptyObject(item)) data[data_name].push(item);
          });
      }
    });
    var $modal = $btn.closest(".modal");
    // $modal.modal("hide");
    SendingData($form.attr("action"), data, $btn, $modal);
  } else $form.submit();
  // } else data["form"] = Serialize($form)

  $(".sticky-bottom.change").removeClass("active");
});

$("body .fade").addClass("show");
UpdateFocus();
// GetFlashedMessages();
// feather.replace();

function getUrlArg(url, arg = "") {
  var hash;
  var hashes = url.slice(url.indexOf("?") + 1).split("&");
  for (var i = 0; i < hashes.length; i++) {
    hash = hashes[i].split("=");
    if (hash[0] !== arg) continue;
    return hash[1];
  }
}

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

// Datepicker
function UpdateDatepicker($element = $("body")) {
  $element.find("input.datepicker").each(function () {
    var date = $(this).data("value");
    date = [new Date(date)] ? date : "";

    new AirDatepicker(this, {
      selectedDates: date,
      buttons: ["today", "clear"],
      position: "right center",
      timepicker: true,
      minHours: 9,
      maxHours: 18,
      minutesStep: 10,
    });
  });
}

// Update Page After Change
$("body").on(
  "change",
  ".update-after-change select, .update-after-change input",
  function (e) {
    var $form = $(this).closest("form"),
      url = $(this).closest(".update-after-change").attr("action"),
      $modal = $(this).closest(".modal-body");

    $.post(OnlyContentUrl(url), $form.serialize()).done(function (data) {
      LoadTo($modal, data);
    });
  },
);

// Update Page After Click Pagination
$("body").on("click", ".pagination a", function (e) {
  var url = $(this).attr("href"),
    $modal = $(this).closest(".modal-body");

  e.preventDefault();

  $.get(OnlyContentUrl(url)).done(function (data) {
    LoadTo($modal, data);
  });
});

function OnlyContentUrl(url) {
  if (url.indexOf("only_content=true") === -1)
    url += `${url.indexOf("?") > 0 ? "&" : "?"}only_content=true`;
  return url;
}

function LoadTo($modal, content) {
  var $load_to;
  if ($modal.length) $load_to = $modal;
  else $load_to = $("#content");

  $load_to.html($(content));
  UpdateScripts($load_to);
}

// Проходим по полям
function Serialize($element, required = false) {
  var dict = {};
  $element.find("input, select, textarea").each(function (index, field) {
    // Если нужно проверить на обязательные поля элемента
    if (required && $(field).data("required") && !$(field).val()) return false;
    // Записываем имя поля и значение
    if ($(field).attr("name")) dict[$(field).attr("name")] = $(field).val();
    $(field).removeAttr("name");
  });
  return dict;
}

// Поиск на странице
$("body").find(".filter").keyup(function () {
  console.log('keyup ')
  // Retrieve the input field text and reset the count to zero
  var filter = $(this).val(),
    count = 0;

  var $find_box = $(this).closest(".modal-body");
  if (!$find_box.length) $find_box = $("#content");

  $find_box.find(".find-item").each(function () {
    // If the list item does not contain the text phrase fade it out
    if ($(this).text().search(new RegExp(filter, "i")) < 0) {
      $(this).fadeOut();

      // Show the list item if the phrase matches and increase the count by 1
    } else {
      $(this).show();
      count++;
    }
  });

  // Update the count
  var numberItems = count;
  $("#filter-count").text("Number of Filter = " + count);
});



function UpdateSortable($element = $("body")) {
  $element.find(".connectedSortable").sortable({
    opacity: 0.5,
    change: function() {$(this).closest("form").trigger("change")},
    update: function() {LineCount($(this).closest("table"))},
  })
}
