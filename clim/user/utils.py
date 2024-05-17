from datetime import datetime, timedelta, timezone
import json

from flask import flash
from flask_login import login_user

from ..app import login_manager, redis
from .models import db, User


LOGIN_ATTEMPTS = 3


@login_manager.user_loader
def find_user(user_id: int | None = None, login: str | None = None
              ) -> User | None:
# def find_user(login: str | None) -> User | None:
    """Возвращает пользователя."""
    select = db.select(User)
    if user_id:
        select = select.filter_by(id=user_id)
    else:
        select = select.filter_by(login=login)
    return db.session.execute(select).scalar()


def login(form: dict) -> bool:
    """Обработка формы входа. Вход пользовалетя"""
    login = form.get('login')
    password = form.get('password')
    redis_key = 'user_auth'

    # Поля не заполнены
    if not login or not password:
        flash('Введити логин и пароль', 'warning')
        return False

    # Поиск прошлых попыток входа
    login_attempts = redis.hget(redis_key, login)
    if login_attempts:
        login_attempts = json.loads(login_attempts.decode())
    if not isinstance(login_attempts, dict):
        login_attempts = {}

    # Проверка на блокировку входа
    block_time = login_attempts.get('next_try_time')
    if block_time:
        block_time = datetime.strptime(block_time, '%Y-%m-%d %H:%M:%S.%f%z')
        delta = (block_time - datetime.now(timezone.utc)).total_seconds()
        if delta > 0:
            m = int(delta // 60)
            s = int(delta - 60 * m) if m else int(delta)

            flash(f'Вход заблокирован. Осталось {m} мин. {s} сек.', 'warning')
            return False

    user = find_user(login)

    # Пользователь не найден
    if not user:
        flash('Неверный логин или пароль', 'warning')
        return False

    # Проверка пройдена
    if user.check_password(password):
        login_user(user, form.get('remember-me', False))
        redis.hdel(redis_key, login)
        return True

    # Проверка не пройдена
    flash('Неверный логин или пароль', 'warning')
    login_attempts.setdefault('count', 0)
    login_attempts['count'] += 1
    if login_attempts['count'] >= LOGIN_ATTEMPTS:
        next_try = datetime.now(timezone.utc) + timedelta(minutes=10)
        login_attempts['next_try_time'] = str(next_try)
        flash('Вход заблокирован на 10 минут', 'warning')

    redis.hset(redis_key, login, json.dumps(login_attempts))
    return False
