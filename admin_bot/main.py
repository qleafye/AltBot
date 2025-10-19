from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, Bot, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    ConversationHandler,
    CallbackQueryHandler
)
import logging
import os
import sys
from os import execl
import asyncio
import asyncpg
from typing import Dict, Any
import json
from collections import defaultdict
from datetime import datetime
import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация БД
DB_CONFIG = {
    "user": "admin",
    "password": "test123",
    "database": "parserdb",
    "host": "postgres",
    "port": "5432"
}
# состояния бота при /retranslate
GET_TEXT, GET_PHOTO_URL, CONFIRM_SEND = range(3)

# Глобальная переменная для списка разрешенных пользователей
ALLOWED_USER_IDS: set[int] = set()

# Функция для загрузки разрешенных пользователей
def load_allowed_users() -> set[int]:
    users_str = os.getenv("ALLOWED_USER_IDS", "")
    if not users_str:
        logger.warning("ALLOWED_USER_IDS не установлен в переменных окружения!")
        return set()
    
    try:
        user_ids = {int(user_id.strip()) for user_id in users_str.split(",")}
        logger.info(f"Загружено {len(user_ids)} админов: {user_ids}")
        return user_ids
    except Exception as e:
        logger.error(f"Ошибка при загрузке ALLOWED_USER_IDS: {e}")
        return set()

def get_admin_menu() -> ReplyKeyboardMarkup:
    """Главное меню админ-бота"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("📊 Статистика"), KeyboardButton("📢 Рассылка")],
            [KeyboardButton("💱 Курсы валют")],
            [KeyboardButton("ℹ️ Помощь")]
        ],
        resize_keyboard=True
    )

# --- Работа с курсами валют ---
CURR_PATH = "/app/shared/currency_rates.json"
DEFAULT_RATES = {
    "USD": 82,
    "EUR": 90,
    "GBP": 115,
    "JPY": 0.6,
    "CNY": 12.5,
   
}

def load_currency_rates():
    if not os.path.exists(CURR_PATH):
        with open(CURR_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_RATES, f, ensure_ascii=False, indent=2)
        return DEFAULT_RATES.copy()
    try:
        with open(CURR_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка чтения курсов валют: {e}")
        return DEFAULT_RATES.copy()

def save_currency_rates(rates):
    try:
        with open(CURR_PATH, "w", encoding="utf-8") as f:
            json.dump(rates, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения курсов валют: {e}")

# --- Conversation для изменения курсов ---
SELECT_CURRENCY, ENTER_NEW_RATE = range(100, 102)

async def currency_menu(update: Update, context: CallbackContext) -> int:
    rates = load_currency_rates()
    msg = "Текущие курсы валют (1 единица в рублях):\n"
    for k, v in rates.items():
        msg += f"{k}: {v}\n"
    msg += "\nВыберите валюту для изменения:"
    buttons = [[KeyboardButton(k)] for k in rates.keys()]
    buttons.append([KeyboardButton("🔙 В меню")])
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    return SELECT_CURRENCY

async def select_currency(update: Update, context: CallbackContext) -> int:
    currency = update.message.text.strip().upper()
    rates = load_currency_rates()
    if currency == "🔙 В МЕНЮ":
        await update.message.reply_text("Вы вернулись в главное меню.", reply_markup=get_admin_menu())
        return ConversationHandler.END
    if currency not in rates:
        await update.message.reply_text("Пожалуйста, выберите валюту из списка.")
        return SELECT_CURRENCY
    context.user_data['currency_to_edit'] = currency
    await update.message.reply_text(f"Введите новый курс для {currency} (текущее значение: {rates[currency]}):", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 В меню")]], resize_keyboard=True))
    return ENTER_NEW_RATE

async def enter_new_rate(update: Update, context: CallbackContext) -> int:
    text = update.message.text.strip()
    if text == "🔙 В меню":
        await update.message.reply_text("Вы вернулись в главное меню.", reply_markup=get_admin_menu())
        return ConversationHandler.END
    currency = context.user_data.get('currency_to_edit')
    try:
        new_rate = float(text.replace(",", "."))
        rates = load_currency_rates()
        rates[currency] = new_rate
        save_currency_rates(rates)
        await update.message.reply_text(f"Курс для {currency} обновлён: {new_rate}", reply_markup=get_admin_menu())
        return ConversationHandler.END
    except Exception:
        await update.message.reply_text("Пожалуйста, введите корректное число.")
        return ENTER_NEW_RATE

def get_confirm_keyboard(with_photo: bool) -> InlineKeyboardMarkup:
    buttons = []
    if with_photo:
        buttons.append([InlineKeyboardButton("✅ Отправить с фото", callback_data='send_with_photo')])
    buttons.append([InlineKeyboardButton("📤 Отправить без фото", callback_data='send_without_photo')])
    buttons.append([InlineKeyboardButton("❌ Отменить", callback_data='cancel')])
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start - показывает главное меню"""
    user_id = update.effective_user.id
    
    logger.info(f"Получена команда /start от пользователя {user_id} (@{update.effective_user.username})")
    logger.info(f"ALLOWED_USER_IDS: {ALLOWED_USER_IDS}")
    logger.info(f"user_id in ALLOWED_USER_IDS: {user_id in ALLOWED_USER_IDS}")
    
    # Проверка прав доступа
    if user_id not in ALLOWED_USER_IDS:
        await update.message.reply_text(
            "⛔ Доступ запрещен\n\n"
            "Этот бот доступен только администраторам.\n"
            f"Ваш Telegram ID: `{user_id}`\n\n"
            "Если вы должны иметь доступ, свяжитесь с администратором.",
            parse_mode='Markdown'
        )
        logger.warning(f"Попытка доступа от неавторизованного пользователя: {user_id} (@{update.effective_user.username})")
        return
    
    # Показываем меню только админам
    await update.message.reply_text(
        f"👋 Добро пожаловать, {update.effective_user.first_name}!\n\n"
        "🔧 Админ-панель бота\n\n"
        "Доступные функции:\n"
        "📊 Статистика - посмотреть заказы пользователей\n"
        "📢 Рассылка - отправить сообщение всем пользователям\n"
        "ℹ️ Помощь - список всех команд",
        reply_markup=get_admin_menu()
    )
    logger.info(f"Админ {user_id} (@{update.effective_user.username}) вошел в систему")

