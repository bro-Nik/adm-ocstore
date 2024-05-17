from functools import cached_property
import json
import os
from flask import current_app, flash

from clim.utils import OptionUtils, ProductUtils

from .app import db


class Product(ProductUtils, db.Model):
    __tablename__ = 'oc_product'
    product_id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(64), default='')
    sku = db.Column(db.String(64), default='')
    upc = db.Column(db.String(64), default='')
    mpn = db.Column(db.String(64), default='')
    location = db.Column(db.String(128), default='')
    ean = db.Column(db.String(64), default='')
    jan = db.Column(db.String(64), default='')
    isbn = db.Column(db.String(64), default='')
    image = db.Column(db.String(255))
    tax_class_id = db.Column(db.Integer)
    images = db.relationship('ProductImage',
                             backref=db.backref('product', lazy=True))
    related_products = db.relationship('ProductRelated',
                                    backref=db.backref('product', lazy=True))
    manufacturer = db.relationship('Manufacturer',
                                   backref=db.backref('products', lazy=True))
    manufacturer_id = db.Column(db.Integer,
                                db.ForeignKey('oc_manufacturer.manufacturer_id'),
                                default=0)
    shipping = db.Column(db.Boolean, default=0)
    options_buy = db.Column(db.Boolean, default=0)
    price = db.Column(db.Float(15.4), default=0)
    points = db.Column(db.Integer, default=0)
    tax_class_id = db.Column(db.Integer, default=0)
    date_available = db.Column(db.Date, default=0)
    weight = db.Column(db.Float(15.4), default=0)
    weight_class_id = db.Column(db.Integer,
                                db.ForeignKey('oc_weight_class.weight_class_id'),
                                default=0)
    length = db.Column(db.Float(15.4), default=0)
    width = db.Column(db.Float(15.4), default=0)
    height = db.Column(db.Float(15.4), default=0)
    length_class_id = db.Column(db.Integer, default=0)
    subtract = db.Column(db.Boolean, default=0)
    minimum = db.Column(db.Integer, default=0)
    sort_order = db.Column(db.Integer, default=0)
    status = db.Column(db.Boolean, default=0)
    viewed = db.Column(db.Integer, default=0)
    date_added = db.Column(db.Date, default=0)
    date_modified = db.Column(db.Date, default=0)
    noindex = db.Column(db.Boolean, default=1)
    cost = db.Column(db.Float, default=0)
    description = db.relationship('ProductDescription',
                                  backref='product', uselist=False)
    other_shop = db.relationship('OtherProduct', backref='product', lazy=True)
    quantity = db.Column(db.Integer, default=0)
    suppler_code = db.Column(db.Integer, default=0)
    suppler_type = db.Column(db.Integer, default=0)
    attributes = db.relationship('ProductAttribute',
                                 backref='product', lazy=True)
    stock_status_id = db.Column(db.Integer,
                                db.ForeignKey('oc_stock_status.stock_status_id'),
                                default=0)
    stock_status = db.relationship('StockStatus',
                                   backref=db.backref('products', lazy=True))
    special_offers = db.relationship('ProductSpecial',
                                     backref=db.backref('products', lazy=True))
    variants = db.relationship('ProductVariant',
                                  backref='product', uselist=False)
    unit_class = db.relationship('WeightClass',
                                   backref=db.backref('products', lazy=True))
    reviews = db.relationship('Review',
                              backref=db.backref('product', lazy=True))


    @cached_property
    def main_category(self):
        d = db.session.execute(
            db.select(ProductToCategory)
            .filter_by(product_id=self.product_id, main_category=1)).scalar()
        return d.category if d else None

    @cached_property
    def url(self):
        return db.session.execute(
            db.select(SeoUrl)
            .filter_by(query=f'product_id={self.product_id}')).scalar()

    @staticmethod
    def child_dependencies() -> list:
        return ['description', 'url', 'related_products', 'attributes',
                'reviews', 'options', 'images', 'variants', 'downloads']

    def delete(self) -> bool:
        """ Удаление товара и все, что с ним связано """

        # Если есть остатки - не удалять
        if self.stocks:
            flash(f'У товара {self.name} есть остатки на складе', 'warning')
            return True  # error

        image_path = current_app.config['IMAGE_PATH']
        if self.image and os.path.isfile(image_path + self.image):
            os.remove(image_path + self.image)

        if self.categories:
            for category in self.categories:
                category.products.remove(self)

        if self.other_shop:
            for other_product in self.other_shop:
                other_product.link_confirmed = None
                other_product.product_id = 0

        download_path = current_app.config['DOWNLOAD_PATH']
        if self.downloads:
            for download in self.downloads:

                if len(download.products) == 1:
                    if os.path.isfile(download_path + download.filename):
                        os.remove(download_path + download.filename)

                    if download.description:
                        db.session.delete(download.description)

                    db.session.delete(download)
                else:
                    download.products.remove(self)

        self.delete_dependencies()
        db.session.delete(self)
        return False


