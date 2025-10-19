# 🧪 Руководство по тестированию парсера

## 📝 Зачем нужны тесты?

Тесты в `parser/UnitTest.py` проверяют, что парсер **правильно работает** после изменений кода.

**Что они проверяют:**
- ✅ Правильно ли извлекаются названия товаров
- ✅ Правильно ли извлекаются цены
- ✅ Обработка разных валют ($, €, £, ¥)
- ✅ Обработка цен с разделителями (1,234.56)
- ✅ Обработка ошибок сети
- ✅ Обработка невалидных данных

---

## 🚀 Как запустить тесты

### **Способ 1: Через Docker (Рекомендую)**

```powershell
# Запустить все тесты
docker compose exec parser pytest UnitTest.py -v

# Запустить конкретный тест
docker compose exec parser pytest UnitTest.py::test_parse_product_name_not_found -v

# Запустить с подробным выводом
docker compose exec parser pytest UnitTest.py -vv

# Запустить с показом print() в тестах
docker compose exec parser pytest UnitTest.py -v -s
```

### **Способ 2: Локально**

```powershell
cd parser

# Установить pytest (если еще не установлен)
pip install pytest pytest-mock

# Запустить тесты
pytest UnitTest.py -v
```

### **Способ 3: Через специальный Docker образ для тестов**

```powershell
# Собрать тестовый образ
docker build -f parser/Dockerfile-test -t parser-test ./parser

# Запустить тесты
docker run parser-test
```

---

## 📊 Результаты тестов

### **Успешный запуск:**
```
test_parse_product_name_not_found PASSED                [ 10%]
test_parse_product_price_different_currency PASSED      [ 20%]
test_parse_product_price_with_whitespace PASSED         [ 30%]
...
========================== 20 passed in 2.34s ==========================
```

### **Провальный тест:**
```
FAILED test_parse_product_price_with_comma_separator - AssertionError: assert 'Price not found' == '£1,234.56'
```

Это означает, что парсер не смог правильно обработать цену с запятой.

---

## 🔍 Анализ тестов

### **Пример теста:**

```python
def test_parse_product_price_with_comma_separator():
    # Создаем парсер
    parser = ProductParser("http://example.com")
    
    # Подсовываем HTML с ценой
    parser.soup = BeautifulSoup('<html><span>£1,234.56</span></html>', 'html.parser')
    
    # Вызываем парсинг цены
    parser.parse_product_price()
    
    # Проверяем результат
    assert parser.product_price == "£1,234.56"
```

**Что происходит:**
1. Создается экземпляр `ProductParser`
2. Вручную создается HTML с ценой
3. Вызывается метод `parse_product_price()`
4. Проверяется, что результат правильный

---

## ✏️ Как добавить свой тест

### **Шаг 1: Найдите новый сайт**

Допустим, парсер не работает с сайтом `https://newshop.com`

### **Шаг 2: Скачайте HTML фрагмент**

```powershell
# Посмотрите HTML страницы
curl https://newshop.com/product/123 > product.html
```

Найдите в HTML название товара и цену:
```html
<div class="product-title">Cool Jacket</div>
<span class="price">€199.99</span>
```

### **Шаг 3: Добавьте тест в UnitTest.py**

```python
def test_parse_newshop_product():
    """Тест для newshop.com"""
    parser = ProductParser("http://newshop.com")
    
    # HTML фрагмент с сайта
    parser.soup = BeautifulSoup('''
        <html>
            <div class="product-title">Cool Jacket</div>
            <span class="price">€199.99</span>
        </html>
    ''', 'html.parser')
    
    # Парсим
    parser.parse_product_name()
    parser.parse_product_price()
    
    # Проверяем
    assert parser.product_name == "Cool Jacket"
    assert parser.product_price == "€199.99"
```

### **Шаг 4: Запустите тест**

```powershell
docker compose exec parser pytest UnitTest.py::test_parse_newshop_product -v
```

### **Шаг 5: Если тест провалился**

**Тест показал:**
```
AssertionError: assert 'Name not found' == 'Cool Jacket'
```

**Значит нужно доработать парсер!**

Откройте `ProductParser.py` и добавьте:

```python
def parse_product_name(self):
    if self.soup:
        # Специально для newshop.com
        if 'newshop.com' in self.url:
            product_name_tag = self.soup.find('div', class_='product-title')
            if product_name_tag:
                self.product_name = product_name_tag.get_text(strip=True)
                return
        
        # Общая логика для остальных
        search_tags = ['h1', 'h2', 'h3', 'title', 'div', 'span']
        # ... остальной код
```

### **Шаг 6: Запустите тест снова**

```powershell
docker compose exec parser pytest UnitTest.py::test_parse_newshop_product -v
```

Теперь должно быть `PASSED` ✅

---

## 🎯 Типичные тест-кейсы

### **Тест 1: Проверка обработки ошибок сети**

```python
def test_fetch_page_timeout(mocker):
    """Тест таймаута при загрузке страницы"""
    mocker.patch('requests.get', side_effect=requests.exceptions.Timeout)
    
    parser = ProductParser("http://example.com")
    parser.fetch_page()
    
    assert parser.soup is None  # Страница не загрузилась
```

