from thefuzz import fuzz as f

from clim.app import celery
from clim.models import db
from clim.site.other_shops.models import OtherProduct

from .utils import get_products, products_prices_module


@celery.task()
def comparison_products(filter_by: dict) -> None:
    """ Подбирает похожие товары """
    products = get_products(pagination=False, filter=filter_by)

    other_products = tuple(db.session.execute(
        db.select(OtherProduct)
        .filter(OtherProduct.link_confirmed == None)).scalars())

    def matching_set(matching, product, other_product):
        id = other_product.other_product_id
        matching_list[id] = {'product_id': product.product_id,
                             'matching': matching,
                             'shop_id': other_product.shop_id}

    matching_list = {}

    for product in products:
        shops_ids = []
        if product.other_shop:
            for comp_product in product.other_shop:
                if comp_product.link_confirmed:
                    shops_ids.append(comp_product.shop_id)

        product_name = product.description.name.lower()

        for other_product in other_products:

            if other_product.shop_id in shops_ids:
                continue

            other_product_name = other_product.name.lower()

            matching = f.ratio(product_name, other_product_name)
            if matching < 60:
                continue

            if not matching_list.get(other_product.other_product_id):
                matching_set(matching, product, other_product)

            elif (matching > matching_list[other_product.other_product_id]['matching']):
                matching_set(matching, product, other_product)

    for x_id in list(matching_list.items()):
        for y_id in list(matching_list.items()):
            if x_id[0] == y_id[0]:
                continue

            if (x_id[1]['product_id'] == y_id[1]['product_id']
                    and x_id[1]['matching'] > y_id[1]['matching']
                    and x_id[1]['shop_id'] == y_id[1]['shop_id']):
                matching_list.pop(y_id[0])

    for other_product in other_products:
        if matching_list.get(other_product.other_product_id):
            other_product.product_id = matching_list[other_product.other_product_id]['product_id']

    db.session.commit()
    print('End')


@celery.task()
def change_prices(filter_by, price_type):
    settings = products_prices_module.get_settings()
    delta = settings.get('price_delta')
    if delta:
        delta = float(delta) / 100

    products = tuple(get_products(pagination=False, filter=filter_by))

    def convert_price(price):
        try:
            return float(price)
        except ValueError:
            return 0

    def update_price(product, other_price):
        if not delta or abs(product.price - other_price) <= product.price * delta:
            product.new_price(other_price, price_type)

    for product in products:
        if not product.other_shop:
            continue

        # Одна цена конкурента
        if len(product.other_shop) < 2:
            other_price = convert_price(product.other_shop[0].price)
            update_price(product, other_price)
            continue

        # Несколько цен конкурентов
        prices = []
        for other_product in product.other_shop:
            other_price = convert_price(other_product.price)
            if other_price:
                prices.append(float(other_price))

        prices = sorted(prices)
        while prices:
            other_price = prices.pop(0)
            update_price(product, other_price)
            if product.price == other_price:
                break

    db.session.commit()
