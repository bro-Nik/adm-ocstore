from flask_sqlalchemy import Model


class ModelMixin(Model):

    @classmethod
    def find(cls, id):
        return 0
        # return db.session.execute(
        #     db.select(cls).filter_by(product_id=id)).scalar()
