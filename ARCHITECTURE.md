---

## 🤖 Компоненты системы

- **user_bot** (`user_bot/main.py`):
    - Принимает только кнопочные команды.
    - Сценарии: "Рассчитать по ссылке", "Рассчитать вручную", "История запросов".
    - Конвертация валют по shared/currency_rates.json.
    - После любого действия — автоответ с предложением нажать /start.
    - Дисклеймер при расчёте по ссылке.

- **admin_bot** (`admin_bot/main.py`):
    - Только для админов (по user_id).
    - Меню: "Изменить курсы валют" (правка shared/currency_rates.json), "Посмотреть логи", "Проверить парсер".
    - Все изменения курсов сразу видны user_bot и parser.

- **parser** (`parser/parser_handler.py`, `parser/ProductParser.py`):
    - Получает запросы от user_bot.
    - Парсит сайты через requests.Session, поддерживает proxy, advanced headers, cookies.
    - Для сложных сайтов — поддержка headless-браузера (Selenium/Playwright).
    - Сохраняет результаты в PostgreSQL.

- **PostgreSQL** (`postgres/init.sql`):
    - Хранит историю запросов, результаты парсинга, логи.

- **shared/currency_rates.json**:
    - Общий volume для всех сервисов.
    - Только для USD, EUR, GBP, JPY, CNY.
    - RUB не поддерживается.

---

## 🐳 Docker Compose и переменные окружения

- Все сервисы запускаются через Docker Compose.
- Общий volume для shared/currency_rates.json.
- Proxy для parser задаётся через HTTP_PROXY/HTTPS_PROXY.
- BOT_TOKEN, ADMIN_IDS, DB credentials — через переменные окружения.

---

## 🔄 Сценарии работы

### User Bot
- Пользователь выбирает действие только через кнопки.
- "Рассчитать по ссылке": вводит ссылку, получает расчёт с дисклеймером.
- "Рассчитать вручную": выбирает валюту, вводит сумму, получает расчёт.
- После любого действия — автоответ с предложением нажать /start.

### Admin Bot
- Только для админов (user_id).
- "Изменить курсы валют": редактирует shared/currency_rates.json.
- "Посмотреть логи": выводит последние события.
- "Проверить парсер": тестовый запрос к parser.

### Parser
- Получает запросы от user_bot.
- Парсит сайт с proxy, advanced headers, cookies.
- Для сложных сайтов — headless-браузер.
- Сохраняет результаты в БД.

---
# 🏗️ Архитектура проекта AltBot

## 📊 Общая схема работы

```
┌─────────────────┐
│   Пользователь  │
│   в Telegram    │
└────────┬────────┘
         │
         │ 1. Отправляет ссылку
         ▼
┌─────────────────────┐
│    User Bot         │  ◄── BOT_TOKEN
│  (user_bot/main.py) │      API_URL
└─────────┬───────────┘
          │
          │ 2. HTTP POST /parse
          ▼
┌─────────────────────┐
│      Parser         │  ◄── DB credentials
│ (parser_handler.py) │
│  + ProductParser    │
└─────┬───────┬───────┘
      │       │
      │       │ 3. Сохраняет в БД
      │       ▼
      │  ┌─────────────┐
      │  │  PostgreSQL │
      │  │   (init.sql)│
      │  └─────────────┘
      │
      │ 4. Парсит сайт
      ▼
┌─────────────────┐
│  Внешний сайт   │
│  (ASOS, etc.)   │
└─────────────────┘
      │
      │ 5. Возвращает HTML
      ▼
┌─────────────────────┐
│      Parser         │
│  (ProductParser.py) │
│  - Извлекает имя    │
│  - Извлекает цену   │
└─────────┬───────────┘
          │
          │ 6. Возвращает JSON
          ▼
┌─────────────────────┐
│    User Bot         │
│  - Конвертирует валюту
│  - Добавляет комиссию
└─────────┬───────────┘
          │
          │ 7. Отправляет результат
          ▼
┌─────────────────┐
│   Пользователь  │
│  Получает цену  │
└─────────────────┘

---

## 🏗️ Архитектура проекта AltBot

## 📊 Общая схема работы

```
┌─────────────────┐
│   Пользователь  │
│   в Telegram    │
└───────┬─────────┘
    │
    │ 1. Выбирает действие в меню (только кнопки)
    │    ├─ "Рассчитать по ссылке"
    │    └─ "Рассчитать вручную"
    ▼
