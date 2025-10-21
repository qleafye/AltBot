import os
import json
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler
from telegram.error import InvalidToken
import re
import sys

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN is not set in the environment variables")
    exit(1)

if not API_URL:
    logger.warning("API_URL is not set. API requests will be skipped.")

logger.info(f"Bot token set: {BOT_TOKEN[:4]}...{BOT_TOKEN[-4:]}")

current_request_id = 0

ORDER_STATE = 1  # State for ordering flow

def get_next_request_id():
    global current_request_id
    current_request_id += 1
    return current_request_id

def check_bot_token(token: str):
    try:
        bot = requests.get(f"https://api.telegram.org/bot{token}/getMe")
        if bot.status_code == 200:
            result = bot.json()
            if not result["ok"]:
                raise InvalidToken("Invalid token provided by Telegram API.")
            logger.info(f"Bot connected successfully: {result['result']['username']}")
        else:
            raise InvalidToken(f"Failed to verify token, status code: {bot.status_code}")
    except Exception as e:
        logger.error(f"Error validating bot token: {e}")
        exit(1)

check_bot_token(BOT_TOKEN)

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("🛍 Рассчитать цену по ссылке"), KeyboardButton("💱 Рассчитать цену вручную")],
            [KeyboardButton("📢 Канал"), KeyboardButton("💬 Отзывы")],
            [KeyboardButton("👤 Поддержка"), KeyboardButton("🛡 Проверенные сайты")]
        ],
        resize_keyboard=True
    )

# Состояния для ручного расчета
SELECT_CURRENCY, ENTER_AMOUNT = range(10, 12)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=get_main_menu()
    )


# Проверка, является ли текст ссылкой
def is_url(text: str) -> bool:
    return text.startswith("https://")

# Проверка, является ли текст ценой (например, $100, 100 USD, 12000 руб.)
def is_price(text: str) -> bool:
    # Примеры: $100, 100 USD, 12000 руб., 1000, 1000 RUB
    price_pattern = re.compile(r"(\$|€|£|USD|EUR|GBP|CNY|元|руб|RUB)?\s*([\d.,]+)\s*(\$|€|£|USD|EUR|GBP|CNY|元|руб|RUB)?", re.IGNORECASE)
    return bool(price_pattern.fullmatch(text.strip()))


def calculate_price(text: str) -> str:
    """Рассчитать цену в рублях из строки с ценой и валютой, добавить эмодзи валюты."""
    # Ищем валюту и сумму (например: $100, 100 USD, €50, 12000 RUB)
    m = re.search(r"(\$|€|¥|£|USD|EUR|GBP|JPY|CNY|元|руб|RUB)?\s*([\d.,]+)\s*(\$|€|¥|£|USD|EUR|GBP|JPY|CNY|元|руб|RUB)?", text.strip(), re.IGNORECASE)
    if not m:
        return "Не удалось распознать цену. Попробуйте, например: $100, 100 USD или 1000."
    cur1, amount_str, cur2 = m.group(1), m.group(2), m.group(3)
    currency = (cur1 or cur2 or "USD").upper()
    # Нормализуем русские обозначения рубля
    if currency in {"РУБ", "RUB"}:
        currency = "RUB"
    amount = None
    try:
        amount = float(amount_str.replace(",", "."))
    except ValueError:
        return "Не удалось распознать сумму. Введите число, например: 99.99"

    rates = load_currency_rates()
    # Поддерживаем как коды, так и символы валют
    rate = rates.get(currency)
    if rate is None:
        # Попробуем символы валют
        symbol_map = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CNY": "元", "RUB": None}
        sym = symbol_map.get(currency)
        if sym:
            rate = rates.get(sym)
    if rate is None:
        # По умолчанию считаем как USD
        rate = rates.get("USD", 1)
        currency = "USD"

    commission = max(amount * 0.15, 15)
    rub_price = round((amount + commission) * rate)

    emoji_map = {"USD": "💵", "EUR": "💶", "GBP": "💷", "JPY": "💴", "CNY": "🧧", "$": "💵", "€": "💶", "£": "💷", "¥": "💴", "元": "🧧", "RUB": ""}
    emoji = emoji_map.get(currency, "")
    return (
        f"Цена ≈ {rub_price} ₽\n"
        f"(введено: {amount} {currency} {emoji})\n"
        f"Стоимость доставки рассчитывается отдельно."
    )


CURR_PATH = "/app/shared/currency_rates.json"
DEFAULT_RATES = {
    "$": 82, "USD": 82,
    "€": 90, "EUR": 90,
    "£": 115, "GBP": 115,
    "CNY": 12.5, "元": 12.5
}

