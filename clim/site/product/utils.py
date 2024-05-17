from datetime import datetime
import json
from flask import current_app, flash, request, session
from clim.models import Category, Module, Product, ProductAttribute, \
    ProductSpecial, ProductVariant, RedirectManager, StockStatus, db
from clim.site.other_shops.models import OtherProduct
from clim.utils import DiscountProducts, smart_int


def get_filter(method=None, path=None):
    if method == 'POST':
        f = request.form
        session['categories_ids'] = f.getlist('categories_ids')
        session['manufacturers_ids'] = f.getlist('manufacturers_ids')
        session['stock'] = f.get('stock')
        session['field'] = f.get('field')
        session['new_products'] = f.get('new_products')
        if path:
            session[path + '_other_filter'] = f.get('other_filter')

        session['results_per_page'] = f.get('results_per_page')
        session['group_attribute'] = f.get('group_attribute', 0, type=int)

    filter = {
        'categories_ids': session.get('categories_ids'),
        'manufacturers_ids': session.get('manufacturers_ids'),
        'stock': session.get('stock'),
        'field': session.get('field'),
        'group_attribute': session.get('group_attribute'),
        'new_products': session.get('new_products')
    }

    if path:
        filter['other_filter'] = session.get(path + '_other_filter')
    return filter


def get_stock_statuses():
    return db.session.execute(
        db.select(StockStatus).filter_by(language_id=1)).scalars()


class ProductsPricesModule:
    def __init__(self):
        self.module = None
        self.settings = None

    # @cached_property
    def load_module(self):
        if not self.module:
            self.module = db.session.execute(
                db.select(Module).filter_by(name='products_prices')).scalar()
        return self.module

    # @cached_property
    def get_settings(self):
        self.load_module()
        if not self.settings:
            self.settings = json.loads(self.module.value) if self.module else {}
        return self.settings

    def set_settings(self, settings):
        self.load_module()
        if not self.module:
            self.module = Module(name='products_prices')
            db.session.add(self.module)
        self.module.value = json.dumps(settings)
        self.module = None


products_prices_module = ProductsPricesModule()


def manual_confirm_prices(ids, price_type):
    """ Ручное применение цен """
    for data in ids:
        product_id, new_price = data.split('-')
        product = Product.get(product_id)
        product.new_price(float(new_price), price_type)


def manual_comparison(ids, action):
    """ Ручное применение цен """
    for product_id in ids:
        other_product = OtherProduct.get(product_id)
        if not other_product:
            continue

        if action == 'bind':
            other_product.link_confirmed = True

            other_compared = (db.session.execute(
                db.select(OtherProduct)
                .filter_by(product_id=other_product.product_id)
                .filter(OtherProduct.shop_id == other_product.shop_id)
                .filter(OtherProduct.other_product_id != other_product.other_product_id))
                .scalars())
            for product in other_compared:
                product.product_id = None

        elif action == 'unbind':
            other_product.link_confirmed = None
            other_product.product_id = 0


def new_stiker(self):
    settings = products_prices_module.get_settings()
    discount_products = DiscountProducts().get()

    if self.product_id in discount_products:
        options_ids = settings.get('options_ids') or []

        for option in self.options:
            if str(option.option_id) in options_ids:
                price = option.product_option_value.price + self.price
                text = settings.get('stiker_text')
                if text:
                    self.ean = text.replace('price', f'{smart_int(price)}')


def new_price(self, price, price_type):
    """ Записывает цену товара и удаляет лишние """
    settings = products_prices_module.get_settings()
    special_offer_id = settings.get('special_offer_id', 0)

    product_special_offer = None
    delete_special_offer = False
    if self.special_offers:
        for special_offer in self.special_offers:
            if int(special_offer.special_offer_id) == int(special_offer_id):
                product_special_offer = special_offer
                break

    if price_type == 'normal_price':
        self.price = price
        delete_special_offer = True

    elif price_type == 'special_price':
        if self.price <= price:
            self.price = price
            delete_special_offer = True
        else:
            if not product_special_offer:
                product_special_offer = ProductSpecial(
                    customer_group_id=1,
                    special_offer_id=special_offer_id,
                    product_id=self.product_id
                )
                # product.special_offers.append(product_special_offer)
                db.session.add(product_special_offer)

            product_special_offer.price = price
            product_special_offer.date_start = datetime.now().date()
            product_special_offer.date_end = 0

    if delete_special_offer and product_special_offer:
        db.session.delete(product_special_offer)

    self.new_stiker()


