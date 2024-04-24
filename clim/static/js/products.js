// Обновление общей суммы
$("body").on("input change", ".sum", function () {
  var all_sum = 0;
    $tab = $(this).closest(".tab-pane");

  $tab.find(".sum").each(function () {
    all_sum += +$(this).text();
  });
  $tab.find(".all-sum").text(all_sum);
});


// Обновление суммы товара
$("body").on("input change", "[name=quantity], [name=price]", function () {
  var $tr = $(this).closest("tr"),
    quantity = $tr.find("[name=quantity]").val();
    price = $tr.find("[name=price]").val();
  $tr.find(".sum").text(price * quantity).trigger("change");
});


$("body").on("click", ".delete-product", function () {
  var $tab = $(this).closest("div[id]");
  $tab.find(".to-check:checked").each(function () {
    if ($tab.find("tr.product").length > 1) $(this).closest("tr").remove();
    else newLine($tab, $(this).closest("tr"));
  });
  $tab.find(".to-check:checkbox").trigger("change");
  LineCount($tab);
});


function LineCount($tab) {
  var count = 1;
  $tab.find("tr.product").each(function () {
    $(this).find(".line-count").text(count + ".");
    count += 1;
  });
}


function UpdateProductSelect($tr) {
  var $productSelect = $tr.find("select.product-select");
  UpdateSelect($productSelect);

  $productSelect.on("select change", function (evt, config) {
    var data = $(this).select2("data")[0],
      $tr = $(this).closest("tr");

    if (data != undefined) {
      $tr.find("[name=price]").val(data.price || "").trigger('change');
      $tr.find("[name=type]").val(data.type);
      $tr.find("[name=name]").val(data.text);
      $tr.find("[name=unit]").val(data.unit);
      $tr.find(".input-group-text.quantity").text(data.unit);
    }
    UpdateStockSelect($tr);
    // $tr.find("select.stock-select").trigger("change");
  });
  //
  // UpdateStockSelect($tr);
}


function UpdateStockSelect($tr) {
  var product_id = $tr.find("select.product-select").val(),
    product_type = $tr.find("[name=type]").val();

  $tr.find("select.stock-select").each(function () {
    var $stockSelect = $(this);

    // Если услуга - убираем склад
    if (product_type === "service") {
      if ($stockSelect.hasClass("select2-hidden-accessible")) $stockSelect.select2("destroy");
      $stockSelect.addClass("visually-hidden");
      return false;
    } else {
      $stockSelect.removeClass("visually-hidden");
    }

    //$stockSelect.prop("disabled", !product_id);
    UpdateSelect($stockSelect, url_args={product_id: +product_id || 0});

    $stockSelect.on("select change", function (evt, config) {
      if ($stockSelect.prop("disabled")) return;
      var data = $(this).select2("data")[0],
        $tr = $(this).closest("tr");

      if (data != undefined) {
        // Текст в скрытый инпут
        $tr.find(`[name=${$stockSelect.data("text-to-input-name")}]`).val(data.text);
        if (product_id) {
          // Количество на складе
          var $available_box = $tr.find(`[data-stock-available=${$stockSelect.attr("name")}]`)
          $available_box.text(data.subtext || $stockSelect.find("option:selected").data("quantity"));
        }
      }

      //var quantity = data.quantity
      //else var quantity = $stockSelect.find(':selected').attr('data-quantity') || 0;
    });

    if (!product_id) return false;

    // Загрузить первую опцию
    // var prevStockId = $tr.prev().find('select.stock-select').val();
    // var url = `${url_stock_first}?product_id=${product_id}`;
    var url = `${$stockSelect.data("url-one")}?product_id=${product_id}&stock_id=${$stockSelect.val()}`;
    // if ($stockSelect.val()) url += `&stock_id=${$stockSelect.val()}`
    // else if (prevStockId) url += '&stock_id=' + prevStockId;

    $.ajax({
      type: "GET",
      url: url,
      dataType: "json",
    }).then(function (data) {
      var option = new Option(data.text, data.id, true, true);
      $(option).data("quantity", data.subtext);

      $stockSelect.empty().append(option);
      // Текст в скрытый инпут
      $tr.find(`[name=${$stockSelect.data("text-to-input-name")}]`).val(data.text);
      // Количество на складе
      $tr.find(`[data-stock-available=${$stockSelect.attr("name")}]`).text(data.subtext);

      $stockSelect.trigger({
        type: "select2:select",
        params: {
          data: data,
        },
      });
    });
  });
}


function newLine($tab="", $new_line="", product_id="") {
  // var $tab = $(tab);
  var $line = $tab.find("tr.product").eq(-1);

  if ($new_line === "") {
    // Отключение select2
    $line.find(".select2-hidden-accessible").select2("destroy");

    // Клонирование и добавление
    $new_line = $line.clone();
    $new_line.appendTo($tab.find("tbody"));

    // Включение select2
    UpdateProductSelect($line);
    UpdateStockSelect($line);
  }

  $new_line.find(".line-count").text(`${$tab.find("tr.product").length}.`);
  $new_line.find(".to-check").prop("checked", false).trigger("change");

  // $new_line.find("select").empty().val(product_id);
  $new_line.find("[data-new-line-text]").each(function () {
    // Значение по умолчанию
    $(this).text($(this).attr("data-new-line-text"));
  });
  $new_line.find("[data-new-line-value]").each(function () {
    var value = $(this).attr("data-new-line-value");
    // Копирование значения
    if (value === "previous") $(this).val($line.find(`[name=${$(this).attr("name")}]`).val());
    // Значение по умолчанию
    else $(this).val(value);
  });

  UpdateProductSelect($new_line);
  UpdateStockSelect($new_line);
  $("#tabProducts").find(".table-responsive").animate({scrollLeft: 0}, 0);
  $new_line.find("select.product-select").select2("open");
}

$("body").on("click", ".create-new-line", function () {
  newLine($(this).closest("div[id]"));
})


