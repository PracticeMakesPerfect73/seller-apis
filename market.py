"""Модуль содержит функции для загрузки и обновления остатков и цен товаров."""
import datetime
import logging.config
from environs import Env
from seller import download_stock

import requests

from seller import divide, price_conversion

logger = logging.getLogger(__file__)


def get_product_list(page, campaign_id, access_token):
    """Получает список товаров с Яндекс Маркета.

    Функция отправляет запрос к API Yandex для получения списка товаров,
    учитывая id кампании и учетные данные.

    Args:
        page (str): Токен страницы для пагинации.
        campaign_id (str): id кампании на Маркете.
        access_token (str): Токен доступа к API.

    Returns:
        dict: Словарь с результатами запроса, содержащий список товаров.

    Raises:
        requests.exceptions.HTTPError: В случае ошибки HTTP.
    """
    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {
        "page_token": page,
        "limit": 200,
    }
    url = endpoint_url + f"campaigns/{campaign_id}/offer-mapping-entries"
    response = requests.get(url, headers=headers, params=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object.get("result")


def update_stocks(stocks, campaign_id, access_token):
    """Обновляет информацию об остатках товаров.

    Функция отправляет запрос к API Yandex для обновления количества
    товаров на складе.

    Args:
        stocks (list): Список товаров с остатками.
        campaign_id (str): id кампании на Маркете.
        access_token (str): Токен доступа к API.

    Returns:
        dict: Ответ API в виде словаря с информацией об обновлении остатков.
    """
    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {"skus": stocks}
    url = endpoint_url + f"campaigns/{campaign_id}/offers/stocks"
    response = requests.put(url, headers=headers, json=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object


def update_price(prices, campaign_id, access_token):
    """Обновляет цены товаров на Маркете.

    Функция отправляет запрос к API Yandex для обновления цен товаров.

    Args:
        prices (list): Список товаров с ценами.
        campaign_id (str): id кампании на Маркете.
        access_token (str): Токен доступа к API.

    Returns:
        dict: Ответ API в виде словаря с информацией об обновлении цен.
    """
    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {"offers": prices}
    url = endpoint_url + f"campaigns/{campaign_id}/offer-prices/updates"
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object


def get_offer_ids(campaign_id, market_token):
    """Получает артикулы (shopSku) товаров из кампании на Яндекс маркете.

    Функция выполняет постраничный запрос списка товаров и собирает их
    артикулы (shopSku). Если товаров много, загружается несколько страниц.

    Args:
        campaign_id (str): id кампании.
        market_token (str): Токен доступа к API.

    Returns:
        list: Список артикулов товаров.
    """
    page = ""
    product_list = []
    while True:
        some_prod = get_product_list(page, campaign_id, market_token)
        product_list.extend(some_prod.get("offerMappingEntries"))
        page = some_prod.get("paging").get("nextPageToken")
        if not page:
            break
    offer_ids = []
    for product in product_list:
        offer_ids.append(product.get("offer").get("shopSku"))
    return offer_ids


def create_stocks(watch_remnants, offer_ids, warehouse_id):
    """Формирует список остатков товаров для загрузки в Яндекс Маркет.

    Перебирает список товаров и формирует список для обновления остатков.
    Если товар есть в `offer_ids`, он добавляется в список остатков,
    иначе — игнорируется.
    Значения `Количество` обрабатываются:
      - ">10" заменяется на 100
      - "1" заменяется на 0 (нулевой остаток)
      - Остальные значения переводятся в `int`

    Args:
        watch_remnants (list): Список товаров с их количеством.
        offer_ids (list): Список артикулов товаров, загруженных на Маркет.
        warehouse_id (int): id склада.

    Returns:
        list: Список остатков товаров в формате API Яндекс Маркета.
    """
    stocks = list()
    date = str(datetime.datetime.utcnow().replace(microsecond=0).isoformat()
               + "Z")
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            count = str(watch.get("Количество"))
            if count == ">10":
                stock = 100
            elif count == "1":
                stock = 0
            else:
                stock = int(watch.get("Количество"))
            stocks.append(
                {
                    "sku": str(watch.get("Код")),
                    "warehouseId": warehouse_id,
                    "items": [
                        {
                            "count": stock,
                            "type": "FIT",
                            "updatedAt": date,
                        }
                    ],
                }
            )
            offer_ids.remove(str(watch.get("Код")))
    for offer_id in offer_ids:
        stocks.append(
            {
                "sku": offer_id,
                "warehouseId": warehouse_id,
                "items": [
                    {
                        "count": 0,
                        "type": "FIT",
                        "updatedAt": date,
                    }
                ],
            }
        )
    return stocks


def create_prices(watch_remnants, offer_ids):
    """Создает список цен товаров для загрузки на Яндекс Маркет.

    Перебирает список товаров и формирует список словарей с ценами.
    Обрабатываются только товары, чьи артикулы есть в `offer_ids`.
    В коде оставлены закомментированные параметры, которые можно
    включить при необходимости.

    Args:
        watch_remnants (list): Список товаров с их ценами.
        offer_ids (list): Список артикулов товаров.

    Returns:
        list: Список словарей с ценами товаров в формате API Яндекс Маркета.
    """
    prices = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            price = {
                "id": str(watch.get("Код")),
                # "feed": {"id": 0},
                "price": {
                    "value": int(price_conversion(watch.get("Цена"))),
                    # "discountBase": 0,
                    "currencyId": "RUR",
                    # "vat": 0,
                },
                # "marketSku": 0,
                # "shopSku": "string",
            }
            prices.append(price)
    return prices


async def upload_prices(watch_remnants, campaign_id, market_token):
    """Загружает цены товаров в Яндекс Маркет.

    Функция асинхронно загружает список цен для предложений,
    указанных в `watch_remnants`.

    Args:
        watch_remnants (list): Список товаров с ценами.
        campaign_id (str): id кампании.
        market_token (str): Токен доступа к API.

    Returns:
        list: Список словарей с ценами.
    """
    offer_ids = get_offer_ids(campaign_id, market_token)
    prices = create_prices(watch_remnants, offer_ids)
    for some_prices in list(divide(prices, 500)):
        update_price(some_prices, campaign_id, market_token)
    return prices


async def upload_stocks(watch_remnants, campaign_id,
                        market_token, warehouse_id):
    """Загружает остатки товаров в Яндекс Маркет.

    Функция асинхронно загружает остатки товаров для предложений,
    указанных в `watch_remnants`.

    Args:
        watch_remnants (list): Список товаров с остатками.
        campaign_id (str): id кампании.
        market_token (str): Токен доступа к API.
        warehouse_id (int): id склада.

    Returns:
        tuple: Кортеж из двух элементов:
        - list: Список товаров, у которых остаток больше 0.
        - list: Список всех товаров с их остатками, включая те,
        у которых остаток равен 0.
    """
    offer_ids = get_offer_ids(campaign_id, market_token)
    stocks = create_stocks(watch_remnants, offer_ids, warehouse_id)
    for some_stock in list(divide(stocks, 2000)):
        update_stocks(some_stock, campaign_id, market_token)
    not_empty = list(
        filter(lambda stock: (stock.get("items")[0].get("count") != 0), stocks)
    )
    return not_empty, stocks


def main():
    """Основная функция для загрузки и обновления остатков и цен товаров.

    Эта функция инициализирует необходимые параметры из переменных
    окружения, а затем выполняет следующие шаги:
    1. Получает список id предложений с помощью `get_offer_ids`
    для кампаний FBS и DBS
    2. Создает и обновляет остатки товаров, используя функции
    `create_stocks` и `update_stocks`, обрабатывая данные партиями по 2000
    для кампаний FBS и DBS
    3. Обновляет цены товаров, используя функцию `upload_prices`
    для кампаний FBS и DBS
    4. Обрабатывает исключения, связанные с таймаутами и проблемами с
    подключением, а также другие возможные ошибки.

    Exceptions:
        requests.exceptions.ReadTimeout: Ошибка, возникающая при превышении
        времени ожидания ответа от сервера.
        requests.exceptions.ConnectionError: Ошибка при установлении
        соединения с сервером.
        Exception: Обработка других общих ошибок.
    """
    env = Env()
    market_token = env.str("MARKET_TOKEN")
    campaign_fbs_id = env.str("FBS_ID")
    campaign_dbs_id = env.str("DBS_ID")
    warehouse_fbs_id = env.str("WAREHOUSE_FBS_ID")
    warehouse_dbs_id = env.str("WAREHOUSE_DBS_ID")

    watch_remnants = download_stock()
    try:
        offer_ids = get_offer_ids(campaign_fbs_id, market_token)
        stocks = create_stocks(watch_remnants, offer_ids, warehouse_fbs_id)
        for some_stock in list(divide(stocks, 2000)):
            update_stocks(some_stock, campaign_fbs_id, market_token)
        upload_prices(watch_remnants, campaign_fbs_id, market_token)

        offer_ids = get_offer_ids(campaign_dbs_id, market_token)
        stocks = create_stocks(watch_remnants, offer_ids, warehouse_dbs_id)
        for some_stock in list(divide(stocks, 2000)):
            update_stocks(some_stock, campaign_dbs_id, market_token)
        upload_prices(watch_remnants, campaign_dbs_id, market_token)
    except requests.exceptions.ReadTimeout:
        print("Превышено время ожидания...")
    except requests.exceptions.ConnectionError as error:
        print(error, "Ошибка соединения")
    except Exception as error:
        print(error, "ERROR_2")


if __name__ == "__main__":
    main()