def update_variants(self):
    main_category = self.main_category

    series = ''
    for attribute in self.attributes:
        if attribute.attribute_id == 134:
            series = attribute.text
            break

    products = Product.query
    if main_category:
        products = (products.join(Product.categories)
                    .filter(Category.category_id == main_category.category_id))

    products = (products.join(Product.attributes)
                    .where((ProductAttribute.attribute_id == 134)
                           & (ProductAttribute.text == series)))
    products = products.all()

    for product in products:
        for attribute in product.attributes:
            if attribute.attribute_id == 55:
                product.upc = round(float(attribute.text) / 500) * 5
                break

    title = '{"1":"Модельный ряд:"}'

    product_ids_in_series = {}
    for product in products:
        for attribute in product.attributes:
            if attribute.attribute_id != 134:
                continue

            product_ids_in_series[int(product.upc)] = product.product_id
            break

    product_ids_in_series = dict(sorted(product_ids_in_series.items()))
    product_ids_in_series = list(product_ids_in_series.values())

    for product_id in product_ids_in_series:

        variants_in_base = db.session.execute(
            db.select(ProductVariant)
            .filter_by(product_id=product_id)).scalar()
        if variants_in_base:
            variants_in_base.prodvar_title = title
            variants_in_base.prodvar_product_str_id = ','.join(map(str, product_ids_in_series))
        else:
            new_variant = ProductVariant(
                product_id=product_id,
                prodvar_title=title,
                prodvar_product_str_id=','.join(map(str, product_ids_in_series))
            )
            db.session.add(new_variant)

    for product in products:
        for attribute in product.attributes:
            if attribute.attribute_id == 55:
                self.upc = f'до {self.upc} м²'
                break

    return product_ids_in_series


@property
def stock_status(self):
    if self.price == 100001 and self.quantity == 1:
        return 'Запрос цены'
    if self.quantity == 10:
        return 'В наличии'
    if self.quantity == 1:
        return 'Под заказ'
    if self.quantity == 0:
        return 'Нет в наличии'


def update_stock_status(self, status: str) -> bool:
    # Запрос цены
    if status == 'price_request':
        self.price = 100001
        self.quantity = 1
    else:
        if self.price == 100001:
            flash(f'{self.name}. Цена не установлена', 'warning')
            return True

        settings = {}

        settings_in_base = db.session.execute(
            db.select(Module).filter_by(name='stock_statuses')).scalar()
        if settings_in_base:
            settings = json.loads(settings_in_base.value)

        status_type = settings.get(status, '')
        self.stock_status_id = int(status)

        if status_type == 'В наличии':
            self.quantity = 10
        elif status_type == 'Под заказ':
            self.quantity = 1
        elif status_type == 'Нет в наличии':
            self.quantity = 0
    return False


def redirect(self, action: str, to_url) -> bool:
    catalog_path = current_app.config['CATALOG_DOMAIN']
    if not catalog_path:
        flash('Не задан url каталога', 'warning')
        return True

    # Seo url
    from_url = f'{catalog_path}{self.url.keyword}' if self.url else None

    # Добавляем редирект
    if 'redirect_to_category' in action:
        if self.main_category and self.main_category.url:
            to_url = f'{catalog_path}{self.main_category.url.keyword}'

    if not to_url:
        flash(f'{self.name} Не задан url редиректа', 'warning')
        return True

    if from_url and to_url:
        redirect = RedirectManager(
            active=1,
            from_url=from_url,
            to_url=to_url,
            response_code=301,
            date_start=datetime.now().date(),
            date_end=0,
            times_used=0
        )
        db.session.add(redirect)
    return False


Product.new_price = new_price
Product.new_stiker = new_stiker
Product.update_variants = update_variants
Product.update_stock_status = update_stock_status
Product.redirect = redirect
Product.stock_status = stock_status
