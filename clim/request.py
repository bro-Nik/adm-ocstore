from __future__ import annotations
import random
import requests

from clim.proxy import get_proxies


def proxy_request(url) -> dict:
    # Неверная ссылка
    if not url.startswith('http'):
        return {'error': 'Неверная ссылка'}

    proxies_list = []
    for _, proxy in get_proxies().items():
        if isinstance(proxy, dict):
            p = f"{proxy['type']}://{proxy['user']}:{proxy['pass']}@{proxy['host']}:{proxy['port']}"
            proxies_list.append(p)

    while proxies_list:
        index = random.randint(0, len(proxies_list) - 1)
        try:
            proxies = {"http": proxies_list[index], "https": proxies_list[index]}

            response = requests.get(url, proxies=proxies)
            return {'response': response}

        except requests.exceptions.ConnectionError as e:
            proxies_list.remove(proxies_list[index])

    return {'error': 'Нет прокси'}
