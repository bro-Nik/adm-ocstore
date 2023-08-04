from flask_sqlalchemy import SQLAlchemy
from itertools import product
# from clim.app import db
from flask_login import UserMixin


db = SQLAlchemy()


class Product(db.Model):
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


class ProductImage(db.Model):
    __tablename__ = 'oc_product_image'
    product_image_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('oc_product.product_id'),
                           primary_key=True)
    image = db.Column(db.String(255))


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


class ProductSpecial(db.Model):
    __tablename__ = 'oc_product_special'
    product_special_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('oc_product.product_id'),
                           primary_key=True)
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
    category = db.relationship('Category',
                               uselist=False,
                               viewonly=True)


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
    parent_id = db.Column(db.Integer)
    sort_order = db.Column(db.Integer)
    products = db.relationship('Product', secondary='oc_product_to_category',
        backref=db.backref('categories', lazy='dynamic'))
    description = db.relationship('CategoryDescription',
                                  backref='description', uselist=False)


# class CategoryPath(db.Model):
#     __tablename__ = 'oc_category_path'
#     category_id = db.Column(db.Integer, primary_key=True)
#     path_id = db.Column(db.Integer, primary_key=True)
#     level = db.Column(db.Integer)


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


class OptionDescription(db.Model):
    __tablename__ = 'oc_option_description'
    option_id = db.Column(db.Integer,
                          db.ForeignKey('oc_option.option_id'), primary_key=True)
    language_id = db.Column(db.Integer)
    name = db.Column(db.String(128))


class OptionValue(db.Model):
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
                                  backref='product_option_', uselist=False)
    product = db.relationship('Product',
                                   backref=db.backref('options', lazy=True))


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


class OtherShops(db.Model):
    __tablename__ = 'adm_other_shops'
    shop_id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(64))
    name = db.Column(db.String(64))
    parsing = db.Column(db.String(256))


class OtherProduct(db.Model):
    __tablename__ = 'adm_other_product'
    other_product_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('oc_product.product_id'), nullable=True)
    shop = db.relationship('OtherShops',
                                   backref=db.backref('products', lazy=True))
    shop_id = db.Column(db.Integer,
                                db.ForeignKey('adm_other_shops.shop_id'))
    name = db.Column(db.String(256))
    price = db.Column(db.String(64))
    link = db.Column(db.String(256))
    link_confirmed = db.Column(db.Boolean)
    text = db.Column(db.String(256))
    category = db.relationship('OtherCategory',
                                   backref=db.backref('products', lazy=True))
    category_id = db.Column(db.Integer,
                                db.ForeignKey('adm_other_category.other_category_id'))


class SeoUrl(db.Model):
    __tablename__ = 'oc_seo_url'
    seo_url_id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(255))
    keyword = db.Column(db.String(255))


class OtherCategory(db.Model):
    __tablename__ = 'adm_other_category'
    other_category_id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer)
    name = db.Column(db.String(256))
    minus = db.Column(db.String(1024))
    url = db.Column(db.String(256))
    parsing = db.Column(db.String(1024))
    last_parsing = db.Column(db.String(256))
    changes = db.Column(db.String(1024))
    shop = db.relationship('OtherShops',
                                   backref=db.backref('categories', lazy=True))
    shop_id = db.Column(db.Integer,
                                db.ForeignKey('adm_other_shops.shop_id'))
    new_price = db.Column(db.Text)
    new_product = db.Column(db.Text)
    sort = db.Column(db.Integer)


class User(db.Model, UserMixin):
    __tablename__ = 'adm_user'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)


class Review(db.Model):
    __tablename__ = 'oc_review'
    review_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer)


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


# class Setting(db.Model):
#     __tablename__ = 'adm_setting'
#     setting_id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(64))
#     value = db.Column(db.Text)


class Module(db.Model):
    __tablename__ = 'adm_modules'
    module_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
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


class Stock(db.Model):
    __tablename__ = 'adm_stock'
    stock_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    sort = db.Column(db.Integer)
    products = db.relationship('StockProduct',
                              backref=db.backref('stock', lazy=True))


class StockProduct(db.Model):
    __tablename__ = 'adm_stock_product'
    product_id = db.Column(db.Integer,
                           db.ForeignKey('oc_product.product_id'),
                           primary_key=True)
    stock_id = db.Column(db.Integer,
                         db.ForeignKey('adm_stock.stock_id'),
                         primary_key=True)
    quantity = db.Column(db.Float)
    main_product = db.relationship('Product',
                              backref=db.backref('stocks', lazy=True))


class Deal(db.Model):
    __tablename__ = 'adm_deal'
    deal_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    contact_id = db.Column(db.Integer, db.ForeignKey('adm_contact.contact_id'))
    stage_id = db.Column(db.Integer, db.ForeignKey('adm_deal_stage.stage_id'))
    details = db.Column(db.Text)
    products = db.Column(db.Text)
    consumables = db.Column(db.Text)
    expenses = db.Column(db.Text)
    posted = db.Column(db.Boolean)
    date_add = db.Column(db.Date)
    date_end = db.Column(db.Date)
    sum = db.Column(db.Float(15.4))
    analytics = db.Column(db.Text)
    profit = db.Column(db.Float(15.4))
    sort_order = db.Column(db.Integer)


class DealStage(db.Model):
    __tablename__ = 'adm_deal_stage'
    stage_id = db.Column(db.Integer, primary_key=True,)
    name = db.Column(db.String(128))
    type = db.Column(db.String(64))
    sort_order = db.Column(db.Integer)
    color = db.Column(db.String(45))
    deals = db.relationship('Deal',
                            backref=db.backref('stage', lazy=True),
                            order_by='Deal.sort_order'
                            )


class Contact(db.Model):
    __tablename__ = 'adm_contact'
    contact_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    phone = db.Column(db.String(64))
    email = db.Column(db.String(64))
    deals = db.relationship('Deal',
                            backref=db.backref('contact', lazy=True))


class StockMovement(db.Model):
    __tablename__ = 'adm_stock_movement'
    movement_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    date = db.Column(db.Date)
    posted = db.Column(db.Boolean)
    products = db.Column(db.Text)
    movement_type = db.Column(db.String(32))
    details = db.Column(db.Text)
    stocks = db.Column(db.Text)


class StockCategory(db.Model):
    __tablename__ = 'adm_stock_category'
    stock_category_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))


class Worker(db.Model):
    __tablename__ = 'adm_worker'
    worker_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(45))
    start_day = db.Column(db.Time)
    end_day = db.Column(db.Time)
    employments = db.relationship('WorkerEmployment',
                            backref=db.backref('worker', lazy=True))


class WorkerEmployment(db.Model):
    __tablename__ = 'adm_worker_employment'
    employment_id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('adm_worker.worker_id'))
    title = db.Column(db.String(64))
    date_start = db.Column(db.Date)
    date_end = db.Column(db.Date)
    time_start = db.Column(db.Time)
    time_end = db.Column(db.Time)
    event = db.Column(db.String(64))


class DealService(db.Model):
    __tablename__ = 'adm_deal_service'
    service_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(45))
    time = db.Column(db.Integer)