┌───────────────────────┐  ◀── BOT_TOKEN
│    User Bot           │      API_URL
│  (user_bot/main.py)   │
└───────┬───────────────┘
    │
    │ 2. (по ссылке) HTTP POST /parse
    ▼
┌───────────────────────┐  ◀── DB credentials
│      Parser           │
│ (parser_handler.py)   │
│  + ProductParser      │
└───────┬───────────────┘
    │
    │ 3. Сохраняет в БД
    ▼
┌───────────────┐
│  PostgreSQL   │
│   (init.sql)  │
└───────┬───────┘
    │
    │ 4. Парсит сайт (requests.Session, proxy, advanced headers)
    ▼
┌───────────────────────┐
│  Внешний сайт         │
│  (ASOS, GOAT, etc.)   │
└───────────────────────┘
    │
    │ 5. Возвращает HTML/JSON
    ▼
┌───────────────────────┐
│      Parser           │
│  (ProductParser.py)   │
│  - Извлекает имя      │
│  - Извлекает цену     │
└───────┬───────────────┘
    │
    │ 6. Возвращает JSON
    ▼
┌───────────────────────┐
│    User Bot           │
│  - Конвертирует валюту (только USD, EUR, GBP, JPY, CNY)
│  - Использует актуальный shared/currency_rates.json
│  - Добавляет комиссию
│  - Показывает дисклеймер для расчёта по ссылке
│  - После любого действия предлагает нажать /start
└───────┬───────────────┘
    │
    │ 7. Отправляет результат
    ▼
┌─────────────────┐
│   Пользователь  │

---

## 🗃️ Shared volume и курсы валют

Вся система использует общий файл `shared/currency_rates.json` (Docker volume), который:
- Редактируется только через admin_bot (меню "Изменить курсы валют").
- Используется для расчётов в user_bot и parser (актуальные курсы всегда синхронизированы).
- RUB не поддерживается (только USD, EUR, GBP, JPY, CNY).

---

## 🛡️ Proxy и антибот в парсере

Парсер поддерживает:
- Proxy через переменные окружения HTTP_PROXY/HTTPS_PROXY (requests.Session).
- Advanced headers (User-Agent, Accept, Accept-Language, Referer и др.).
- Cookies и сессии для обхода антибота (например, goat.com).
- Если сайт требует JS — используйте headless-браузер (Selenium/Playwright).

---

## 🧑‍💻 UX и сценарии

- Только кнопочный интерфейс для пользователя (никаких ручных текстовых команд).
- Пошаговые сценарии: выбор валюты, ввод суммы, подтверждение.
- Дисклеймер для расчёта по ссылке ("цена ориентировочная, не все сайты поддерживаются").
- После любого действия — автоответ с предложением нажать /start.

---
```

---

## 🔄 Поток данных (детальный)

### **Сценарий 1: Пользователь проверяет цену товара**

```
[Пользователь] 
    │
    │ Отправляет: https://shop.com/product/123
    ▼
[User Bot - main.py]
    │
    │ handle_order_link():
    │ ├─ Проверяет что это URL
    │ ├─ Генерирует request_id
    │ └─ Отправляет POST запрос
    ▼
[Parser - parser_handler.py]
    │
    │ /parse endpoint:
    │ ├─ Получает URL
    │ ├─ Создает ProductParser(url)
    │ └─ Вызывает parser.get_product_info()
    ▼
