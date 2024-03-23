from ..app import db
from ..models import DealStage


def get_stage(stage_id: int = 0, stage_type: str = ''):
    if stage_id:
        select = db.select(DealStage).filter_by(stage_id=stage_id)
    elif stage_type:
        select = db.select(DealStage).filter_by(type=stage_type)
    else:
        return
    return db.session.execute(select).scalar()
