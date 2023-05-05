from itertools import product
from clim.app import db
from flask_login import UserMixin


class Product(db.Model):
    __tablename__ = 'oc_product'
    product_id = db.Column(db.Integer, primary_key=True)
    mpn = db.Column(db.String(64))
    ean = db.Column(db.String(64))
    image = db.Column(db.String(255))
    price = db.Column(db.Float(15.4))
    images = db.relationship('ProductImage',
                             backref=db.backref('product', lazy=True))
    related_products = db.relationship('ProductRelated',
                                    backref=db.backref('product', lazy=True))
    manufacturer = db.relationship('Manufacturer',
                                   backref=db.backref('products', lazy=True))
    manufacturer_id = db.Column(db.Integer,
                                db.ForeignKey('oc_manufacturer.manufacturer_id'))
    description = db.relationship('ProductDescription',
                                  backref='product', uselist=False)
    other_shop = db.relationship('OtherProduct', backref='product', lazy=True)
    isbn = db.Column(db.String(64))
    jan = db.Column(db.String(64))
    quantity = db.Column(db.Integer)
    viewed = db.Column(db.Integer)
    attributes = db.relationship('ProductAttribute',
                                   backref='product', lazy=True)
    sort_order = db.Column(db.Integer)


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
    product_id = db.Column(db.Integer)
    prodvar_product_str_id = db.Column(db.Text)


class Manufacturer(db.Model):
    __tablename__ = 'oc_manufacturer'
    manufacturer_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))


class ProductDescription(db.Model):
    __tablename__ = 'oc_product_description'
    product_id = db.Column(db.Integer, db.ForeignKey('oc_product.product_id'),
                           primary_key=True)
    name = db.Column(db.String(255))


product_to_category = db.Table('oc_product_to_category',
    db.Column('product_id', db.Integer, db.ForeignKey('oc_product.product_id')),
    db.Column('category_id', db.Integer, db.ForeignKey('oc_category_description.category_id')),
    db.Column('main_category', db.Boolean)
)


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
    description = db.relationship('CategoryDescription',
                                  backref='description', uselist=False)


class CategoryDescription(db.Model):
    __tablename__ = 'oc_category_description'
    category_id = db.Column(db.Integer,
                            db.ForeignKey('oc_category.category_id'),
                            primary_key=True)
    name = db.Column(db.String(255))
    products = db.relationship('Product', secondary=product_to_category,
        backref=db.backref('categories', lazy='dynamic'))


class ProductAttribute(db.Model):
    __tablename__ = 'oc_product_attribute'
    product_id = db.Column(db.Integer,
                           db.ForeignKey('oc_product.product_id'),
                           primary_key=True)
    attribute_id = db.Column(db.Integer, primary_key=True)
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
    image = db.Column(db.String(255))
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


class AttributeDescription(db.Model):
    __tablename__ = 'oc_attribute_description'
    attribute_id = db.Column(db.Integer,
                             db.ForeignKey('oc_attribute.attribute_id'),
                             primary_key=True)
    name = db.Column(db.String(256))


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
