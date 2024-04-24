const $modalsBox = $('#Modals');

$(function () {


  // Action
  $("body").on("click", ".action", function () {
    var $btn = $(this),
      checked = [];

    // If button not in form
    if ($btn.attr("data-form")) {
      var $form = $($btn.attr("data-form"));
    } else {
      var $form = $btn.closest("form");
    }

    // If info not in main form
    if ($btn.attr("data-form-info")) {
      var info = $($btn.attr("data-form-info")).serializeArray();
    } else {
      var info = $form.serializeArray();
    }

    if ($btn.attr("data-id")) {
      checked.push($btn.attr("data-id"));
    } else {
      $form.find(".to-check:checked").each(function () {
        checked.push($(this).val());
      });
    }

    var data = {
      action: $btn.attr("data-action"),
      info: info,
      ids: checked,
    };

    var $modal = $btn.closest('.modal');
    $modal.attr('data-pre-need-update', true);

    SendingData($form.attr("action"), data, $btn, $modal);
    // $.ajax({
    // }).done(function (response) {
    //   if(response.redirect) {
    //     window.location.href = response.redirect;
    //   } else if ($btn.attr('data-this-need-update')) {
    //     LoadToModal($modal.attr('id'), $modal.attr("data-url"), true);
    //   } else {
    //     setTimeout(PageUpdate, 500, $modal);
    //   }
    // });
  });


  // Modals
  //
  // Open modal to confirm
  $("body").on("click", ".open-modal-confirmation", function () {
    var $modal = $("#ModalConfirmation"),
      $btn = $(this);

    if ($btn.attr("data-form")) {
      $modal.find(".action").attr("data-form", $btn.attr("data-form"));
    } else {
      $modal.find(".action").attr("data-form", `#${$btn.closest("form").attr("id")}`);
    }

    // if modal then update
    var pre_modal_id = $btn.closest(".modal").attr("id");
    if (pre_modal_id) {
      $modal.attr("data-pre-modal-id", pre_modal_id);
    } else {
      $modal.removeAttr("data-pre-modal-id");
    }
    var pre_need_clean = $btn.attr("data-pre-need-clean") || false;
    $modal.attr("data-pre-need-clean", pre_need_clean);

    // to modal action
    var title = $btn.attr("data-title"),
      action = $btn.attr("data-action"),
      id = $btn.attr("data-id") || "",
      text = $btn.attr("data-text") || "";
    $modal.find(".modal-title").text(title);
    $modal.find(".modal-text").text(text);
    $modal.find(".action").attr("data-action", action);
    $modal.find(".action").attr("data-id", id);
    $modal.modal({backdrop: false}).modal("show");
  });

  $("body").on("click", ".open-modal", function () {
    var modal_id = $(this).attr("data-modal-id"),
      url = $(this).attr("data-url"),
      pre_modal_id = $(this).closest('.modal').attr('id');
    if ($(this).hasClass('not-update')) {
      pre_modal_id = false;
    }
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
        `<div class="modal-backdrop fade show" style="z-index: ${z_index - 1};"></div>`
      );
    }
  });

  $("body").on("shown.bs.modal", function () {
    var $modal = $(this);
    $("body .modal-backdrop").css("z-index", parseInt($modal.css("z-index")) - 1);

    UpdateFocus($modal);
  });

  // Close Modal
  $("body").on("hide.bs.modal", ".modal", function () {
    var $modal = $(this);

    if (!$(".modal.show").length > 1) {
      return false;
    }

    var z_index = parseInt($modal.css("z-index"));
    var max_z_index = 0;

    $("body").find(".modal.show").each(function () {
        var this_z_index = parseInt($(this).css("z-index"));
        if (this_z_index !== z_index && this_z_index > max_z_index) {
          max_z_index = this_z_index;
        }
      });

    if ($modal.find(".modal-fullscreen").length) {
      $("body").find(".modal.show").each(function () {
        if ($(this).index() !== $modal.index()) {
          $(this).find(".modal-close-label").css("top", "-=60");
        }
      });
    }
  });

  $("body").on("hidden.bs.modal", ".modal", function () {
    var $modal = $(this);
    // Fade
    if (!$modal.find(".modal-fullscreen").length) {
      $("body .modal-backdrop").eq(-1).remove();
    }
  });

  $('body').on('hide.bs.modal', '.modal', function () {
    var $modal = $(this);
    if ($modal.attr('id') != 'ModalConfirmation' && !$modal.hasClass('not-update')) {
      PageUpdate($modal);
    }
  })

  $('body').on("click", ".load-page-or-modal", function () {
    var modal_id = $(this).closest(".modal").attr("id"),
      url = $(this).attr("data-url");

    if (modal_id) {
      LoadToModal(modal_id, url);
    } else {
      LoadToPage(url);
    }
  });

  // Form
  $('body').on("submit", function(event) {
    var $form = $(event.target), $modal = $form.closest(".modal");

    if ($modal.length) {
      event.preventDefault();

      var posting = $.post($form.attr("data-url"), $form.serialize());

      posting.done(function (data) {
        $modal.attr('data-pre-need-update', true);
        $modal.modal("hide");
      });
    }
  });

  // Show more content
  $('body').on('click', '.show-more', function () {
    $(this).next('.show-more-content').slideToggle(500);
  })

  // Paste into input
  $('body').on('click', '.paste-into-input', function () {
    var $input = $(this).closest('div').find('input');
    $input.val($(this).data('value')).trigger('input');
  })

})

