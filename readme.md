# Краткое объяснение по всем модулям приложения
Приложение создано для сбора данных с instagram и 4 сайтов с прогнозами

## Запуск
Запускается все через основной скрипт management/management.py, который принимает следующие аргументы:
1. Ресурс - (instagram, odds, stavka, vseprosport, vprognoze)
2. Инстаграм каналы в список через пробел (только если Ресурс - instagram)

### flask_app
1. api.py - основной модуль апика с flask-ким приложением
2. wsgi.py - точка входа для gunicorn
3. apivenv - virtualenv для gunicorn

### helpers
Пакет с различными помощниками(обёртками)
1. category_translation.py - Хранит в себе dictionary с переводом различных неструктурированных видов спорта в 1 стандартный eng формат
2. downloader_helper.py - Обёртка для http запросов, с handling-ом плохих ответов, работой с прокси и т.д
3. helpers.py - Различные однофункциональные хелперы
4. proxy_helper - Скрипт для работы с прокси, вычисление скорости их работы, фильтр умерших и т.д

### management.py
1. management.py - Модуль для запуска приложения

### resource.py
1. base_forcasts.py - Абстрактный модуль сайта с прописанной структурой и логикой обработки данных
2. instagram_parser.py - Модуль работы с инстаграмом
3. odds.py - Модуль работы с odds.ru
4. stavka.py - Модуль работы с stavka.tv
5. vprognoze.py - Модуль работы с vprognoze.ru
6. vseprosport.py - Модуль работы с vseprosport.ru
7. resources.py - dictionary для импорта Ресурсов

### storage
1. mongodb_storage.py - Основной модуль работы с MongoDB 

### stream
Директория для хранения файлов с odds.ru, vseprosport.ru и инстаграма

## config.ini
Параметры интерфейса, которые возможно понадобится менять

### instagram
1. PASSWORD - Пароль от инстаграм аккаунта (не используется)
2. LOGIN - Логин от инстаграм аккаунта (не используется)
3. scraping_date_limit - Лимит дней, за который парсятся аккаунты

### forecasts
1. scraping_page_limit - Лимит по кол-ву спаршенных страниц
2. scraping_date_limit - Лимит дней, за который парсятся сайты
3. login - логин для vprognoze
4. password - пароль для vprognoze
### server
1. old_remove - Кол-во дней, за которые файлы хранятся в stream/
2. domain - Домен для апика, чтобы формировать ссылку на файлы из stream/
3. proxy_key - ключ с best-proxies.ru