class ProductImage(db.Model):
    __tablename__ = 'oc_product_image'
    product_image_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('oc_product.product_id'),
                           primary_key=True)
    image = db.Column(db.String(255))

    def delete(self):
        image_path = current_app.config['IMAGE_PATH']
        other_images = db.session.execute(
            db.select(ProductImage).filter(
                (ProductImage.product_id != self.product_id)
                & (ProductImage.image == self.image))).scalar()
        if not other_images and os.path.isfile(image_path + self.image):
            os.remove(image_path + self.image)

        self.product_id = None
        db.session.delete(self)


class ProductRelated(db.Model):
    __tablename__ = 'oc_product_related'
    product_id = db.Column(db.Integer, db.ForeignKey('oc_product.product_id'),
                           primary_key=True)
    related_id = db.Column(db.Integer,
                           primary_key=True)


class ProductVariant(db.Model):
    __tablename__ = 'oc_prodvar'
    prodvar_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('oc_product.product_id'))
    prodvar_title = db.Column(db.Text)
    prodvar_product_str_id = db.Column(db.Text)

    def delete(self):
        variants = db.session.execute(
            db.select(ProductVariant)
            .filter(ProductVariant.prodvar_product_str_id.contains(self.product_id))).scalars()

        for variant in variants:
            ids = variant.prodvar_product_str_id.split(',')
            if id in ids:
                ids.remove(str(self.product_id))
                variant.prodvar_product_str_id = ','.join(ids)

        db.session.delete(self)


class ProductSpecial(db.Model):
    __tablename__ = 'oc_product_special'
    product_special_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('oc_product.product_id'))
                           # primary_key=True)
    customer_group_id = db.Column(db.Integer)
    priority = db.Column(db.Integer, default=0)
    price = db.Column(db.Float)
    date_start = db.Column(db.Date)
    date_end = db.Column(db.Date, default=0)
    special_offer_id = db.Column(db.Integer)


class Manufacturer(db.Model):
    __tablename__ = 'oc_manufacturer'
    manufacturer_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))


class ProductDescription(db.Model):
    __tablename__ = 'oc_product_description'
    product_id = db.Column(db.Integer, db.ForeignKey('oc_product.product_id'),
                           primary_key=True)
    language_id = db.Column(db.Integer)
    name = db.Column(db.String(255), default='')
    description = db.Column(db.Text, default='')
    short_description = db.Column(db.Text, default='')
    tag = db.Column(db.Text, default='')
    meta_title = db.Column(db.String(255), default='')
    meta_description = db.Column(db.String(255), default='')
    meta_keyword = db.Column(db.String(255), default='')
    meta_h1 = db.Column(db.String(255), default='')


class ProductToCategory(db.Model):
    __tablename__ = 'oc_product_to_category'
    product_id = db.Column(db.Integer,
                           db.ForeignKey('oc_product.product_id'),
                           primary_key=True)
    category_id = db.Column(db.Integer,
                            db.ForeignKey('oc_category.category_id'),
                            primary_key=True)
    main_category = db.Column(db.Boolean)
    category = db.relationship('Category', uselist=False, viewonly=True)


product_to_download = db.Table('oc_product_to_download',
    db.Column('product_id', db.Integer, db.ForeignKey('oc_product.product_id')),
    db.Column('download_id', db.Integer, db.ForeignKey('oc_download.download_id'))
)


class Download(db.Model):
    __tablename__ = 'oc_download'
    download_id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(160))
    products = db.relationship('Product', secondary=product_to_download,
                               backref=db.backref('downloads', lazy='dynamic'))
    description = db.relationship('DownloadDescription',
                                  backref='download', uselist=False)


class DownloadDescription(db.Model):
    __tablename__ = 'oc_download_description'
    download_id = db.Column(db.Integer,
                            db.ForeignKey('oc_download.download_id'),
                            primary_key=True)
    name = db.Column(db.String(64))


class Category(db.Model):
    __tablename__ = 'oc_category'
    category_id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('oc_category.category_id'))
    sort_order = db.Column(db.Integer)
    products = db.relationship('Product', secondary='oc_product_to_category',
                               backref=db.backref('categories', lazy='dynamic'))
    description = db.relationship('CategoryDescription',
                                  backref='description', uselist=False)
#
#     # Relationships
    child_categories = db.relationship(
        "Category",
        primaryjoin="Category.category_id == foreign(Category.parent_id)",
        viewonly=True,
        # backref=db.backref('parent_category', lazy=True)
    )

    @cached_property
    def url(self):
        param = f'category_id={self.category_id}'
        return db.session.execute(db.select(SeoUrl).filter_by(query=param)).scalar()