// Load to Page
function LoadToPage(url) {
  if (!url) {
    url = $(location).attr('href');
    url += `${url.indexOf("?") > 0 ? "&" : "?"}only_content=true`;
  }
  $('#content').load(url, function () {
    UpdateScripts($('#content'));
    UpdateFocus($('#content'));
  });

}

// Load to Modal
function LoadToModal(modal_id, url, pre_need_update, pre_modal_id) {
  var $modal = $("#" + modal_id);

  // нужно для обновления контента в модульном
  if ($modal.length) {
    // load only content
    if ($modal.find(".modal-fullscreen").length) {
      var $loadIn = $modal.find(".modal-body").empty();
      url += `${url.indexOf("?") > 0 ? "&" : "?"}only_content=true`;
    } else {
      var $loadIn = $modal.empty();
    }
  } else {
    // create and load full modal
    var $loadIn = $modal = $('<div>', {
      id: modal_id,
      class: 'modal fade',
      tabindex: '-1'
    })
    .attr('aria-hidden', 'false')
    .appendTo($modalsBox);
  }
  
  $modal.attr("data-pre-need-update", pre_need_update || false);
  if (pre_modal_id) {
    $modal.attr("data-pre-modal-id", pre_modal_id);
  }

  $loadIn.load(url, function () {
    UpdateScripts($modal);
    $modal.modal({
      backdrop: false,
      keyboard: true,
    });
    $modal.attr("data-url", url);
    if (!$modal.hasClass("show")) {
      $modal.modal("show");
    } else {
      UpdateFocus($modal);
    }
  });
}

function PageUpdate($modal) {
  var this_need_update = $modal.attr("data-this-need-update"),
    pre_need_update = $modal.attr("data-pre-need-update"),
    pre_need_clean = $modal.attr("data-pre-need-clean"),
    pre_modal_id = $modal.attr("data-pre-modal-id"),
    $pre_modal = $(`#${pre_modal_id}`);

  if (pre_need_clean == 'true') {
    $pre_modal.attr('data-pre-need-update', true);
    $pre_modal.modal('hide');
  } else if (pre_need_update == 'true') {
    if (pre_modal_id) {
      LoadToModal(pre_modal_id, $pre_modal.attr("data-url"), true);
    } else {
      LoadToPage();
    }
  }
}

// Focus
function UpdateFocus($element=$("body")) {
  if ($element.find('.focus').length) {
    $element.find('.focus').focus();
  } else {
    $element.find(".search-input").focus();
  }
}

// Update Page
function UpdateScripts($element=$("body")) {
  StickyBottomActionsUpdate($element);
  UpdateSelects($element);
  GetFlashedMessages($element)
  UpdateProductItems($element)
  UpdateDatepicker($element)
  feather.replace();
}

function UpdateProductItems($element=$("body")) {
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
  $element.find('.check-all:checkbox').trigger('change');

  // Показать панель действий при изменениях
  $element.on("change", function (event) {
    if (event.target.type !== "checkbox" && event.target.nodeName !== "SPAN") {
      $element.find(".sticky-bottom.change").addClass("active");
    }
  });
}

