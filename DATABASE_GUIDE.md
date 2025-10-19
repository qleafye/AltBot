# 🏦 Структура данных и курсы валют

## Основные сущности

- **products** — результаты парсинга (название, цена, валюта, ссылка, дата)
- **requests** — история запросов пользователей
- **logs** — логи событий
- **currency_rates** — (устарело, теперь только файл shared/currency_rates.json)

---

## Курсы валют (shared/currency_rates.json)

- Все сервисы используют общий файл `shared/currency_rates.json` (Docker volume)
- Курсы редактируются только через admin_bot (меню "Изменить курсы валют")
- RUB не поддерживается (только USD, EUR, GBP, JPY, CNY)
- Изменения курсов доступны сразу всем сервисам (user_bot, parser)

### Пример currency_rates.json
```json
{
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 149.5,
    "CNY": 7.3
}
```

---

## Важные моменты

- История запросов и результаты парсинга хранятся в БД
- Все сервисы используют один и тот же файл курсов валют
- RUB не поддерживается

---
# 🗄️ Работа с базой данных PostgreSQL

## 📊 Подключение к базе данных

### **Метод 1: Через Docker (Быстрый способ)**

```powershell
# Войти в контейнер PostgreSQL
docker compose exec postgres psql -U admin -d parserdb
```

Вы окажетесь в интерактивной консоли `psql`.

---

## 📋 Полезные SQL команды

### **Основные команды psql**

```sql
-- Показать все таблицы
\dt

-- Описание таблицы
\d parsed_data

-- Список всех баз данных
\l

-- Выход из psql
\q

-- Помощь
\?
```

### **Просмотр данных**

```sql
-- Показать все записи (ОСТОРОЖНО: может быть много!)
SELECT * FROM parsed_data;

-- Показать последние 10 записей
SELECT * FROM parsed_data ORDER BY created_at DESC LIMIT 10;

-- Показать только определенные поля
SELECT user_id, created_at FROM parsed_data LIMIT 10;

-- Подсчитать количество записей
SELECT COUNT(*) FROM parsed_data;

-- Показать записи конкретного пользователя
SELECT * FROM parsed_data WHERE user_id = '873278697';

-- Статистика по пользователям
SELECT user_id, COUNT(*) as order_count 
FROM parsed_data 
GROUP BY user_id 
ORDER BY order_count DESC;

-- Записи за последние 7 дней
SELECT * FROM parsed_data 
WHERE created_at >= NOW() - INTERVAL '7 days';

-- Записи за сегодня
SELECT * FROM parsed_data 
WHERE DATE(created_at) = CURRENT_DATE;
```

### **Анализ данных**

```sql
-- Самые активные пользователи
SELECT user_id, COUNT(*) as orders 
FROM parsed_data 
GROUP BY user_id 
ORDER BY orders DESC 
LIMIT 10;

-- Количество заказов по дням
SELECT DATE(created_at) as date, COUNT(*) as orders 
FROM parsed_data 
GROUP BY DATE(created_at) 
ORDER BY date DESC;

-- Просмотр JSON данных (красиво)
SELECT user_id, 
       content::json->>'name' as product_name,
       content::json->>'price' as price,
       created_at 
FROM parsed_data 
LIMIT 10;

-- Поиск по названию товара в JSON
SELECT user_id, content, created_at 
FROM parsed_data 
WHERE content::json->>'name' ILIKE '%jacket%';
```

### **Изменение данных**

```sql
-- Удалить конкретную запись
DELETE FROM parsed_data WHERE id = 123;

-- Удалить все записи конкретного пользователя
DELETE FROM parsed_data WHERE user_id = '123456789';

-- Удалить старые записи (старше 30 дней)
DELETE FROM parsed_data 
WHERE created_at < NOW() - INTERVAL '30 days';

-- Удалить ВСЕ записи (ОСТОРОЖНО!)
TRUNCATE TABLE parsed_data;

-- Обновить данные
UPDATE parsed_data 
SET content = '{"name": "New Product", "price": "$100"}' 
WHERE id = 1;
```

---

## 🖥️ Графические инструменты

### **Вариант 1: pgAdmin (Профессиональный)**

1. **Скачайте:** https://www.pgadmin.org/download/
2. **Установите и откройте**
3. **Создайте новое подключение:**
   - Правый клик на "Servers" → Register → Server
   - **General:**
     - Name: `AltBot Local`
   - **Connection:**
     - Host: `localhost`
     - Port: `5432`
     - Database: `parserdb`
     - Username: `admin`
     - Password: `test123`
   - Нажмите "Save"

4. **Работа с данными:**
   - Откройте: Servers → AltBot Local → Databases → parserdb → Schemas → public → Tables
   - Правый клик на `parsed_data` → View/Edit Data → All Rows

### **Вариант 2: DBeaver (Рекомендую!)**

1. **Скачайте:** https://dbeaver.io/download/
2. **Установите и откройте**
3. **Создайте подключение:**
   - Нажмите "Новое подключение"
   - Выберите "PostgreSQL"
   - **Connection Settings:**
     - Host: `localhost`
     - Port: `5432`
     - Database: `parserdb`
     - Username: `admin`
     - Password: `test123`
   - Нажмите "Test Connection"
   - Если OK, нажмите "Finish"

4. **Работа с данными:**
   - Двойной клик на `parsed_data`
   - Вкладка "Data" для просмотра
   - Кнопка SQL для выполнения запросов

### **Вариант 3: VS Code расширение**

1. **Установите расширение:** "PostgreSQL" (автор: Chris Kolkman)
2. **Подключитесь:**
   - Откройте Command Palette (Ctrl+Shift+P)
   - Выберите "PostgreSQL: New Query"
   - Введите данные подключения
