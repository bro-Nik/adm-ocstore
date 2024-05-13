from datetime import datetime
import json
import re
import time

from bs4 import BeautifulSoup
from flask import flash

from clim.app import celery
from clim.models import db
from clim.request import proxy_request

from .models import OtherProduct
from .utils import get_category


@celery.task()
def get_other_products_task(category_id, test=None):
    cat = get_category(category_id)
    parsing = json.loads(cat.parsing)
    prefix = cat.shop.domain if cat.shop.parsing == 'domain' else cat.url
    page = 1
    result = []
    new_price_ids = cat.new_price.split(',') if cat.new_price else []
    new_product_ids = cat.new_product.split(',') if cat.new_product else []

    links_list = []

    def block_find(block) -> bool:
        return block and block != -1

    error = ''
    attempts = 5
    while True:
        attempts -= 1
        if attempts < 0 or not parsing:
            return

        # ToDo
        if page > 5:
            break

        if error:
            if test:
                flash(error, 'warning')
                return
            print(error)
            error = ''

        url = f"{cat.url}{f'?page={page}' if page > 1 else ''}"
        response = proxy_request(url)

        if not response or response.status_code != 200:
            error = f'Ошибка запроса {response.status_code if response else ""}'
            # time.sleep(15)
            continue

        print(page)
        bs = BeautifulSoup(response.text, "lxml")
        blocks = bs.find(parsing['blocks_type'], parsing['blocks_class'])
        if not block_find(blocks):
            error = 'Не найден блок с товарами'
            continue

        for block in blocks:
            if not block_find(block):
                error = 'Не найден блок с товаром'
                continue

            # Ссылка
            link = None
            block_link = block.find(parsing['block_link_type'],
                                    parsing['block_link_class'])
            if not block_find(block_link):
                error = 'Не найден блок с ссылкой'
                continue

            href = block_link.a.get('href')
            if href:
                if prefix.endswith('/') and href.startswith('/'):
                    prefix = prefix[:-1]
                elif not prefix.endswith('/') and not href.startswith('/'):
                    prefix += '/'
                link = f'{prefix}{href}'.lower()

            if not link or link in links_list:
                continue

            links_list.append(link)

            # Наименование
            name = None
            block_name = block.find(parsing['block_name_type'],
                                    parsing['block_name_class'])
            if block_find(block_name):
                if parsing.get('block_name_inside'):
                    block_name = block_name.find(parsing['block_name_inside'])
            if not block_find(block_name):
                error = 'Не найден блок с названием'
                continue

            name = block_name.get_text()
            name = re.sub(parsing['minus'], '', name, flags=re.IGNORECASE)
            name = name.strip()
            if not name:
                continue

            # Цена
            price = 0
            block_price = block.find(parsing['block_price_type'],
                                     parsing['block_price_class'])
            if not block_find(block_price):
                block_price = block.find(parsing['block_other_price_type'],
                                         parsing['block_other_price_class'])
            if not block_find(block_price):
                error = 'Не найден блок с ценой'
                continue

            p = block_price.get_text(strip=True)
            if p:
                try:
                    price = re.sub(r'(руб.|руб| |р)', '', p, flags=re.IGNORECASE)
                    price = float(price)
                except ValueError:
                    pass

            if test:
                result.append({'name': name, 'link': link, 'price': price})
                continue

            product_in_base = db.session.execute(
                    db.select(OtherProduct).filter_by(link=link)).scalar()

            if not product_in_base:
                product_in_base = OtherProduct(shop_id=cat.shop_id,
                                               category_id=category_id,
                                               name=name,
                                               link=link,
                                               product_id=0)
                db.session.add(product_in_base)
                db.session.flush()
                new_product_ids.append(str(product_in_base.other_product_id))
            print(f'{name} {price}')

            try:
                product_in_base.price = float(product_in_base.price)
            except ValueError:
                product_in_base.price = float(0)

            if product_in_base.price != price:
                product_in_base.price = price
            product_in_base.text = str(datetime.now().date())

            if product_in_base.link_confirmed:
                new_price_ids.append(str(product_in_base.other_product_id))
                continue

        if test:
            return result

        page += 1
        time.sleep(5)

    cat.new_price = (',').join(new_price_ids)
    cat.new_product = (',').join(new_product_ids)

    cat.last_parsing = str(datetime.now().date())
    db.session.commit()
    print('End')