// Sticky Bottom Actions
function StickyBottomActionsUpdate($element=$("body")) {

  if ($element.find('form').length > 1) {
    $element.find('form').each(function () {
      CreateStickyBottomActions($(this));
    })
  } else {
    CreateStickyBottomActions($element);
  }
}

function CreateStickyBottomActions($element) {
  var $content = $(`
    <div class="sticky-bottom form-actions">
      <div class="col-12">
        <div class="bg-white h-100 d-flex gap-2 align-items-center align-items-center">
          <span class="ms-5">Отмечено:</span>
          <span class="checks-count"></span>
          <a class="ms-3 decheck-all text-secondary">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M2.146 2.854a.5.5 0 1 1 .708-.708L8 7.293l5.146-5.147a.5.5 0 0 1 .708.708L8.707 8l5.147 5.146a.5.5 0 0 1-.708.708L8 8.707l-5.146 5.147a.5.5 0 0 1-.708-.708L7.293 8 2.146 2.854Z"/></svg>
          </a>
          <div class="vr my-3"></div>
          <div class="buttons"></div>
        </div>
      </div>
    </div>
  `);
  var stickyBottomButtons = $element.find(".sticky-bottom-buttons");
  if (stickyBottomButtons.length) {
    $content.find('.buttons').append(stickyBottomButtons.children());
    stickyBottomButtons.parent().append($content);
    stickyBottomButtons.remove();
  }
}

function SendingData(url, data, $btn, $modal) {
  $.ajax({
    type: "POST",
    url: url,
    data: JSON.stringify(data),
    contentType: "application/json; charset=utf-8",
  }).done(function (response) {
    if(response.redirect) {
      LoadToModal($modal.attr('id'), response.redirect, true);
      // window.location.href = response.redirect;
    } else if ($btn.attr('data-this-need-update')) {
      LoadToModal($modal.attr('id'), $modal.attr("data-url"), true);
    } else {
      setTimeout(PageUpdate, 500, $modal);
    }
  });
}

function GetFlashedMessages($element=$('body')) {
  var $messages_box = $element.find('script[data-selector="flashed-messages-page-data-js"]');
  if($messages_box.length) NewToasts(JSON.parse($messages_box.html()));
}


// Data To Server
$("body").on("click", ".btn-to-submit", function () {
  var $btn = $(this),
    $form = $btn.closest("form");

  var data = {};
  // Действие
  if ($btn.attr("data-action")) data.action = $btn.attr("data-action")

  // Данные
  $form.find("[data-to-server]").each(function(index, element){
    // Ключ данных
    var data_name = $(element).attr("data-to-server");

    if (element.tagName === "DIV") {
      if (data[data_name] === undefined) data[data_name] = {}
      // Проходим по полям
      $(element).find("input, select, textarea").each(function (index, field) {
        if ($(field).attr('name')) data[data_name][$(field).attr('name')] = $(field).val();
      });

    } else if (element.tagName === "TABLE") {
      if (data[data_name] === undefined) data[data_name] = []

      $(element).find("tr.product").each(function (index, tr) {
        var item = {},
          skip = false;
        $(tr).find("td").each(function (index, td) {
          // Проходим по полям
          $(td).find("input, select, textarea").each(function (index, field) {
            if ($(field).attr('data-required') && !$(field).val()) skip = true;
            if ($(field).attr('name')) item[$(field).attr('name')] = $(field).val();
          });
        });
        if (skip) return;
        else data[data_name].push(item);
      });
    }
  });

  SendingData($form.data("url"), data, $btn, $btn.closest(".modal"));
  $(".sticky-bottom").removeClass("active");
});

StickyBottomActionsUpdate();
$('body .fade').addClass('show');
UpdateFocus();
GetFlashedMessages();
feather.replace();


function getUrlArg(url, arg="") {
  var hash;
  var hashes = url.slice(url.indexOf('?') + 1).split('&');
  for(var i = 0; i < hashes.length; i++) {
    hash = hashes[i].split('=');
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
function UpdateDatepicker($element=$("body")) {
  $element.find("input.datepicker").each(function () {
    var date = $(this).data('value');
    date = [new Date(date)] ? date : "";

    new AirDatepicker(this, {
      selectedDates: date,
      buttons: ['today', 'clear'],
      position: "right center",
      timepicker: true,
      minHours: 9,
      maxHours: 18,
      minutesStep: 10});
  });
}
