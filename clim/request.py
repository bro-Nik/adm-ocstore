from __future__ import annotations
import random
import time
import requests

from clim.proxy import get_proxies


def proxy_request(url):
    # Неверная ссылка
    if not url.startswith('http'):
        return

    proxies_list = []
    for _, proxy in get_proxies().items():
        if isinstance(proxy, dict):
            p = f"{proxy['type']}://{proxy['user']}:{proxy['pass']}@{proxy['host']}:{proxy['port']}"
            proxies_list.append(p)

    # st_accept = "text/html"  # говорим веб-серверу, что хотим получить html
    # # имитируем подключение через браузер Mozilla на macOS
    # st_useragent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15"
    # # формируем хеш заголовков
    # headers = {
    #    "Accept": st_accept,
    #    "User-Agent": st_useragent
    # }

    while True:
        index = random.randint(0, len(proxies_list) - 1)
        try:
            proxies = {"http": proxies_list[index], "https": proxies_list[index]}

            # return requests.get(url, proxies=proxies, timeout=5)
            # return requests.get(url, proxies=proxies, verify=False)
            print(f'Попытка запроса, url: {url}, proxy: {proxies_list[index]}')
            return requests.get(url, proxies=proxies)
            # return requests.get(url, headers=headers, proxies=proxies)

        except requests.exceptions.ConnectionError as e:
            print(f'Ошибка: {e}')
            proxies_list.remove(proxies_list[index])

