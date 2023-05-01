from flask import render_template, redirect, url_for, request, flash, session
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import requests
import pickle

from clim.app import app, db, login_manager, redis
from clim.models import User


# @app.route('/sign_up', methods=['GET', 'POST'])
# def sign_up():
#     login = request.form.get('login')
#     password = request.form.get('password')
#     password2 = request.form.get('password2')
#     if request.method == 'POST':
#         if not (login and password and password2):
#             flash('Пожалуйста заполните все поля')
#         elif db.session.execute(db.select(User)
#                                 .filter_by(login=login.lower())).scalar():
#             flash('Такой логин уже используется')
#         elif password != password2:
#             flash('Пароли не совпадают')
#         else:
#             hash_password = generate_password_hash(password)
#             new_user = User(login=login.lower(), password=hash_password)
#             db.session.add(new_user)
#             db.session.commit()
#             return redirect(url_for('sign_in'))
#
#         return redirect(url_for('sign_up'))
#     else:
#         return render_template('user/sign-up.html')


@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    login = request.form.get('login')
    password = request.form.get('password')

    if request.method == 'POST':
        if login and password:
            user = db.session.execute(db.select(User)
                                      .filter_by(login=login.lower())).scalar()

            if user and check_password_hash(user.password, password):
                login_user(user, remember=True)
                next_page = request.args.get('next') if request.args.get('next') else '/'
                return redirect(next_page)
            else:
                flash('Некорректные данные')
        else:
            flash('Введите данные')

    return render_template('user/sign-in.html')


@login_manager.user_loader
def load_user(user_id):
    return db.session.execute(db.select(User).filter_by(id=user_id)).scalar()


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('sign_in'))


@app.after_request
def redirect_to_signin(response):
    if response.status_code == 401:
        return redirect(url_for('sign_in') + '?next=' + request.url)

    return response
