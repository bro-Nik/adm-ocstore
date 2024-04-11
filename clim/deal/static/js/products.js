// Consumables
function DealConsumablesFill() {
  //ToDo просто удалить все tr и начинать с новых
  $("#tabConsumables").find("tr.product").each(function () {
      var $tab = $(this).closest("div[id]");
      if ($tab.find("tr.product").length > 1) $(this).closest("tr").remove();
      else newLine($tab, $(this).closest("tr")); 
    });

  $("#tabProducts").find("select.product-select").each(function (index, element) {
      var type = $(this).find(":selected").attr("data-product-type");
      if (type === "service") {
        var $tr = $(this).closest("tr"),
          option_quantity = $tr.find(".quantity").val(),
          option_value_id = $tr.find("select.product-select").find(":selected").val(),
          url = url_get_consumables_in_option + "/" + option_value_id;

        DealConsumablesFillAdd(url, option_quantity);
      }
    });
}

async function DealConsumablesFillAdd(url, option_quantity) {
  await getConsumablesInOption(url);

  if (consumables_in_option.length > 0) {
    var first_line = true;
    for (let i = 0; i < consumables_in_option.length; i++) {

      consumables_in_option[i].quantity = +option_quantity * +consumables_in_option[i].quantity;

      if (first_line !== true) newLine($("#tabConsumables"));
      else first_line = false;

      var $tr = $("#tabConsumables").find("tr.product").eq(-1);
      $tr.find("select.product-select").append(new Option(consumables_in_option[i].name, consumables_in_option[i].product_id))
      
      $tr.find(".quantity").val(consumables_in_option[i].quantity);
      $tr.find(".price").val(consumables_in_option[i].cost);
      $tr.find(".input-group-text.quantity").text(consumables_in_option[i].unit);
    }

    $("#tabConsumables").find("tr.product").each(function () {
        var $this = $(this);
        UpdateProductSelect($this);
        UpdateStockSelect($this);
        UpdateSum($this);
      });
  }
}

var consumables_in_option = {};
function getConsumablesInOption(url) {
  return fetch(url, {
    method: "GET",
    headers: {
      "Content-type": "application/json; charset=UTF-8",
    },
  })
    .then((res) => res.json())
    .then((data) => (window.consumables_in_option = data));
}