class CategoryDescription(db.Model):
    __tablename__ = 'oc_category_description'
    category_id = db.Column(db.Integer,
                            db.ForeignKey('oc_category.category_id'),
                            primary_key=True)
    name = db.Column(db.String(255))


class ProductAttribute(db.Model):
    __tablename__ = 'oc_product_attribute'
    product_id = db.Column(db.Integer,
                           db.ForeignKey('oc_product.product_id'),
                           primary_key=True)
    attribute_id = db.Column(db.Integer,
                             db.ForeignKey('oc_attribute.attribute_id'),
                             primary_key=True)
    text = db.Column(db.Text)

class Option(db.Model):
    __tablename__ = 'oc_option'
    option_id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(32))
    sort_order = db.Column(db.Integer)
    opt_image = db.Column(db.Boolean)
    description = db.relationship('OptionDescription',
                                  backref='option', uselist=False)
    settings = db.relationship('OptionSetting',
                                  backref='option', uselist=False)
    values = db.relationship('OptionValue',
                                   backref=db.backref('option', lazy=True))

    @staticmethod
    def child_dependencies() -> list:
        return ['description', 'settings']


class OptionDescription(db.Model):
    __tablename__ = 'oc_option_description'
    option_id = db.Column(db.Integer,
                          db.ForeignKey('oc_option.option_id'), primary_key=True)
    language_id = db.Column(db.Integer)
    name = db.Column(db.String(128))


class OptionValue(OptionUtils, db.Model):
    __tablename__ = 'oc_option_value'

    option_value_id = db.Column(db.Integer, primary_key=True)
    option_id = db.Column(db.Integer,
                          db.ForeignKey('oc_option.option_id'))
    sort_order = db.Column(db.Integer)
    image = db.Column(db.String(255), default='')
    description = db.relationship('OptionValueDescription',
    backref='description1', uselist=False)
    settings = db.relationship('OptionValueSetting',
                                  backref='value', uselist=False)
    products_options = db.relationship('ProductOptionValue',
                                  backref=db.backref('product_option', lazy=True))

    @staticmethod
    def child_dependencies() -> list:
        return ['settings', 'description']

    def auto_compare(self):
        settings = json.loads(option_value.option.settings.text)
        products = Product.all_by_filter(filter=get_filter_options(option_value),
                                         pagination=False)

        products_ids = []
        for product in products:
            products_ids.append(product.product_id)
            product_have_this_option = product_clean_other_options(product,
                                                                   option_value)

            db.session.commit()

            if product_have_this_option:
                continue
            else:
                product_option = new_product_option(product.product_id,
                                                    option_value,
                                                    settings)

                product.options.append(product_option)
        db.session.commit()

        other_products_in_option = other_products_in_option_value(option_value)

        for product in other_products_in_option:
            for option in product.options:
                db.session.delete(option.product_option_value)
                db.session.delete(option)

    def clean_options(self):
        for product_option in self.products_options:
            product = Product.get(product_option.product_id)

            for option in product.options:
                if option.product_option_value:
                    db.session.delete(option.product_option_value)
                db.session.delete(option)


class OptionSetting(db.Model):
    __tablename__ = 'adm_option_settings'
    option_id = db.Column(db.Integer,
                          db.ForeignKey('oc_option.option_id'),
                          primary_key=True)
    text = db.Column(db.Text)


class OptionValueDescription(db.Model):
    __tablename__ = 'oc_option_value_description'
    option_value_id = db.Column(db.Integer,
                                db.ForeignKey('oc_option_value.option_value_id'),
                                primary_key=True)
    option_id = db.Column(db.Integer,
                          db.ForeignKey('oc_option.option_id'))
    language_id = db.Column(db.Integer)
    name = db.Column(db.String(128))


class OptionValueSetting(db.Model):
    __tablename__ = 'adm_option_value_settings'
    option_value_id = db.Column(db.Integer,
                          db.ForeignKey('oc_option_value.option_value_id'),
                          primary_key=True)
    price = db.Column(db.Float(15.4))
    settings = db.Column(db.Text)
    consumables = db.Column(db.Text)


class ProductOption(db.Model):
    __tablename__ = 'oc_product_option'
    product_option_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer,
                           db.ForeignKey('oc_product.product_id'))
    option_id = db.Column(db.Integer)
    value = db.Column(db.Text)
    required = db.Column(db.Boolean)
    product_option_value = db.relationship('ProductOptionValue',
                                           backref='product_option_',
                                           uselist=False)
    product = db.relationship('Product',
                              backref=db.backref('options', lazy=True))

    @staticmethod
    def child_dependencies() -> list:
        return ['product_option_value']


