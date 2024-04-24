from .models import Employment, db


def get_event_booking(event):
    if event:
        return tuple(db.session.execute(
                     db.select(Employment).filter_by(event=event)).scalars())


def get_booking(employment_id):
    return db.session.execute(
        db.select(Employment).filter_by(employment_id=employment_id)).scalar()