def load_currency_rates():
    # Сопоставление синонимов валют
    synonyms = {
        "$": "USD",
        "€": "EUR",
        "£": "GBP",
    # "¥": "JPY",  # JPY удалена из поддерживаемых валют
        "元": "CNY"
    }
    try:
        with open(CURR_PATH, "r", encoding="utf-8") as f:
            rates = json.load(f)
        rates_full = rates.copy()
        # Применяем синонимы: если есть основной курс, синониму присваиваем то же значение
        for syn, main in synonyms.items():
            if main in rates:
                rates_full[syn] = rates[main]
        return rates_full
    except Exception:
        # Если файл не найден — возвращаем дефолтные значения
        rates_full = DEFAULT_RATES.copy()
        for syn, main in synonyms.items():
            if main in DEFAULT_RATES:
                rates_full[syn] = DEFAULT_RATES[main]
        return rates_full



async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    logger.info(f"Received message from {update.message.from_user.id}: {text}")

    # Если пользователь только начал диалог не с /start, подскажем ему
    if update.message.text and update.message.text != "/start" and update.message.chat.type == "private" and not update.message.text.startswith("/") and context.user_data.get("_welcomed") is None:
        await update.message.reply_text("Для начала работы нажмите /start")
        context.user_data["_welcomed"] = True
        return ConversationHandler.END

    if text == "🛍 Рассчитать цену по ссылке":
        await update.message.reply_text(
            "Отправьте ссылку на товар.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 В меню")]], resize_keyboard=True)
        )
        return ORDER_STATE

    elif text == "💱 Рассчитать цену вручную":
        # Переход к выбору валюты
        currency_buttons = [
            [KeyboardButton("USD 💵"), KeyboardButton("EUR 💶"), KeyboardButton("GBP 💷")],
            [KeyboardButton("CNY 🧧")],
            [KeyboardButton("🔙 В меню")]
        ]
        await update.message.reply_text(
            "Выберите валюту:",
            reply_markup=ReplyKeyboardMarkup(currency_buttons, resize_keyboard=True)
        )
        return SELECT_CURRENCY



    elif text == "🛡 Проверенные сайты":
        await update.message.reply_text("Список сайтов: https://telegra.ph/Spisok-osnovnyh-sajtov-dlya-vykupa-v-SYTNXX-STORE-08-22")

    elif text == "👤 Поддержка":
        await update.message.reply_text("Связаться с поддержкой: https://t.me/sytnixxstore")

    elif text == "📢 Канал":
        await update.message.reply_text("Наш канал: https://t.me/sytnxxstore")

    elif text == "💬 Отзывы":
        await update.message.reply_text("Отзывы: https://t.me/sytnxxcomment")

    else:
        await update.message.reply_text("Пожалуйста, выберите действие из меню.")

    return ConversationHandler.END

# Обработка выбора валюты
async def handle_select_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    if text == "🔙 В МЕНЮ":
        await update.message.reply_text("Вы вернулись в главное меню.", reply_markup=get_main_menu())
        return ConversationHandler.END
    # Убираем эмодзи из текста и принимаем только валюные коды
    clean = (
        text.replace("💵", "")
            .replace("💶", "")
            .replace("💷", "")
            .replace("💴", "")
            .replace("🧧", "")
            .strip()
    )
    allowed = {"USD", "EUR", "GBP", "CNY"}
    if clean not in allowed:
        await update.message.reply_text("Пожалуйста, выберите валюту из списка.")
        return SELECT_CURRENCY
    context.user_data['manual_currency'] = clean
    emoji_map = {"USD":"💵","EUR":"💶","GBP":"💷","CNY":"🧧"}
    await update.message.reply_text(
        f"Введите сумму в {clean} {emoji_map.get(clean,'')}",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 В меню")]], resize_keyboard=True)
    )
    return ENTER_AMOUNT