class ProductOptionValue(db.Model):
    __tablename__ = 'oc_product_option_value'
    product_option_value_id = db.Column(db.Integer, primary_key=True)
    product_option_id = db.Column(db.Integer,
                                db.ForeignKey('oc_product_option.product_option_id'))
    option_id = db.Column(db.Integer)
    product_id = db.Column(db.Integer,
                                db.ForeignKey('oc_product.product_id'))
    option_value_id = db.Column(db.Integer,
                                db.ForeignKey('oc_option_value.option_value_id'),
                                db.ForeignKey('oc_option_value_description.option_value_id'))
    quantity = db.Column(db.Integer)
    subtract = db.Column(db.Boolean)
    price = db.Column(db.Float(15.4))
    price_prefix = db.Column(db.String(1))
    points = db.Column(db.Integer)
    points_prefix = db.Column(db.String(1))
    weight = db.Column(db.Float)
    weight_prefix = db.Column(db.String(1))
    model = db.Column(db.String(256))
    optsku = db.Column(db.String(64))


class Attribute(db.Model):
    __tablename__ = 'oc_attribute'
    attribute_id = db.Column(db.Integer, primary_key=True)
    sort_order = db.Column(db.Integer)
    description = db.relationship('AttributeDescription',
                                  backref='description', uselist=False)
    product_attributes = db.relationship('ProductAttribute',
                                  backref='main_attribute', uselist=False)


class AttributeDescription(db.Model):
    __tablename__ = 'oc_attribute_description'
    attribute_id = db.Column(db.Integer,
                             db.ForeignKey('oc_attribute.attribute_id'),
                             primary_key=True)
    name = db.Column(db.String(256))


class WeightClass(db.Model):
    __tablename__ = 'oc_weight_class'
    weight_class_id = db.Column(db.Integer, primary_key=True)
    description = db.relationship('WeightClassDescription',
                                  backref='weight_class', uselist=False)


class WeightClassDescription(db.Model):
    __tablename__ = 'oc_weight_class_description'
    weight_class_id = db.Column(db.Integer,
                                db.ForeignKey('oc_weight_class.weight_class_id'),
                                primary_key=True)
    language_id = db.Column(db.Integer)
    title = db.Column(db.String(32))
    unit = db.Column(db.String(4))


class SeoUrl(db.Model):
    __tablename__ = 'oc_seo_url'
    seo_url_id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(255))
    keyword = db.Column(db.String(255))


class Review(db.Model):
    __tablename__ = 'oc_review'
    review_id = db.Column(db.Integer, primary_key=True)
    # product_id = db.Column(db.Integer)
    product_id = db.Column(db.Integer, db.ForeignKey('oc_product.product_id'),
                           primary_key=True)


class RedirectManager(db.Model):
    __tablename__ = 'oc_redirect_manager'
    redirect_manager_id = db.Column(db.Integer, primary_key=True)
    active = db.Column(db.Boolean)
    from_url = db.Column(db.Text)
    to_url = db.Column(db.Text)
    response_code = db.Column(db.Integer)
    date_start = db.Column(db.Date)
    date_end = db.Column(db.Date)
    times_used = db.Column(db.Integer)


class Module(db.Model):
    __tablename__ = 'adm_modules'
    # module_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text)


class StockStatus(db.Model):
    __tablename__ = 'oc_stock_status'
    stock_status_id = db.Column(db.Integer, primary_key=True)
    language_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))


class SpecialOffer(db.Model):
    __tablename__ = 'oc_special_offer'
    special_offer_id = db.Column(db.Integer, primary_key=True)
    offer_type = db.Column(db.Integer)
    list_customer_group_id = db.Column(db.String(255))
    priority = db.Column(db.Integer)
    date_start = db.Column(db.Date)
    date_end = db.Column(db.Date)
    gift_product_id = db.Column(db.Integer)
    product_quantity = db.Column(db.Integer)
    product_sum = db.Column(db.Float)
    gift_quantity = db.Column(db.Integer)
    percent = db.Column(db.Float)
    timer_status = db.Column(db.Boolean)
    free_shipping = db.Column(db.Boolean)
    cycle_of_timer = db.Column(db.Integer)
    offer_status = db.Column(db.Boolean)
    selling_price = db.Column(db.Integer)
    description = db.relationship('SpecialOfferDescription',
                                  backref='offer', uselist=False)


class SpecialOfferDescription(db.Model):
    __tablename__ = 'oc_special_offer_description'
    special_offer_id = db.Column(db.Integer,
                                 db.ForeignKey('oc_special_offer.special_offer_id'),
                                 primary_key=True)
    language_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    description = db.Column(db.Text)
    meta_title = db.Column(db.String(255))
