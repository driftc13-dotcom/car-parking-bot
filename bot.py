from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import json
import logging
import os
from dotenv import load_dotenv

# Принудительная перезагрузка переменных окружения
load_dotenv(override=True)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_GROUP_ID = "-1003694488802"  # ID группы для уведомлений
ALLOWED_ADMINS = os.getenv("ALLOWED_ADMINS", "").split(",")

logger.info(f"ADMIN_GROUP_ID: {ADMIN_GROUP_ID}")

if not TOKEN:
    raise ValueError("TOKEN не установлен в .env файле")

storage = MemoryStorage()
bot = Bot(TOKEN)
dp = Dispatcher(bot, storage=storage)

# Файл с товарами
PRODUCTS_FILE = "products.json"

# Состояния для добавления товара
class AddProduct(StatesGroup):
    waiting_for_name = State()
    waiting_for_price = State()
    waiting_for_description = State()
    waiting_for_photo = State()

# Функция для экранирования Markdown
def escape_markdown(text):
    """Экранирует специальные символы Markdown"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

# Загрузка товаров
def load_products():
    try:
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

# Сохранение товаров
def save_products(products):
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

# Проверка админа
def is_admin(user):
    is_admin_by_id = user.id == ADMIN_ID
    is_admin_by_username = user.username in ALLOWED_ADMINS
    
    logger.info(f"Проверка админа: user_id={user.id}, username={user.username}, "
                f"ADMIN_ID={ADMIN_ID}, ALLOWED_ADMINS={ALLOWED_ADMINS}, "
                f"is_admin_by_id={is_admin_by_id}, is_admin_by_username={is_admin_by_username}")
    
    return is_admin_by_id or is_admin_by_username

# Главное меню
def main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🛒 Магазин"))
    keyboard.add(KeyboardButton("ℹ️ Информация"))
    return keyboard

# Админ меню
def admin_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🛒 Магазин"), KeyboardButton("➕ Добавить товар"))
    keyboard.add(KeyboardButton("📝 Список товаров"), KeyboardButton("🗑 Удалить товар"))
    keyboard.add(KeyboardButton("ℹ️ Информация"))
    return keyboard

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user = message.from_user
    chat_id = message.chat.id
    
    # Показываем ID чата (для групп это будет отрицательное число)
    logger.info(f"Chat ID: {chat_id}, User {user.first_name} (@{user.username}) ID: {user.id}")
    
    # Если это группа, показываем ID группы
    if message.chat.type in ['group', 'supergroup']:
        await message.answer(f"🆔 ID этой группы: `{chat_id}`\n\nСкопируйте и добавьте в .env файл как ADMIN_GROUP_ID", parse_mode="Markdown")
        return
    
    if is_admin(user):
        await message.answer(
            f"👋 Привет, {user.first_name}!\n\n"
            "🎮 Добро пожаловать в магазин Car Parking!\n\n"
            "👑 Вы администратор. Доступны все функции.",
            reply_markup=admin_menu()
        )
    else:
        await message.answer(
            f"👋 Привет, {user.first_name}!\n\n"
            "🎮 Добро пожаловать в магазин Car Parking!\n"
            "Здесь вы можете заказать игровые товары.\n\n"
            "Нажмите 🛒 Магазин чтобы посмотреть товары.",
            reply_markup=main_menu()
        )

@dp.message_handler(lambda message: message.text == "🛒 Магазин")
async def show_shop(message: types.Message):
    products = load_products()
    
    if not products:
        await message.answer("😔 Магазин пока пуст. Товары скоро появятся!")
        return
    
    for i, product in enumerate(products):
        name = escape_markdown(product['name'])
        price = escape_markdown(str(product['price']))
        description = escape_markdown(product['description'])
        
        text = f"📦 *{name}*\n\n"
        text += f"💰 Цена: {price} грн\n"
        text += f"📝 {description}\n"
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(
            f"🛒 Заказать", 
            callback_data=f"buy_{i}"
        ))
        
        # Если есть фото - отправляем с фото
        if product.get('photo'):
            await message.answer_photo(
                photo=product['photo'],
                caption=text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        else:
            await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == "ℹ️ Информация")
async def info(message: types.Message):
    await message.answer(
        "ℹ️ *Информация о магазине*\n\n"
        "🎮 Магазин игровых товаров Car Parking\n\n"
        "📞 *Поддержка:* @Arizonaa_cpm\n"
        "💬 *Вопросы:* @sukunuma\n\n"
        "💡 Как заказать:\n"
        "1. Выберите товар в магазине\n"
        "2. Нажмите 'Заказать'\n"
        "3. Ожидайте связи с администратором",
        parse_mode="Markdown"
    )

# Админ команды
@dp.message_handler(lambda message: message.text == "➕ Добавить товар")
async def add_product_start(message: types.Message):
    if not is_admin(message.from_user):
        await message.answer("❌ У вас нет прав администратора")
        return
    
    await AddProduct.waiting_for_name.set()
    await message.answer(
        "➕ *Добавление товара*\n\n"
        "Шаг 1/4: Введите название товара:",
        parse_mode="Markdown"
    )

@dp.message_handler(state=AddProduct.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await AddProduct.waiting_for_price.set()
    await message.answer("Шаг 2/4: Введите цену товара (только число):")

@dp.message_handler(state=AddProduct.waiting_for_price)
async def process_price(message: types.Message, state: FSMContext):
    if not message.text.replace(".", "").isdigit():
        await message.answer("❌ Цена должна быть числом. Попробуйте еще раз:")
        return
    
    await state.update_data(price=message.text)
    await AddProduct.waiting_for_description.set()
    await message.answer("Шаг 3/4: Введите описание товара:")

@dp.message_handler(state=AddProduct.waiting_for_description)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await AddProduct.waiting_for_photo.set()
    
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("⏭ Пропустить фото"))
    
    await message.answer(
        "Шаг 4/4: Отправьте фото товара или нажмите 'Пропустить фото':",
        reply_markup=keyboard
    )

@dp.message_handler(lambda message: message.text == "⏭ Пропустить фото", state=AddProduct.waiting_for_photo)
async def skip_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    products = load_products()
    products.append({
        "name": data['name'],
        "price": data['price'],
        "description": data['description'],
        "photo": None
    })
    save_products(products)
    
    await state.finish()
    await message.answer(
        f"✅ Товар '{data['name']}' добавлен без фото!",
        reply_markup=admin_menu()
    )
    
    # Уведомление в группу
    try:
        if ADMIN_GROUP_ID:
            name = escape_markdown(data['name'])
            price = escape_markdown(data['price'])
            description = escape_markdown(data['description'])
            
            group_text = (
                f"➕ *Новый товар добавлен!*\n\n"
                f"📦 Название: {name}\n"
                f"💰 Цена: {price} грн\n"
                f"📝 Описание: {description}\n"
                f"🚫 Без фото"
            )
            await bot.send_message(int(ADMIN_GROUP_ID), group_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления о добавлении: {e}")

@dp.message_handler(content_types=['photo'], state=AddProduct.waiting_for_photo)
async def process_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id
    
    products = load_products()
    products.append({
        "name": data['name'],
        "price": data['price'],
        "description": data['description'],
        "photo": photo_id
    })
    save_products(products)
    
    await state.finish()
    await message.answer(
        f"✅ Товар '{data['name']}' добавлен с фото!",
        reply_markup=admin_menu()
    )
    
    # Уведомление в группу
    try:
        if ADMIN_GROUP_ID:
            name = escape_markdown(data['name'])
            price = escape_markdown(data['price'])
            description = escape_markdown(data['description'])
            
            group_text = (
                f"➕ *Новый товар добавлен!*\n\n"
                f"📦 Название: {name}\n"
                f"💰 Цена: {price} грн\n"
                f"📝 Описание: {description}\n"
                f"📷 С фото"
            )
            await bot.send_photo(int(ADMIN_GROUP_ID), photo=photo_id, caption=group_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления о добавлении: {e}")

@dp.message_handler(lambda message: message.text == "📝 Список товаров")
async def list_products(message: types.Message):
    if not is_admin(message.from_user):
        await message.answer("❌ У вас нет прав администратора")
        return
    
    products = load_products()
    
    if not products:
        await message.answer("📝 Список товаров пуст")
        return
    
    text = "📝 *Список товаров:*\n\n"
    for i, product in enumerate(products):
        photo_status = "📷" if product.get('photo') else "🚫"
        text += f"{i+1}. {product['name']} - {product['price']} грн {photo_status}\n"
    
    await message.answer(text, parse_mode="Markdown")

@dp.message_handler(lambda message: message.text == "🗑 Удалить товар")
async def delete_product_start(message: types.Message):
    if not is_admin(message.from_user):
        await message.answer("❌ У вас нет прав администратора")
        return
    
    products = load_products()
    
    if not products:
        await message.answer("📝 Список товаров пуст")
        return
    
    text = "🗑 *Удаление товара*\n\n"
    text += "Отправьте номер товара для удаления:\n\n"
    
    for i, product in enumerate(products):
        photo_status = "📷" if product.get('photo') else "🚫"
        text += f"{i+1}. {product['name']} {photo_status}\n"
    
    await message.answer(text, parse_mode="Markdown")

# Обработка удаления товаров
@dp.message_handler(lambda message: is_admin(message.from_user) and message.text.isdigit())
async def delete_product(message: types.Message):
    try:
        logger.info(f"Попытка удаления товара пользователем {message.from_user.username} (ID: {message.from_user.id})")
        
        index = int(message.text) - 1
        products = load_products()
        
        if index < 0 or index >= len(products):
            await message.answer("❌ Неверный номер товара")
            return
        
        deleted = products.pop(index)
        save_products(products)
        
        logger.info(f"Товар '{deleted['name']}' удален пользователем {message.from_user.username}")
        
        await message.answer(f"✅ Товар '{deleted['name']}' удален!", reply_markup=admin_menu())
        
        # Уведомление в группу
        try:
            if ADMIN_GROUP_ID:
                name = escape_markdown(deleted['name'])
                price = escape_markdown(str(deleted['price']))
                description = escape_markdown(deleted['description'])
                
                group_text = (
                    f"🗑 *Товар удален!*\n\n"
                    f"📦 Название: {name}\n"
                    f"💰 Цена: {price} грн\n"
                    f"📝 Описание: {description}"
                )
                if deleted.get('photo'):
                    await bot.send_photo(int(ADMIN_GROUP_ID), photo=deleted['photo'], caption=group_text, parse_mode="Markdown")
                else:
                    await bot.send_message(int(ADMIN_GROUP_ID), group_text, parse_mode="Markdown")
                logger.info(f"Уведомление об удалении отправлено в группу")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об удалении: {e}")
            
    except Exception as e:
        logger.error(f"Ошибка при удалении товара: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")

# Обработка покупки
@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    try:
        index = int(callback.data.split("_")[1])
        products = load_products()
        
        if index >= len(products):
            await callback.answer("❌ Товар не найден")
            return
        
        product = products[index]
        user = callback.from_user
        
        # Экранируем данные для Markdown
        product_name = escape_markdown(product['name'])
        product_price = escape_markdown(str(product['price']))
        user_first_name = escape_markdown(user.first_name)
        user_username = escape_markdown(user.username or 'нет username')
        
        # Отправка уведомления админу (только если ADMIN_ID корректный)
        admin_text = (
            f"🛒 *Новый заказ!*\n\n"
            f"👤 Покупатель: {user_first_name} (@{user_username})\n"
            f"🆔 ID: `{user.id}`\n\n"
            f"📦 Товар: {product_name}\n"
            f"💰 Цена: {product_price} грн\n\n"
            f"Свяжитесь с покупателем для завершения сделки!"
        )
        
        # Отправляем уведомление в группу админов
        try:
            if ADMIN_GROUP_ID:
                group_id = int(ADMIN_GROUP_ID)
                if product.get('photo'):
                    await bot.send_photo(group_id, photo=product['photo'], caption=admin_text, parse_mode="Markdown")
                else:
                    await bot.send_message(group_id, admin_text, parse_mode="Markdown")
                logger.info(f"Уведомление отправлено в группу {group_id}")
            else:
                logger.warning("ADMIN_GROUP_ID не установлен в .env")
        except Exception as e:
            logger.error(f"Ошибка при отправке в группу: {e}")
            logger.info(f"Заказ от пользователя {user.id} (@{user.username}): {product['name']}")
        
        # Отправка подтверждения покупателю
        await callback.message.answer(
            f"✅ *Заказ оформлен!*\n\n"
            f"📦 Товар: {product['name']}\n"
            f"💰 Цена: {product['price']} грн\n\n"
            f"Администратор скоро свяжется с вами для завершения заказа.\n"
            f"Ожидайте сообщения!",
            parse_mode="Markdown"
        )
        
        await callback.answer("✅ Заказ отправлен!")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке покупки: {e}")
        await callback.answer("❌ Ошибка при оформлении заказа")

if __name__ == "__main__":
    logger.info("Запуск бота...")
    executor.start_polling(dp)