# Обработка ввода суммы
async def handle_enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "🔙 В меню":
        await update.message.reply_text("Вы вернулись в главное меню.", reply_markup=get_main_menu())
        return ConversationHandler.END
    currency = context.user_data.get('manual_currency', 'USD')
    try:
        amount = float(text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректную сумму.")
        return ENTER_AMOUNT
    CURRENCY_RATES = load_currency_rates()
    rate = CURRENCY_RATES.get(currency, 1)
    commission = max(amount * 0.15, 15)
    total = amount + commission
    rub_price = round(total * rate)
    emoji_map = {"USD":"💵","EUR":"💶","GBP":"💷","CNY":"🧧"}
    await update.message.reply_text(
        f"Цена ≈ {rub_price} ₽\n(введено: {amount} {currency} {emoji_map.get(currency,'')})\n"
        f"Стоимость доставки рассчитывается отдельно."
    )
    await update.message.reply_text(
        "Для оформления заказа и уточнения деталей перешлите сообщение менеджеру https://t.me/sytnixxstore"
    )
    await update.message.reply_text("Вы вернулись в главное меню.", reply_markup=get_main_menu())
    return ConversationHandler.END

async def handle_order_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "🔙 В меню":
        await update.message.reply_text("Вы вернулись в главное меню.", reply_markup=get_main_menu())
        return ConversationHandler.END


    # Если это ссылка — работаем как раньше
    if is_url(text):
        await update.message.reply_text(
            "⚠️ Внимание! Не все сайты поддерживаются для автоматического расчёта цены.\n"
            "Например, сайт dw4.co(Poizon) может работать некорректно. Если возникнут проблемы — воспользуйтесь ручным вводом или обратитесь к менеджеру."
        )
        if not API_URL:
            return ConversationHandler.END
        user = update.message.from_user
        request_data = {
            "url": text,
            "request_id": str(get_next_request_id()),
            "user_id": user.username or "Неизвестно",
            "id": user.id
        }
        logger.info(f"Sending request to {API_URL} with data: {request_data}")
        try:
            response = requests.post(API_URL, json=request_data)
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response content: {response.text}")
            if response.status_code != 200:
                await update.message.reply_text(f"Ошибка. Попробуйте позже")
                return ORDER_STATE
            data = response.json()
            product_info = data.get("product_info", {})
            name = product_info.get("name", "Неизвестно")
            price = product_info.get("price", "Неизвестно")
            # Конвертация валют с учетом комиссии (теперь используем актуальные курсы)
            CURRENCY_RATES = load_currency_rates()
            if isinstance(price, str):
                match = re.search(r"(€|\$|£|USD|EUR|GBP|CNY|元)\s*([\d.,]+)", price.upper())
                if match:
                    currency = match.group(1)
                    amount_str = match.group(2).replace(",", ".")
                    try:
                        amount = float(amount_str)
                        commission = max(amount * 0.15, 15)
                        total = amount + commission
                        rate = CURRENCY_RATES.get(currency)
                        if rate:
                            rub_price = round(total * rate)
                            price = f"≈ {rub_price} ₽"
                    except ValueError:
                        logger.warning(f"Не удалось разобрать цену: {price}")
            # Покажем эмодзи валюты, если распознали
            if isinstance(price, str):
                m = re.search(r"(€|\$|£|USD|EUR|GBP|CNY|元)", price.upper())
                cur = m.group(1) if m else ""
                emoji_map = {"USD":"💵","EUR":"💶","GBP":"💷","CNY":"🧧","$":"💵","€":"💶","£":"💷","元":"🧧"}
                emoji = emoji_map.get(cur, "")
                price = f"{price} {emoji}".strip()
            await update.message.reply_text(
                f"Название: {name}\n"
                f"Ссылка: {text}\n"
                f"Цена: {price}\n"
                f"Стоимость доставки рассчитывается отдельно.\n"
                f"Для оформления заказа и уточнения деталей перешлите сообщение менеджеру https://t.me/sytnixxstore"
            )
            await update.message.reply_text("Вы вернулись в главное меню.", reply_markup=get_main_menu())
            return ConversationHandler.END
        except requests.RequestException as e:
            logger.error(f"Ошибка при запросе к API: {e}")
            return ORDER_STATE

    # Если это цена — считаем и показываем результат
    if is_price(text):
        result = calculate_price(text)
        await update.message.reply_text(result)
        await update.message.reply_text("Вы вернулись в главное меню.", reply_markup=get_main_menu())
        return ConversationHandler.END

    # Если не ссылка и не цена
    await update.message.reply_text("Пожалуйста, отправьте ссылку на товар или цену (например, $100, 100 USD, 12000 руб.), либо нажмите 🔙 В меню.")
    return ORDER_STATE

if __name__ == '__main__':
    print(f"[DEBUG] Running user_bot from: {sys.argv[0]}")
    application = Application.builder().token(BOT_TOKEN).build()

    # Объединённый ConversationHandler для всех сценариев
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)],
        states={
            ORDER_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_order_link)],
            SELECT_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_select_currency)],
            ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_enter_amount)]
        },
        fallbacks=[],
    )
    application.add_handler(conv_handler)
    application.run_polling()
