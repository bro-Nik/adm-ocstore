import json
from clim.app import app


def smart_int(number):
    ''' Float без точки, если оно целое '''
    if int(number) == number:
        return int(number)
    else:
        return number

app.add_template_filter(smart_int)


def to_json(str):
    if not str:
        return []
    return json.loads(str)

app.add_template_filter(to_json)