async def help_command(update: Update, context: CallbackContext) -> None:
    """Обработчик кнопки Помощь"""
    if update.effective_user.id not in ALLOWED_USER_IDS:
        await update.message.reply_text("⛔ Доступ запрещен")
        logger.warning(f"Попытка доступа к /help от неавторизованного пользователя: {update.effective_user.id}")
        return
    
    await update.message.reply_text(
        "📖 Доступные команды:\n\n"
        "📊 /count - Статистика по заказам\n"
        "   Показывает всех пользователей и их заказы\n\n"
        "📢 /retranslate - Рассылка сообщений\n"
        "   Отправить сообщение всем пользователям\n"
        "   Можно добавить текст и фото\n\n"
        "ℹ️ /help - Эта справка\n"
        "🏠 /start - Главное меню",
        reply_markup=get_admin_menu()
    )

async def handle_menu_buttons(update: Update, context: CallbackContext) -> int:
    """Обработчик нажатий на кнопки меню"""
    user_id = update.effective_user.id
    
    # Дополнительная проверка безопасности
    if user_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("⛔ Доступ запрещен")
        logger.warning(f"Попытка использования меню от неавторизованного пользователя: {user_id}")
        return ConversationHandler.END
    
    text = update.message.text
    
    if text == "📊 Статистика":
        # Вызываем функцию статистики
        await count_handler(update, context)
        return ConversationHandler.END
    
    elif text == "📢 Рассылка":
        # Запускаем процесс рассылки
        return await retranslate_start(update, context)
    
    elif text == "ℹ️ Помощь":
        await help_command(update, context)
        return ConversationHandler.END
    
    else:
        # Если нажата неизвестная кнопка или просто текст
        await update.message.reply_text(
            "Используйте кнопки меню ниже или команды:",
            reply_markup=get_admin_menu()
        )
        return ConversationHandler.END
    
    return ConversationHandler.END

async def retranslate_start(update: Update, context: CallbackContext) -> int:
    """Начало процесса рассылки"""
    user_id = update.effective_user.id
    
    if user_id not in ALLOWED_USER_IDS:
        if update.message:
            await update.message.reply_text("⛔ Доступ запрещен")
        logger.warning(f"Попытка доступа к /retranslate от неавторизованного пользователя: {user_id}")
        return ConversationHandler.END
    
    context.user_data.clear()
    
    # Определяем откуда пришел запрос - из команды или кнопки
    message = update.message
    await message.reply_text(
        "📝 Введите текст сообщения для рассылки:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отменить", callback_data='cancel')]])
    )
    logger.info(f"Админ {user_id} начал процесс рассылки")
    return GET_TEXT

async def handle_text(update: Update, context: CallbackContext) -> int:
    """Обработка текста сообщения"""
    context.user_data['message_text'] = update.message.text
    await update.message.reply_text(
        "🖼 Прикрепите URL изображения (или нажмите /skip чтобы пропустить):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Пропустить", callback_data='skip_photo')]])
    )
    return GET_PHOTO_URL