[ProductParser - ProductParser.py]
    │
    │ fetch_page():
    │ ├─ requests.get(url) с fake User-Agent
    │ ├─ BeautifulSoup(html)
    │ └─ Сохраняет в self.soup
    │
    │ parse_product_name():
    │ ├─ Ищет в тегах: h1, h2, h3, title
    │ ├─ Ищет в классах: product-title, name
    │ └─ Возвращает название
    │
    │ parse_product_price():
    │ ├─ Ищет символы валют: $, €, £, ¥
    │ ├─ Извлекает число
    │ └─ Возвращает цену
    ▼
[Parser - parser_handler.py]
    │
    │ Получил: {"name": "Jacket", "price": "$100"}
    │
    │ save_to_db():
    │ ├─ INSERT INTO parsed_data
    │ ├─ VALUES (user_id, JSON, timestamp)
    │ └─ Сохранено!
    │
    │ Возвращает JSON
    ▼
[User Bot - main.py]
    │
    │ Получил: {"name": "Jacket", "price": "$100"}
    │
    │ Конвертация:
    │ ├─ Парсит "$100" → 100
    │ ├─ Комиссия: max(100 * 0.15, 15) = 15
    │ ├─ Итого: 100 + 15 = 115
    │ ├─ Курс: 115 * 82 = 9430 руб.
    │ └─ Форматирует: "≈ 9430 руб."
    │
    │ Отправляет сообщение:
    │ "Название: Jacket
    │  Цена: ≈ 9430 руб.
    │  Для заказа: @manager"
    ▼
[Пользователь]
    Получил результат!
```

---

### **Сценарий 2: Админ делает рассылку**

```
[Админ]
    │
    │ /retranslate
    ▼
[Admin Bot - main.py]
    │
    │ retranslate_start():
    │ ├─ Проверяет ALLOWED_USER_IDS
    │ └─ Запрашивает текст
    │
    │ handle_text():
    │ ├─ Сохраняет текст в context
    │ └─ Запрашивает URL фото
    │
    │ handle_photo_url() или skip_photo():
    │ ├─ Сохраняет photo_url (опционально)
    │ └─ Показывает предпросмотр
    │
    │ confirm_send():
    │ ├─ Подключается к PostgreSQL
    │ ├─ SELECT DISTINCT user_id FROM parsed_data
    │ └─ Получает список всех пользователей
    ▼
[PostgreSQL]
    │
    │ Возвращает: [123, 456, 789, ...]
    ▼
[Admin Bot - confirm_send()]
    │
    │ Для каждого user_id:
    │ ├─ Создает Bot(USER_BOT_TOKEN)
    │ ├─ Отправляет через User Bot:
    │ │   └─ bot.send_message(user_id, text)
    │ │   └─ или bot.send_photo(user_id, photo, caption)
    │ ├─ Считает: success++
    │ └─ При ошибке: failed++
    │
    │ Отчет: "Успешно: 100, Ошибки: 2"
    │
    │ ⚠️ ПЕРЕЗАПУСК:
    │ └─ execl(sys.executable, sys.executable, *sys.argv)
    ▼
[Все пользователи]
    Получили сообщение от User Bot!
```

---

### **Сценарий 3: Админ смотрит статистику**

```
[Админ]
    │
    │ /count
    ▼
[Admin Bot - count_handler()]
    │
    │ Подключается к PostgreSQL:
    │ SELECT user_id, content, created_at
    │ FROM parsed_data
    │ ORDER BY user_id, created_at
    ▼
[PostgreSQL]
    │
    │ Возвращает все записи
    ▼
