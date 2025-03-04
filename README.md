## Описание скрипта seller.py
Скрипт автоматически обновляет остатки и цены товаров в магазине Ozon. 
Он получает список всех товаров, которые уже есть в магазине, затем скачивает
свежие данные об остатках с сайта Casio и сравнивает их с товарами, представленными на Ozon.
После этого он обновляет количество доступных товаров и их стоимость в соответствии с новыми данными.

Сначала скрипт запрашивает у Ozon список всех товаров, чтобы понять, какие артикулы уже загружены в магазин.
Далее он скачивает архив с сайта Casio, распаковывает его и извлекает нужный файл с остатками.
Этот файл обрабатывается, и из него формируется список товаров с их количеством и ценами.

Для корректного обновления остатков скрипт проверяет, какие товары есть в загруженном файле 
и сопоставляет их с товарами на Ozon. Если количество товара в файле указано как больше десяти, оно автоматически 
устанавливается на сто. Если в наличии только одна единица, она считается отсутствующей. Для всех товаров, которые 
были в магазине, но отсутствуют в загруженном файле, остаток сбрасывается в ноль.

Цены товаров также пересчитываются перед отправкой в Ozon. Они очищаются от лишних символов, таких как пробелы и 
знаки валюты, и приводятся к числовому формату. После этого скрипт формирует данные для обновления и отправляет 
их в Ozon небольшими порциями, чтобы избежать ограничений по количеству запросов.

## Описание скрипта market.py
Скрипт предназначен для обновления остатков и цен товаров на платформе Яндекс Маркет. 
Он работает с двумя типами кампаний: FBS и DBS. Основная цель — синхронизировать данные между вашим складом и 
Яндекс Маркетом, чтобы актуализировать информацию о товарах, их наличии и ценах.

Процесс работы скрипта начинается с получения списка товаров с использованием токена доступа. 
Далее скрипт обновляет данные о наличии товаров на складе и пересчитывает цены в соответствии с информацией об остатках. 
Если данные по товарам обновляются на одной платформе (например, FBS), то скрипт также синхронизирует 
эту информацию на другой платформе (например, DBS).

Скрипт делит данные на несколько частей для более эффективной загрузки, отправляя обновления порциями. 
Это важно, так как API Яндекс Маркета имеет ограничения по объему данных, которые можно отправить за один запрос.