async def handle_photo_url(update: Update, context: CallbackContext) -> int:
    """Обработка URL фото"""
    if update.message.text.startswith(('http://', 'https://')):
        context.user_data['photo_url'] = update.message.text
        preview_msg = f"📝 Текст:\n---------------------------------------\n {context.user_data['message_text']}\n\n---------------------------------------\n🖼 Фото: {update.message.text}"
    else:
        await update.message.reply_text("❌ Некорректный URL. Используйте http:// или https://")
        return GET_PHOTO_URL
    
    await update.message.reply_text(
        f"🔍 Предпросмотр:\n{preview_msg}",
        reply_markup=get_confirm_keyboard(with_photo='photo_url' in context.user_data)
    )
    return CONFIRM_SEND

async def skip_photo(update: Update, context: CallbackContext) -> int:
    """Пропуск прикрепления фото"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        f"📝 Текст сообщения:\n{context.user_data['message_text']}\n\n"
        "🖼 Фото не прикреплено",
        reply_markup=get_confirm_keyboard(with_photo=False)
    )
    return CONFIRM_SEND

async def confirm_send(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancel':
        await query.edit_message_text(
            "❌ Рассылка отменена",
        )
        # Возвращаем главное меню через новое сообщение
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Вы вернулись в главное меню",
            reply_markup=get_admin_menu()
        )
        return ConversationHandler.END
    
    try:
        connection = await asyncpg.connect(**DB_CONFIG)
        users = await connection.fetch("SELECT DISTINCT user_id FROM parsed_data")
        
        if not users:
            await query.edit_message_text("❌ Нет пользователей для рассылки")
            return ConversationHandler.END
        
        success = failed = 0
        message = context.user_data['message_text']
        photo_url = context.user_data.get('photo_url')
        
        await query.edit_message_text(f"🔄 Рассылка для {len(users)} пользователей...")
        
        # Создаем временного бота
        sender_bot = Bot(token=os.getenv("USER_BOT_TOKEN"))
        
        try:
            for user in users:
                try:
                    chat_id = int(user['user_id'])
                    if query.data == 'send_with_photo' and photo_url:
                        await sender_bot.send_photo(
                            chat_id=chat_id,
                            photo=photo_url,
                            caption=message
                        )
                    else:
                        await sender_bot.send_message(
                            chat_id=chat_id,
                            text=message
                        )
                    success += 1
                except Exception as e:
                    logger.error(f"Ошибка отправки {user['user_id']}: {e}")
                    failed += 1
        finally:
            await sender_bot.close()
        
        await query.edit_message_text(
            f"✅ Рассылка завершена!\n\n"
            f"📤 Успешно отправлено: {success}\n"
            f"❌ Ошибок: {failed}\n\n"
            "🔄 Приложение перезапускается..."
        )
        
        await asyncio.sleep(2)
        
        # Отправляем главное меню перед перезапуском
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Бот перезапущен. Возвращайтесь в главное меню:",
            reply_markup=get_admin_menu()
        )
        
        application = context.application
        await application.stop()
        execl(sys.executable, sys.executable, *sys.argv)
        
    except Exception as e:
        logger.error(f"Ошибка рассылки: {e}")
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    finally:
        if 'connection' in locals():
            await connection.close()
    
    return ConversationHandler.END
# Функция для списка заказов
async def count_handler(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /count — статистика по заказам с товарами, ценами и датами"""
    user_id = update.effective_user.id
    
    if user_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("⛔ Доступ запрещен")
        logger.warning(f"Попытка доступа к /count от неавторизованного пользователя: {user_id}")
        return

    try:
        logger.info(f"Админ {user_id} запросил статистику")
        connection = await asyncpg.connect(**DB_CONFIG)
        rows = await connection.fetch("""
            SELECT user_id, content, created_at
            FROM parsed_data
            ORDER BY user_id, created_at;
        """)
        await connection.close()

        if not rows:
            await update.message.reply_text("🔍 В базе нет данных.")
            return

        # Группировка заказов по user_id
        user_orders = defaultdict(list)

        for row in rows:
            uid = row["user_id"] or "неизвестно"

            try:
                content = json.loads(row["content"])
                name = content.get("name", "Без названия")
                price = content.get("price", "Без цены")
            except Exception as e:
                logger.warning(f"Ошибка парсинга JSON для {uid}: {e}")
                name = "❌ Ошибка"
                price = "—"

            try:
                created_at = row["created_at"].strftime('%Y-%m-%d %H:%M')
            except Exception as e:
                created_at = "—"

            user_orders[uid].append((name, price, created_at))

        def pluralize(count: int) -> str:
            if count % 10 == 1 and count % 100 != 11:
                return "заказ"
            elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
                return "заказа"
            else:
                return "заказов"

        lines = ["📊 Статистика по пользователям:\n"]
        for uid, orders in user_orders.items():
            count = len(orders)
            word = pluralize(count)
            lines.append(f"👤 {uid} – {count} {word}:")
            for name, price, created in orders:
                lines.append(f"  • {name} — {price}")
            lines.append("")

        await update.message.reply_text(
            "\n".join(lines).strip(),
            reply_markup=get_admin_menu()
        )

    except Exception as e:
        logger.error(f"Ошибка в /count: {e}")
        await update.message.reply_text(
            "❌ Ошибка при обращении к базе.",
            reply_markup=get_admin_menu()
        )

