# 🐳 Запуск бота через Docker Compose

## Быстрый старт

### 1. Установите Docker Desktop
Скачайте с [docker.com](https://www.docker.com/products/docker-desktop/)

### 2. Создайте файл с токенами
Скопируйте `.env.example` в `.env` и заполните токены:

```bash
copy .env.example .env
```

Откройте `.env` и вставьте свои токены:
```env
USER_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_BOT_TOKEN=987654321:XYZabcDEFghiJKLmnoPQRstuv
ALLOWED_USER_IDS=123456789,987654321
```

### 3. Запустите всю систему одной командой

```bash
docker-compose up -d
```

**Готово!** Все 4 сервиса запущены 🚀

## Полезные команды

```bash
# Посмотреть логи всех сервисов
docker-compose logs -f

# Посмотреть логи конкретного сервиса
docker-compose logs -f user_bot
docker-compose logs -f admin_bot
docker-compose logs -f parser
docker-compose logs -f postgres

# Остановить все сервисы
docker-compose down

# Остановить и удалить все данные
docker-compose down -v

# Перезапустить конкретный сервис
docker-compose restart user_bot

# Пересобрать и запустить
docker-compose up -d --build

# Посмотреть статус
docker-compose ps
```

## Проверка работы

```bash
# Проверить, что все контейнеры работают
docker-compose ps

# Должно быть 4 контейнера в статусе "Up"
```

## Доступ к сервисам

- **Parser API**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Боты**: работают через Telegram API

## Обновление кода

После изменения кода:

```bash
docker-compose up -d --build
```

## Troubleshooting

### Бот не отвечает
```bash
docker-compose logs user_bot
```

### Ошибки парсера
```bash
docker-compose logs parser
```

### Проблемы с БД
```bash
docker-compose logs postgres
docker-compose exec postgres psql -U admin -d parserdb -c "SELECT * FROM parsed_data LIMIT 5;"
```

### Очистить всё и начать заново
```bash
docker-compose down -v
docker-compose up -d --build
```
