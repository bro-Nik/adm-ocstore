from clim.app import db
from clim.site.other_shops.utils import CategoryUtils, ShopUtils


class OtherShops(ShopUtils, db.Model):
    __tablename__ = 'adm_other_shops'
    shop_id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(64))
    name = db.Column(db.String(64))
    parsing = db.Column(db.String(256))

    @staticmethod
    def child_dependencies():
        return ['categories']


class OtherProduct(db.Model):
    __tablename__ = 'adm_other_product'
    other_product_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('oc_product.product_id'),
                           nullable=True)
    shop = db.relationship('OtherShops',
                            backref=db.backref('products', lazy=True))
    shop_id = db.Column(db.Integer, db.ForeignKey('adm_other_shops.shop_id'))
    name = db.Column(db.String(256))
    price = db.Column(db.String(64))
    link = db.Column(db.String(256))
    link_confirmed = db.Column(db.Boolean)
    text = db.Column(db.String(256))
    category = db.relationship('OtherCategory',
                               backref=db.backref('products', lazy=True))
    category_id = db.Column(db.Integer,
                            db.ForeignKey('adm_other_category.other_category_id'))


class OtherCategory(CategoryUtils, db.Model):
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

    # Relationships
    child_categories = db.relationship(
        "OtherCategory",
        primaryjoin="OtherCategory.other_category_id == foreign(OtherCategory.parent_id)",
        viewonly=True,
        # backref=db.backref('parent_category', lazy=True)
    )

    @staticmethod
    def child_dependencies():
        return ['products']
