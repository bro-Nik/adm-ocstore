import pickle
import json
from datetime import datetime
import locale

from clim.main import bp
from clim.models import OptionValue, Product


def smart_int(number):
    ''' Float без точки, если оно целое '''
    if not number:
        return 0
    elif int(number) == number:
        return int(number)
    else:
        return round(number, 2)


bp.add_app_template_filter(smart_int)


def money(number):
    number = smart_int(number)
    number = '{:,}'.format(number).replace(',', ' ')
    return number.replace('.', ',')


bp.add_app_template_filter(money)


def to_json(str):
    if not str:
        return []
    return json.loads(str)


bp.add_app_template_filter(to_json)


def smart_date(date_time):
    ''' Возвращает сколько прошло от входящей даты '''
    locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

    if type(date_time) == str:
        if 'T' in date_time:
            date_time = date_time.replace('T', ' ') + ':0.0'
        elif len(date_time) == 16:
            date_time = date_time + ':0.0'
        date_time = datetime.strptime(
            date_time, '%d.%m.%Y %H:%M:%S.%f')
            # date_time, '%Y-%m-%d %H:%M:%S.%f')

    delta_time = datetime.now() - date_time
    current_date = datetime.now().date()
    if current_date == datetime.date(date_time):
        if delta_time.total_seconds() < 60:
            result = 'только что'
        elif 60 <= delta_time.total_seconds() < 120:
            result = '1 минуту назад'
        elif 120 <= delta_time.total_seconds() < 300:
            result = str(int(delta_time.total_seconds() / 60)) + ' минуты назад'
        elif 300 <= delta_time.total_seconds() < 3600:
            result = str(int(delta_time.total_seconds() / 60)) + ' минут назад'
        else:
            result = 'сегодня, ' + str(datetime.strftime(date_time, '%H:%M'))
    elif 0 < (current_date - datetime.date(date_time)).days < 2:
        result = 'вчера, ' + str(datetime.strftime(date_time, '%H:%M'))
    else:
        date = str(datetime.strftime(date_time, '%d ')) + date_time.strftime('%B')
        year = datetime.date(date_time).year
        year = ' ' + str(year) if year != datetime.now().year else ''
        time = str(datetime.strftime(date_time, '%H:%M'))
        time = ', ' + time if time != '00:00' else ''

        result = date + year + time

    return result


bp.add_app_template_filter(smart_date)


def how_long_ago(event_date):
    ''' Возвращает сколько прошло от входящей даты '''
    if type(event_date) == str:
        event_date = datetime.strptime(event_date, '%Y-%m-%d')

    today = datetime.now().date()
    if today == datetime.date(event_date):
        result = 'сегодня'
    else:
        result = str((today - datetime.date(event_date)).days) + ' д. назад'

    return result


bp.add_app_template_filter(how_long_ago)


def smart_phone(phone_number: str) -> str:
    if not phone_number:
        return ''
    numbers = list(filter(str.isdigit, phone_number))[1:]
    return "+7 {}{}{} {}{}{}-{}{}-{}{}".format(*numbers)


bp.add_app_template_filter(smart_phone)