### **Тест 2: Проверка разных валют**

```python
def test_parse_different_currencies():
    """Тест парсинга разных валют"""
    currencies = ['$99.99', '€89.99', '£79.99', '¥9999']
    
    for currency_price in currencies:
        parser = ProductParser("http://example.com")
        parser.soup = BeautifulSoup(f'<html><span>{currency_price}</span></html>', 'html.parser')
        parser.parse_product_price()
        
        assert parser.product_price == currency_price
```

### **Тест 3: Проверка цен с текстом**

```python
def test_parse_price_with_text():
    """Тест парсинга цены с дополнительным текстом"""
    parser = ProductParser("http://example.com")
    parser.soup = BeautifulSoup('<html><span>Price: $123.45 USD</span></html>', 'html.parser')
    parser.parse_product_price()
    
    assert parser.product_price == "$123.45"
```

---

## 📈 Покрытие тестами

### **Проверить покрытие:**

```powershell
# Установить pytest-cov
docker compose exec parser pip install pytest-cov

# Запустить с проверкой покрытия
docker compose exec parser pytest UnitTest.py --cov=ProductParser --cov-report=html

# Откроется отчет с процентом покрытия кода тестами
```

**Хорошее покрытие:** > 80%

---

## 🔥 Продвинутые примеры

### **Тест с реальным HTTP запросом:**

```python
@pytest.mark.slow  # Помечаем как медленный тест
def test_real_website():
    """Тест с реальным сайтом (медленный!)"""
    parser = ProductParser("https://example.com/product/123")
    product_info = parser.get_product_info()
    
    assert product_info['name'] != "Name not found"
    assert product_info['price'] != "Price not found"
```

Запустить только быстрые тесты (без `@pytest.mark.slow`):
```powershell
docker compose exec parser pytest UnitTest.py -v -m "not slow"
```

### **Тест с параметризацией:**

```python
@pytest.mark.parametrize("html,expected_price", [
    ('<span>$99.99</span>', '$99.99'),
    ('<span>€89.99</span>', '€89.99'),
    ('<span>£79.99</span>', '£79.99'),
    ('<span>Price not available</span>', 'Price not found'),
])
def test_parse_multiple_prices(html, expected_price):
    """Тест парсинга множества вариантов цен"""
    parser = ProductParser("http://example.com")
    parser.soup = BeautifulSoup(f'<html>{html}</html>', 'html.parser')
    parser.parse_product_price()
    
    assert parser.product_price == expected_price
```

---

## 🛠️ Отладка провалившихся тестов

### **Способ 1: Добавить print()**

```python
def test_my_test():
    parser = ProductParser("http://example.com")
    parser.soup = BeautifulSoup('<html><span>$99.99</span></html>', 'html.parser')
    parser.parse_product_price()
    
    print(f"Parsed price: {parser.product_price}")  # Для отладки
    
    assert parser.product_price == "$99.99"
```

Запустить с выводом print():
```powershell
docker compose exec parser pytest UnitTest.py::test_my_test -v -s
```

### **Способ 2: Использовать pytest debugger**

```python
def test_my_test():
    parser = ProductParser("http://example.com")
    parser.soup = BeautifulSoup('<html><span>$99.99</span></html>', 'html.parser')
    parser.parse_product_price()
    
    import pdb; pdb.set_trace()  # Точка останова
    
    assert parser.product_price == "$99.99"
```

### **Способ 3: Запустить с подробным выводом**

```powershell
docker compose exec parser pytest UnitTest.py::test_my_test -vv
```

---

## 📋 CI/CD интеграция

Тесты автоматически запускаются при каждом коммите (если настроен CI/CD).

### **GitHub Actions пример:**

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build test image
        run: docker build -f parser/Dockerfile-test -t parser-test ./parser
      - name: Run tests
        run: docker run parser-test
```

---

## 🎯 Быстрая шпаргалка

```powershell
# Запустить все тесты
docker compose exec parser pytest UnitTest.py -v

# Запустить конкретный тест
docker compose exec parser pytest UnitTest.py::test_parse_product_price_with_comma_separator -v

# Запустить с выводом print()
docker compose exec parser pytest UnitTest.py -v -s

# Запустить только провалившиеся тесты
docker compose exec parser pytest UnitTest.py --lf

# Остановиться на первой ошибке
docker compose exec parser pytest UnitTest.py -x

# Показать самые медленные тесты
docker compose exec parser pytest UnitTest.py --durations=10
```

---

## ✅ Когда запускать тесты

**Обязательно запускайте тесты:**
- ✅ После изменения `ProductParser.py`
- ✅ Перед коммитом в Git
- ✅ После добавления поддержки нового сайта
- ✅ Перед деплоем в продакшен

**Команда перед деплоем:**
```powershell
# Запустить тесты
docker compose exec parser pytest UnitTest.py -v

# Если все PASSED - можно деплоить
docker compose restart parser
```

---

✅ **Теперь вы знаете всё о тестировании парсера!**