[Admin Bot]
    │
    │ Группирует по user_id:
    │ ├─ user_123: [заказ1, заказ2, заказ3]
    │ ├─ user_456: [заказ1]
    │ └─ user_789: [заказ1, заказ2]
    │
    │ Парсит JSON в каждой записи:
    │ ├─ content → {"name": "...", "price": "..."}
    │ └─ Извлекает name и price
    │
    │ Форматирует сообщение:
    │ "📊 Статистика:
    │  👤 user_123 – 3 заказа:
    │    • Jacket — $100
    │    • Shoes — €80
    │    • Hat — £50
    │  👤 user_456 – 1 заказ:
    │    • T-shirt — $30"
    ▼
[Админ]
    Получил статистику!
```

---

## 🐳 Docker Compose структура

```
┌─────────────────────────────────────────────────┐
│            Docker Compose                       │
│  (docker-compose.yml)                           │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │  Network: bot_network                   │   │
│  │  (bridge)                               │   │
│  │                                         │   │
│  │  ┌────────────────┐  ┌────────────┐    │   │
│  │  │   PostgreSQL   │  │   Parser   │    │   │
│  │  │  (port 5432)   │◄─┤ (port 8000)│    │   │
│  │  │                │  │            │    │   │
│  │  │  Volume:       │  └─────┬──────┘    │   │
│  │  │  postgres_data │        │           │   │
│  │  └────────────────┘        │           │   │
│  │         ▲                  │           │   │
│  │         │                  ▼           │   │
│  │         │        ┌────────────────┐    │   │
│  │         │        │   User Bot     │    │   │
│  │         │        │                │    │   │
│  │         │        └────────────────┘    │   │
│  │         │                              │   │
│  │         │        ┌────────────────┐    │   │
│  │         └────────┤   Admin Bot    │    │   │
│  │                  │                │    │   │
│  │                  └────────────────┘    │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
         │                      │
         │                      │
         ▼                      ▼
  [Telegram API]        [Внешние сайты]
```

---

## 🔐 Переменные окружения (.env)

```
.env (файл)
├── USER_BOT_TOKEN        → user_bot (main.py: BOT_TOKEN)
│                          → admin_bot (main.py: USER_BOT_TOKEN)
│
├── ADMIN_BOT_TOKEN       → admin_bot (main.py: BOT_TOKEN)
│
└── ALLOWED_USER_IDS      → admin_bot (main.py: ALLOWED_USER_IDS)
```

---

## 💾 Схема базы данных

```sql
┌─────────────────────────────────┐
│       parsed_data               │
├─────────────────────────────────┤
│ id           SERIAL PRIMARY KEY │
│ content      TEXT               │  ← JSON: {"name": "...", "price": "..."}
│ user_id      TEXT               │  ← Telegram ID пользователя
│ created_at   TIMESTAMP          │  ← Время создания
└─────────────────────────────────┘
```

**Пример записи:**
```json
{
  "id": 1,
  "content": "{\"name\": \"Cool Jacket\", \"price\": \"$100\"}",
  "user_id": "873278697",
  "created_at": "2025-10-19 21:30:00"
}
```

---

## 📦 Зависимости между сервисами

```
PostgreSQL (запускается первым)
    │
    │ depends_on (health check)
    ▼
Parser (запускается после PostgreSQL)
    │
    │ depends_on
    ▼
User Bot (запускается после Parser и PostgreSQL)

Admin Bot (запускается после PostgreSQL)
```

**Порядок запуска:**
1. PostgreSQL (ждет health check)
2. Parser (подключается к PostgreSQL)
3. User Bot (подключается к Parser)
4. Admin Bot (подключается к PostgreSQL)

---

## 🌐 Сетевое взаимодействие

```
User Bot → Parser:
├─ Протокол: HTTP
├─ Метод: POST
├─ URL: http://parser:8000/parse
└─ Данные: {"url": "...", "user_id": "...", "request_id": "..."}

Parser → PostgreSQL:
├─ Протокол: PostgreSQL (asyncpg)
├─ Host: postgres
├─ Port: 5432
└─ Query: INSERT INTO parsed_data ...

