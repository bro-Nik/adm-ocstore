from datetime import datetime

from clim.jinja_filters import smart_date
from clim.utils import smart_int


def money(number):
    number = smart_int(number)
    number = '{:,}'.format(number).replace(',', ' ')
    return number.replace('.', ',')


def smart_phone(phone_number: str) -> str:
    if not phone_number:
        return ''
    numbers = list(filter(str.isdigit, phone_number))[1:]
    return "+7 {}{}{} {}{}{}-{}{}-{}{}".format(*numbers)


def datetime_from_str(string: str) -> datetime | str:
    try:
        return datetime.strptime(string, "%d.%m.%Y %H:%M")
    except ValueError:
        return ''
    except TypeError:
        return ''


def dt_to_str(date_time):
    return datetime.strftime(date_time, "%d.%m.%Y %H:%M")
