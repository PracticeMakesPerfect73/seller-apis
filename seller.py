"""Модуль содержит функции для загрузки и обновления остатков и цен товаров."""
import io
import logging.config
import os
import re
import zipfile
from environs import Env

import pandas as pd
import requests

logger = logging.getLogger(__file__)


def get_product_list(last_id, client_id, seller_token):
    """Получает список товаров магазина Ozon.

    Функция отправляет запрос к API Ozon для получения списка товаров,
    учитывая id последнего товара и учетные данные клиента.

    Args:
        last_id (str): id последнего полученного товара.
        client_id (str): id клиента Ozon.
        seller_token (str): API-ключ продавца для авторизации запроса.

    Returns:
        dict: Словарь с результатами запроса, содержащий список товаров.

    Raises:
        requests.exceptions.RequestException: В случае ошибки при
        выполнении запроса.
    """
    url = "https://api-seller.ozon.ru/v2/product/list"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {
        "filter": {
            "visibility": "ALL",
        },
        "last_id": last_id,
        "limit": 1000,
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    response_object = response.json()
    return response_object.get("result")


def get_offer_ids(client_id, seller_token):
    """Получает артикулы товаров магазина Ozon.

    Функция запрашивает список всех товаров, доступных в магазине,
    и извлекает их артикулы (offer_id).

    Args:
        client_id (str): id клиента Ozon.
        seller_token (str): API-ключ продавца для авторизации запроса.

    Returns:
        list: Список строковых значений offer_id всех товаров в магазине.

    Raises:
        requests.exceptions.RequestException: В случае ошибки при
        выполнении запроса.
    """
    last_id = ""
    product_list = []
    while True:
        some_prod = get_product_list(last_id, client_id, seller_token)
        product_list.extend(some_prod.get("items"))
        total = some_prod.get("total")
        last_id = some_prod.get("last_id")
        if total == len(product_list):
            break
    offer_ids = []
    for product in product_list:
        offer_ids.append(product.get("offer_id"))
    return offer_ids


def update_price(prices: list, client_id, seller_token):
    """Обновляет цены товаров.

    Функция отправляет запрос к API Ozon для обновления цен товаров.
    Принимает список цен, идентификатор клиента и API-ключ продавца
    для авторизации.

    Args:
        prices (list): Список словарей с информацией о ценах товаров.
        client_id (str): id клиента Ozon.
        seller_token (str): API-ключ продавца для авторизации запроса.

    Returns:
        dict: Ответ API в виде словаря с информацией об обновлении цен.

    Raises:
        requests.exceptions.RequestException: В случае ошибки при
        выполнении запроса.
    """
    url = "https://api-seller.ozon.ru/v1/product/import/prices"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {"prices": prices}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def update_stocks(stocks: list, client_id, seller_token):
    """Обновляет остатки товаров.

    Функция отправляет запрос к API Ozon для обновления количества
    товаров на складе.
    Принимает список остатков, идентификатор клиента и API-ключ
    продавца для авторизации.

    Args:
        stocks (list): Список словарей, содержащих информацию об
        остатках товаров.
        client_id (str): id клиента Ozon.
        seller_token (str): API-ключ продавца для авторизации запроса.

    Returns:
        dict: Ответ API в виде словаря с информацией об обновлении остатков.

    Raises:
        requests.exceptions.RequestException: В случае ошибки
        при выполнении запроса.
    """
    url = "https://api-seller.ozon.ru/v1/product/import/stocks"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {"stocks": stocks}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def download_stock():
    """Скачивает файл 'ostatki.xls' с сайта casio.

    Скачивает и распаковывает архив с остатками товаров с сайта сasio,
    обрабатывает Excel файл и возвращает данные в виде списка словарей.
    Также удаляет временно скачанный файл 'ostatki.xls'.

    Returns:
        list: Список словарей, где каждый словарь содержит
        данные об остатках часов.
    """
    casio_url = "https://timeworld.ru/upload/files/ostatki.zip"
    session = requests.Session()
    response = session.get(casio_url)
    response.raise_for_status()
    with response, zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(".")
    excel_file = "ostatki.xls"
    watch_remnants = pd.read_excel(
        io=excel_file,
        na_values=None,
        keep_default_na=False,
        header=17,
    ).to_dict(orient="records")
    os.remove("./ostatki.xls")
    return watch_remnants


def create_stocks(watch_remnants, offer_ids):
    """Создает список остатков на складе для предложений в offer_ids.

    Функция принимает список остатков товаров (watch_remnants) и список id
    предложений (offer_ids). Для каждого товара из watch_remnants,
    если его код присутствует в offer_ids, добавляется
    запись о количестве товара на складе. Если количество товара указано
    как ">10", то количество устанавливается равным 100. Если количество
    равно "1", то устанавливается 0. Если товар не найден в
    watch_remnants, то для него добавляется запись с количеством 0.

    Args:
        watch_remnants (list): Список словарей с информацией о товарах
        на складе.
        offer_ids (list): Список строк, содержащих id предложений,
        для которых нужно создать остатки.

    Returns:
        list: Список словарей, каждый из которых содержит:
              - "offer_id" (str): id предложения.
              - "stock" (int): Количество товара на складе
              для этого предложения.

    Example:
        watch_remnants = [{"Код": "1", "Количество": "5"},
                            {"Код": "2", "Количество": "14"}]
        offer_ids = ["1", "2", "3"]
        result = create_stocks(watch_remnants, offer_ids)
        print(result)
        # Вывод: [{'offer_id': '1', 'stock': 5},
                    {'offer_id': '2', 'stock': 100},
                    {'offer_id': '3', 'stock': 0}]
    """
    stocks = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            count = str(watch.get("Количество"))
            if count == ">10":
                stock = 100
            elif count == "1":
                stock = 0
            else:
                stock = int(watch.get("Количество"))
            stocks.append({"offer_id": str(watch.get("Код")), "stock": stock})
            offer_ids.remove(str(watch.get("Код")))
    for offer_id in offer_ids:
        stocks.append({"offer_id": offer_id, "stock": 0})
    return stocks


def create_prices(watch_remnants, offer_ids):
    """Создает список цен для предложений, указанных в offer_ids.

    Функция принимает список остатков товаров (watch_remnants) и
    список id предложений (offer_ids). Для каждого товара из watch_remnants,
    добавляется информация о цене товара. Значение цены получается с помощью
    функции `price_conversion`, а также устанавливаются значения для других
    параметров, таких как валюта (RUB) и статус автоматического
    действия (UNKNOWN).

    Args:
        watch_remnants (list): Список словарей с информацией о товарах.
        offer_ids (list): Список строк, содержащих id предложений, для
        которых нужно создать цены.

    Returns:
        list: Список словарей, каждый из которых содержит:
              - "offer_id" (str): id предложения.
              - "auto_action_enabled" (str): Статус автоматического действия.
              По умолчанию "UNKNOWN".
              - "currency_code" (str): Код валюты. По умолчанию "RUB".
              - "old_price" (str): Старая цена товара. По умолчанию "0".
              - "price" (float): Новая цена товара, преобразованная с помощью
              функции `price_conversion`.

    Example:
        watch_remnants = [{"Код": "1", "Цена": "1000"},
        {"Код": "2", "Цена": "2000"}]
        offer_ids = ["1", "2", "3"]
        result = create_prices(watch_remnants, offer_ids)
        print(result)
        # Вывод: [
        #     {'offer_id': '1', 'auto_action_enabled': 'UNKNOWN',
        'currency_code': 'RUB', 'old_price': '0', 'price': 1000.0},
        #     {'offer_id': '2', 'auto_action_enabled': 'UNKNOWN',
        'currency_code': 'RUB', 'old_price': '0', 'price': 2000.0}
        # ]
    """
    prices = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            price = {
                "auto_action_enabled": "UNKNOWN",
                "currency_code": "RUB",
                "offer_id": str(watch.get("Код")),
                "old_price": "0",
                "price": price_conversion(watch.get("Цена")),
            }
            prices.append(price)
    return prices


def price_conversion(price: str) -> str:
    """Преобразует строку с ценой в числовой формат без лишних символов.

    Args:
        price (str): Строка с ценой, которая может содержать символы валюты
            и знаки форматирования (например, "5'990.00 руб.").

    Returns:
        str: Строковое представление очищенной целочисленной цены
            (например, "5990").
    """
    return re.sub("[^0-9]", "", price.split(".")[0])


def divide(lst: list, n: int):
    """Разделяет список lst на части по n элементов.

    Args:
        lst (list): Список, который нужно разделить на части.
        n (int): Количество элементов в каждой части.

    Returns:
        генератор: Генератор, который возвращает части списка
        длиной до n элементов.
    """
    for i in range(0, len(lst), n):
        yield lst[i: i + n]


async def upload_prices(watch_remnants, client_id, seller_token):
    """Загружает цены для предложений и обновляет их партиями по 1000.

    Функция асинхронно загружает список цен для предложений,
    указанных в `watch_remnants`.

    Args:
        watch_remnants (list): Список словарей с информацией о товарах.
        client_id (str): id клиента, необходимый для получения и
        обновления информации.
        seller_token (str): API-ключ продавца для авторизации запроса.

    Returns:
        list: Список словарей с ценами для каждого предложения,
        который был передан в функцию.
    """
    offer_ids = get_offer_ids(client_id, seller_token)
    prices = create_prices(watch_remnants, offer_ids)
    for some_price in list(divide(prices, 1000)):
        update_price(some_price, client_id, seller_token)
    return prices


async def upload_stocks(watch_remnants, client_id, seller_token):
    """Загружает остатки товаров и обновляет их партиями по 100.

    Функция асинхронно загружает остатки товаров для предложений,
    указанных в `watch_remnants`.

    Args:
        watch_remnants (list): Список словарей с информацией о товарах.
        client_id (str): id клиента, необходимый для получения и
        обновления информации.
        seller_token (str): API-ключ продавца для авторизации запроса.

    Returns:
        tuple: Кортеж из двух элементов:
        - list: Список товаров, у которых остаток больше 0.
        - list: Список всех товаров с их остатками, включая те,
        у которых остаток равен 0.
    """
    offer_ids = get_offer_ids(client_id, seller_token)
    stocks = create_stocks(watch_remnants, offer_ids)
    for some_stock in list(divide(stocks, 100)):
        update_stocks(some_stock, client_id, seller_token)
    not_empty = list(filter(lambda stock: (stock.get("stock") != 0), stocks))
    return not_empty, stocks


def main():
    """Основная функция для загрузки и обновления остатков и цен товаров.

    Эта функция инициализирует необходимые параметры из переменных
    окружения (SELLER_TOKEN и CLIENT_ID),
    а затем выполняет следующие шаги:
    1. Получает список id предложений с помощью `get_offer_ids`.
    2. Загружает данные об остатках товаров с помощью `download_stock`.
    3. Создает и обновляет остатки товаров, используя функции
    `create_stocks` и `update_stocks`, обрабатывая данные партиями по 100.
    4. Создает и обновляет цены товаров, используя функции `create_prices`
    и `update_price`, обрабатывая данные партиями по 900.
    5. Обрабатывает исключения, связанные с таймаутами и проблемами с
    подключением, а также другие возможные ошибки.

    Exceptions:
        requests.exceptions.ReadTimeout: Ошибка, возникающая при превышении
        времени ожидания ответа от сервера.
        requests.exceptions.ConnectionError: Ошибка при установлении
        соединения с сервером.
        Exception: Обработка других общих ошибок.
    """
    env = Env()
    seller_token = env.str("SELLER_TOKEN")
    client_id = env.str("CLIENT_ID")
    try:
        offer_ids = get_offer_ids(client_id, seller_token)
        watch_remnants = download_stock()
        stocks = create_stocks(watch_remnants, offer_ids)
        for some_stock in list(divide(stocks, 100)):
            update_stocks(some_stock, client_id, seller_token)
        prices = create_prices(watch_remnants, offer_ids)
        for some_price in list(divide(prices, 900)):
            update_price(some_price, client_id, seller_token)
    except requests.exceptions.ReadTimeout:
        print("Превышено время ожидания...")
    except requests.exceptions.ConnectionError as error:
        print(error, "Ошибка соединения")
    except Exception as error:
        print(error, "ERROR_2")


if __name__ == "__main__":
    main()
