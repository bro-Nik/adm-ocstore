// Consumables
function DealConsumablesFill() {
  //ToDo просто удалить все tr и начинать с новых
  $("#tabConsumables").find("tr.product").each(function () {
      var $tab = $(this).closest("div[id]");
      if ($tab.find("tr.product").length > 1) $(this).closest("tr").remove();
      else newLine($tab, $(this).closest("tr")); 
    });

  $("#tabProducts").find("select.product-select").each(function () {
      var $tr = $(this).closest("tr"),
        type = $tr.find("[name=type]").val();
      if (type === "service") {
        var option_quantity = $tr.find("[name=quantity]").val(),
          url = `${url_get_consumables_in_option}/${$(this).val()}`;

        DealConsumablesFillAdd(url, option_quantity);
      }
    });
}

async function DealConsumablesFillAdd(url, option_quantity) {
  await getConsumablesInOption(url);

  if (consumables_in_option.length > 0) {
    var first_line = true;
    for (let i = 0; i < consumables_in_option.length; i++) {
      if (first_line !== true) newLine($("#tabConsumables"));
      else first_line = false;

      var product = consumables_in_option[i];
      product.quantity = +option_quantity * +product.quantity;

      var $tr = $("#tabConsumables").find("tr.product").eq(-1);
      $tr.find("select.product-select").append(new Option(product.name, product.product_id, true, true));
      $tr.find("[name=quantity]").val(product.quantity);
      $tr.find("[name=price]").val(product.price).trigger("change");
      $tr.find("[name=name]").val(product.name);
      $tr.find(".input-group-text.quantity").text(product.unit);

      UpdateProductSelect($tr);
      UpdateStockSelect($tr);
    }
  }
}

var consumables_in_option = {};
function getConsumablesInOption(url) {
  return fetch(url, {
    method: "GET",
    headers: {
      "Content-type": "application/json; charset=UTF-8",
    },
  }).then((res) => res.json())
    .then((data) => (window.consumables_in_option = data));
}