# Настройка обработчиков
def setup_handlers(application: Application) -> None:
    # Conversation handler для рассылки
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('retranslate', retranslate_start),
            MessageHandler(filters.Regex('^📢 Рассылка$'), handle_menu_buttons)
        ],
        states={
            GET_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)],
            GET_PHOTO_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_photo_url),
                CallbackQueryHandler(skip_photo, pattern='^skip_photo$')
            ],
            CONFIRM_SEND: [
                CallbackQueryHandler(confirm_send, pattern='^(send_with_photo|send_without_photo|cancel)$')
            ]
        },
        fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
    )

    # Conversation handler для изменения курсов валют
    currency_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^💱 Курсы валют$'), currency_menu)],
        states={
            SELECT_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_currency)],
            ENTER_NEW_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_new_rate)]
        },
        fallbacks=[]
    )

    # Основные команды (должны быть ПЕРЕД conversation handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("count", count_handler))

    # Conversation handler для рассылки
    application.add_handler(conv_handler)
    # Conversation handler для курсов валют
    application.add_handler(currency_handler)

    # Обработчики кнопок меню (должны быть ПОСЛЕ conversation handler)
    application.add_handler(MessageHandler(filters.Regex('^📊 Статистика$'), handle_menu_buttons))
    application.add_handler(MessageHandler(filters.Regex('^ℹ️ Помощь$'), handle_menu_buttons))

    # Обработчик всех остальных текстовых сообщений (самый последний!)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_buttons))

# Запуск бота

import asyncio

# ID пользователя, которому слать напоминание (можно указать свой Telegram ID)
ADMIN_NOTIFY_ID = int(os.getenv("ADMIN_NOTIFY_ID"))  # 0 = не отправлять


async def daily_reminder_task(app: Application):
    if not ADMIN_NOTIFY_ID:
        logger.info("ADMIN_NOTIFY_ID не задан, напоминания не будут отправляться.")
        return
    while True:
        # Определяем время до следующего 10:00 по Москве
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        if ZoneInfo:
            msk = now_utc.astimezone(ZoneInfo("Europe/Moscow"))
        else:
            msk = now_utc + datetime.timedelta(hours=3)
        next_10 = msk.replace(hour=10, minute=0, second=0, microsecond=0)
        if msk >= next_10:
            next_10 += datetime.timedelta(days=1)
        seconds_to_sleep = (next_10 - msk).total_seconds()
        logger.info(f"До следующего напоминания: {int(seconds_to_sleep)} секунд (до 10:00 по МСК)")
        await asyncio.sleep(seconds_to_sleep)
        try:
            logger.info(f"Отправка ежедневного напоминания админу {ADMIN_NOTIFY_ID}")
            await app.bot.send_message(
                chat_id=ADMIN_NOTIFY_ID,
                text="Пожалуйста, обновите курсы валют в админ-боте!"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания: {e}")

# Функция для запуска фоновой задачи после старта приложения
async def on_startup(app: Application):
    if ADMIN_NOTIFY_ID:
        app.create_task(daily_reminder_task(app))

if __name__ == '__main__':
    # Загружаем список разрешенных пользователей при старте
    ALLOWED_USER_IDS = load_allowed_users()

    # Проверка переменных окружения при запуске
    bot_token = os.getenv("BOT_TOKEN")

    logger.info("=" * 50)
    logger.info("ЗАПУСК АДМИН-БОТА")
    logger.info(f"BOT_TOKEN установлен: {'Да' if bot_token else 'НЕТ'}")
    logger.info(f"ALLOWED_USER_IDS переменная окружения: {os.getenv('ALLOWED_USER_IDS')}")
    logger.info(f"Загруженные админы: {ALLOWED_USER_IDS}")
    logger.info(f"ADMIN_NOTIFY_ID: {ADMIN_NOTIFY_ID}")
    logger.info("=" * 50)

    if not bot_token:
        logger.error("ОШИБКА: BOT_TOKEN не найден в переменных окружения!")
        sys.exit(1)

    if not ALLOWED_USER_IDS:
        logger.warning("ВНИМАНИЕ: ALLOWED_USER_IDS пуст! Никто не сможет пользоваться ботом!")

    app = Application.builder().token(bot_token).post_init(on_startup).build()
    setup_handlers(app)

    logger.info("Бот запущен и ожидает сообщений...")
    app.run_polling()