3. **Выполняйте SQL** прямо в VS Code

---

## 📈 Примеры полезных отчетов

### **Отчет 1: Активность пользователей**

```sql
SELECT 
    user_id,
    COUNT(*) as total_orders,
    MIN(created_at) as first_order,
    MAX(created_at) as last_order,
    DATE_PART('day', MAX(created_at) - MIN(created_at)) as days_active
FROM parsed_data
GROUP BY user_id
ORDER BY total_orders DESC;
```

### **Отчет 2: Популярные товары**

```sql
SELECT 
    content::json->>'name' as product_name,
    COUNT(*) as times_requested
FROM parsed_data
GROUP BY content::json->>'name'
ORDER BY times_requested DESC
LIMIT 20;
```

### **Отчет 3: Активность по дням недели**

```sql
SELECT 
    TO_CHAR(created_at, 'Day') as day_of_week,
    COUNT(*) as orders
FROM parsed_data
GROUP BY TO_CHAR(created_at, 'Day')
ORDER BY 
    CASE TO_CHAR(created_at, 'Day')
        WHEN 'Monday   ' THEN 1
        WHEN 'Tuesday  ' THEN 2
        WHEN 'Wednesday' THEN 3
        WHEN 'Thursday ' THEN 4
        WHEN 'Friday   ' THEN 5
        WHEN 'Saturday ' THEN 6
        WHEN 'Sunday   ' THEN 7
    END;
```

### **Отчет 4: Средняя цена товаров (если в USD)**

```sql
SELECT 
    AVG(CAST(REGEXP_REPLACE(content::json->>'price', '[^0-9.]', '', 'g') AS NUMERIC)) as avg_price
FROM parsed_data
WHERE content::json->>'price' LIKE '$%';
```

---

## 🔄 Бэкап и восстановление

### **Создать бэкап**

```powershell
# Полный бэкап всей базы
docker compose exec postgres pg_dump -U admin parserdb > backup_$(Get-Date -Format "yyyy-MM-dd").sql

# Только данные (без структуры)
docker compose exec postgres pg_dump -U admin --data-only parserdb > data_backup.sql

# Только структура (без данных)
docker compose exec postgres pg_dump -U admin --schema-only parserdb > schema_backup.sql

# Только одна таблица
docker compose exec postgres pg_dump -U admin -t parsed_data parserdb > parsed_data_backup.sql
```

### **Восстановить из бэкапа**

```powershell
# Восстановить базу
Get-Content backup_2025-10-19.sql | docker compose exec -T postgres psql -U admin -d parserdb

# Или через Unix pipe (если работает)
cat backup.sql | docker compose exec -T postgres psql -U admin -d parserdb
```

---

## 🧹 Очистка и обслуживание

```sql
-- Удалить дубликаты (если есть)
DELETE FROM parsed_data a USING (
    SELECT MIN(id) as id, user_id, content
    FROM parsed_data 
    GROUP BY user_id, content 
    HAVING COUNT(*) > 1
) b
WHERE a.user_id = b.user_id 
AND a.content = b.content 
AND a.id <> b.id;

-- Оптимизация таблицы
VACUUM ANALYZE parsed_data;

-- Размер таблицы
SELECT pg_size_pretty(pg_total_relation_size('parsed_data'));

-- Количество записей и размер
SELECT 
    COUNT(*) as records,
    pg_size_pretty(pg_total_relation_size('parsed_data')) as size
FROM parsed_data;
```

---

## 📊 Экспорт данных

### **Экспорт в CSV**

```powershell
# Из командной строки Docker
docker compose exec postgres psql -U admin -d parserdb -c "COPY parsed_data TO STDOUT WITH CSV HEADER" > export.csv

# Или внутри psql
\copy parsed_data TO 'export.csv' WITH CSV HEADER

# Только определенные поля
\copy (SELECT user_id, content::json->>'name' as product, created_at FROM parsed_data) TO 'export.csv' WITH CSV HEADER
```

### **Экспорт в JSON**

```powershell
# Экспорт всех данных в JSON
docker compose exec postgres psql -U admin -d parserdb -t -c "SELECT json_agg(t) FROM (SELECT * FROM parsed_data) t" > export.json
```

---

## 🔍 Мониторинг

```sql
-- Активные подключения
SELECT * FROM pg_stat_activity WHERE datname = 'parserdb';

-- Размер базы данных
SELECT pg_size_pretty(pg_database_size('parserdb'));

-- Самые медленные запросы (если включено логирование)
SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;

-- Статистика по таблицам
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    n_live_tup AS rows
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 🚨 Частые проблемы

### **Проблема: "relation does not exist"**
```sql
-- Проверьте что таблица существует
\dt

-- Если нет, пересоздайте базу:
-- (в PowerShell)
docker compose down -v
docker compose up -d
```

### **Проблема: "password authentication failed"**
```powershell
# Проверьте что используете правильные данные:
# Username: admin
# Password: test123
```

### **Проблема: "connection refused"**
```powershell
# Проверьте что PostgreSQL запущен:
docker compose ps

# Если нет, запустите:
docker compose up -d postgres
```

---

## 🎯 Быстрая шпаргалка

```powershell
# Подключиться
docker compose exec postgres psql -U admin -d parserdb

# Внутри psql:
\dt                                    # Список таблиц
SELECT * FROM parsed_data LIMIT 10;    # Показать 10 записей
SELECT COUNT(*) FROM parsed_data;      # Количество записей
\q                                     # Выход

# Бэкап
docker compose exec postgres pg_dump -U admin parserdb > backup.sql

# Очистить всё
docker compose exec postgres psql -U admin -d parserdb -c "TRUNCATE TABLE parsed_data;"
```

---

✅ **Теперь вы можете работать с базой данных как профи!**
