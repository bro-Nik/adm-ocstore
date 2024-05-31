from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user, logout_user

from ..app import db
from . import bp, utils


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Отдает страницу входа и принимает форму."""
    if current_user.is_authenticated:
        return redirect(url_for('crm.deal.deals'))

    if request.method == 'POST':
        # Проверка данных
        if utils.login(request.form) is True:
            page = request.args.get('next', url_for('crm.deal.deals'))
            return redirect(page)

    return render_template('user/login.html')


@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():

    if request.method == 'POST':
        # Проверка старого пароля
        if current_user.check_password(request.form.get('old_pass')):
            new_pass = request.form.get('new_pass')
            # Пароль с подтверждением совпадают
            if new_pass == request.form.get('new_pass2'):
                current_user.set_password(new_pass)
                db.session.commit()
                flash('Пароль обновлен')
            else:
                flash('Новые пароли не совпадают', 'warning')
        else:
            flash('Не верный старый пароль', 'warning')

    return render_template('user/password.html')


@bp.route('/logout')
@login_required
def logout():
    """Выводит пользователя из системы."""
    logout_user()
    return redirect(url_for('.login'))


@bp.after_request
def redirect_to_signin(response):
    """Перекидывает на странизу авторизации."""
    if response.status_code == 401:
        return redirect(f"{url_for('.login')}?next={request.url}")

    return response