Admin Bot → PostgreSQL:
├─ Протокол: PostgreSQL (asyncpg)
├─ Host: postgres
├─ Port: 5432
└─ Query: SELECT * FROM parsed_data ...

Admin Bot → Telegram (через User Bot):
├─ Создает экземпляр Bot(USER_BOT_TOKEN)
├─ Отправляет сообщения от имени User Bot
└─ bot.send_message() / bot.send_photo()

Боты → Telegram API:
├─ Протокол: HTTPS
├─ URL: api.telegram.org
└─ Метод: long polling (run_polling())
```

---

## 🔄 Жизненный цикл запроса

```
1. Старт
   └─ docker compose up -d

2. Инициализация
   ├─ PostgreSQL: Выполняет init.sql
   ├─ Parser: Запускает uvicorn (FastAPI)
   ├─ User Bot: Подключается к Telegram
   └─ Admin Bot: Подключается к Telegram

3. Работа
   ├─ Боты: run_polling() - ждут сообщений
   ├─ Parser: app (FastAPI) - ждет HTTP запросов
   └─ PostgreSQL: Принимает подключения

4. Обработка запроса (см. схемы выше)

5. Остановка
   └─ docker compose down
```

---

## 🧪 Тестирование

```
UnitTest.py
    │
    │ pytest
    ▼
ProductParser.py
    │
    │ Тестирует:
    ├─ fetch_page() - загрузка HTML
    ├─ parse_product_name() - извлечение названия
    └─ parse_product_price() - извлечение цены
    │
    │ Mock объекты:
    ├─ requests.get → моковый HTML
    └─ BeautifulSoup → тестовый DOM
```

---

## 📊 Схема файловой структуры

```
AltBot/
├── 🔧 Конфигурация
│   ├── .env                     ← Секреты (токены)
│   ├── docker-compose.yml       ← Оркестрация Docker
│   ├── Makefile                 ← Автоматизация Kubernetes
│   └── Makefile.ci              ← CI/CD
│
├── 📚 Документация
│   ├── readme.md                ← Главная страница
│   ├── DOCS_INDEX.md            ← Навигация по документам
│   ├── PROJECT_STRUCTURE.md     ← Структура проекта (детально)
│   ├── DATABASE_GUIDE.md        ← Работа с БД
│   ├── TESTING_GUIDE.md         ← Тестирование
│   ├── QUICK_START_DOCKER.md    ← Быстрый старт
│   ├── README_DOCKER.md         ← Docker инструкция
│   └── TROUBLESHOOTING.md       ← Решение проблем
│
├── 🤖 User Bot (Пользовательский)
│   ├── main.py                  ← Логика бота
│   ├── Dockerfile               ← Образ
│   ├── requirements.txt         ← Зависимости
│   └── userbot-deployment.yaml  ← Kubernetes
│
├── 👨‍💼 Admin Bot (Админский)
│   ├── main.py                  ← Логика админ-бота
│   ├── Dockerfile               ← Образ
│   ├── requirements.txt         ← Зависимости
│   └── admin-deployment.yaml    ← Kubernetes
│
├── 🔍 Parser (Парсинг товаров)
│   ├── ProductParser.py         ← Класс парсера
│   ├── parser_handler.py        ← FastAPI сервер
│   ├── UnitTest.py              ← Тесты
│   ├── Dockerfile               ← Образ
│   ├── Dockerfile-test          ← Образ для тестов
│   ├── runTestDocker.sh         ← Скрипт тестов
│   ├── requirements.txt         ← Зависимости
│   └── parser.yaml              ← Kubernetes
│
└── 💾 PostgreSQL (База данных)
    ├── init.sql                 ← Инициализация БД
    ├── Dockerfile               ← Образ
    ├── postgres-pv.yaml         ← Kubernetes PV
    └── postgres-sts.yaml        ← Kubernetes StatefulSet
```

---

✅ **Теперь вы понимаете архитектуру всего проекта!**
