from __future__ import annotations

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from ..app import db


class User(db.Model, UserMixin):
    __tablename__ = 'adm_user'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)

    def set_password(self, password: str) -> None:
        """Изменение пароля пользователя."""
        self.password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Проверка пароля пользователя."""
        return check_password_hash(self.password, password)
