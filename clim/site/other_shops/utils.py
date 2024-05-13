from .models import db, OtherProduct, OtherCategory, OtherShops


def get_other_product(product_id: int):
    return db.session.execute(
        db.select(OtherProduct).filter_by(other_product_id=product_id)).scalar()


def get_other_shops():
    return db.session.execute(db.select(OtherShops)).scalars()


def get_shop(id):
    return db.session.execute(
            db.select(OtherShops).filter_by(shop_id=id)).scalar()


def get_categories(shop_id):
    return db.session.execute(
        db.select(OtherCategory).filter_by(shop_id=shop_id)).scalars()


def get_category(id):
    return db.session.execute(
        db.select(OtherCategory).filter_by(other_category_id=id)).scalar()


def int_or_other(number, default):
    return int(number, 0) if number else default
