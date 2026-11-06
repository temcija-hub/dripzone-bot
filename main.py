import os
import sqlite3
import threading
from flask import Flask
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Токен берется из переменных окружения Render
TOKEN = os.environ.get("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ID администратора (при необходимости измени на свой Telegram ID)
ADMIN_ID = 2125409043  


# Состояния для выбора языка и товаров
class UserState(StatesGroup):
    waiting_for_language = State()

class AddProduct(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_photo = State()

class EditProduct(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_description = State()
    waiting_for_new_price = State()


# Инициализация базы данных
def init_db():
    conn = sqlite3.connect("dripzone.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            price TEXT,
            photo TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


# --- Команда /start: Выбор языка ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_language)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang_ua"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")
        ]
    ])
    await message.answer("Оберіть мову / Выберите язык:", reply_markup=kb)


# --- Обработка выбора языка ---
@dp.callback_query(F.data.startswith("lang_"))
async def process_language(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    await state.clear()
    
    if lang == "ua":
        text = "Ласкаво просимо в DripZone! Головне меню:"
        kb = [
            [types.KeyboardButton(text="🔥 Каталог брендів"), types.KeyboardButton(text="🛒 Кошик")],
            [types.KeyboardButton(text="📐 Розміри"), types.KeyboardButton(text="💬 Зв'язок з менеджером")]
        ]
        admin_btn = "⚙️ Адмін панель"
        admin_msg = "Вам доступна панель адміністратора:"
    else:
        text = "Добро пожаловать в DripZone! Главное меню:"
        kb = [
            [types.KeyboardButton(text="🔥 Каталог брендов"), types.KeyboardButton(text="🛒 Корзина")],
            [types.KeyboardButton(text="📐 Размеры"), types.KeyboardButton(text="💬 Связь с менеджером")]
        ]
        admin_btn = "⚙️ Админ панель"
        admin_msg = "Вам доступна панель администратора:"
        
    markup = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await callback.message.edit_text("Мову успішно обрано! / Язык успешно выбран!")
    await callback.message.answer(text, reply_markup=markup)
    
    # Если это админ, показываем кнопку админ-панели
    if callback.from_user.id == ADMIN_ID:
        admin_kb = types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text=admin_btn)]], 
            resize_keyboard=True
        )
        await callback.message.answer(admin_msg, reply_markup=admin_kb)
    
    await callback.answer()


# --- Обработка кнопок меню ---
@dp.message(F.text.in_(["💬 Зв'язок з менеджером", "💬 Связь с менеджером"]))
async def contact_manager(message: types.Message):
    await message.answer("З приводу замовлень та питань звертайтесь до менеджера: @your_manager")

@dp.message(F.text.in_(["📐 Розміри", "📐 Размеры"]))
async def show_sizes(message: types.Message):
    await message.answer("📐 <b>Таблиця розмірів:</b>\n\nS — зріст 160-170\nM — зріст 170-175\nL — зріст 175-182\nXL — зріст 182+", parse_mode="HTML")


# --- Админ-панель ---
@dp.message(F.text.in_(["⚙️ Адмін панель", "⚙️ Админ панель"]))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Додати товар", callback_data="add_product")],
        [InlineKeyboardButton(text="📦 Управління товарами", callback_data="manage_products")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="bot_stats")]
    ])
    await message.answer("<b>Панель адміністратора:</b>", parse_mode="HTML", reply_markup=kb)


# --- Статистика для админа ---
@dp.callback_query(F.data == "bot_stats")
async def callback_stats(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect("dripzone.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]
    conn.close()
    
    await callback.message.answer(f"📊 Кількість товарів у магазині: {count}")
    await callback.answer()


# --- Добавление товара ---
@dp.callback_query(F.data == "add_product")
async def start_add_product(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await state.set_state(AddProduct.waiting_for_name)
    await callback.message.answer("Введіть назву товару:")
    await callback.answer()

@dp.message(AddProduct.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddProduct.waiting_for_description)
    await message.answer("Введіть опис товару:")

@dp.message(AddProduct.waiting_for_description)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddProduct.waiting_for_price)
    await message.answer("Введіть ціну товару:")

@dp.message(AddProduct.waiting_for_price)
async def process_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await state.set_state(AddProduct.waiting_for_photo)
    await message.answer("Надішліть фото товару (картинку):")

@dp.message(AddProduct.waiting_for_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    
    conn = sqlite3.connect("dripzone.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, description, price, photo) VALUES (?, ?, ?, ?)",
        (data["name"], data["description"], data["price"], photo_id)
    )
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer("✅ Товар успішно додано!")


# --- Управление товарами ---
@dp.callback_query(F.data == "manage_products")
async def manage_products(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect("dripzone.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price FROM products")
    products = cursor.fetchall()
    conn.close()
    
    if not products:
        await callback.message.answer("📭 Товарів поки немає.")
        await callback.answer()
        return
    
    for prod in products:
        prod_id, name, price = prod[0], prod[1], prod[2]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Змінити", callback_data=f"edit_prod_{prod_id}")],
            [InlineKeyboardButton(text="❌ Видалити", callback_data=f"del_prod_{prod_id}")]
        ])
        await callback.message.answer(f"📦 <b>{name}</b>\n💰 Ціна: {price}", parse_mode="HTML", reply_markup=kb)
    
    await callback.answer()


# --- Удаление товара ---
@dp.callback_query(F.data.startswith("del_prod_"))
async def delete_product(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    prod_id = callback.data.split("_")[2]
    conn = sqlite3.connect("dripzone.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text("✅ Товар видалено!")
    await callback.answer()


# --- Редактирование товара ---
@dp.callback_query(F.data.startswith("edit_prod_"))
async def edit_product_menu(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    prod_id = callback.data.split("_")[2]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Назву", callback_data=f"set_name_{prod_id}")],
        [InlineKeyboardButton(text="📄 Опис", callback_data=f"set_desc_{prod_id}")],
        [InlineKeyboardButton(text="💰 Ціну", callback_data=f"set_price_{prod_id}")]
    ])
    await callback.message.edit_text("Що саме ви хочете змінити?", reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("set_name_"))
async def edit_name_start(callback: types.CallbackQuery, state: FSMContext):
    prod_id = callback.data.split("_")[2]
    await state.update_data(edit_id=prod_id)
    await state.set_state(EditProduct.waiting_for_new_name)
    await callback.message.answer("Введи нову назву:")
    await callback.answer()

@dp.message(EditProduct.waiting_for_new_name)
async def edit_name_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect("dripzone.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET name = ? WHERE id = ?", (message.text, data["edit_id"]))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer("✅ Назву оновлено!")


@dp.callback_query(F.data.startswith("set_desc_"))
async def edit_desc_start(callback: types.CallbackQuery, state: FSMContext):
    prod_id = callback.data.split("_")[2]
    await state.update_data(edit_id=prod_id)
    await state.set_state(EditProduct.waiting_for_new_description)
    await callback.message.answer("Введи новий опис:")
    await callback.answer()

@dp.message(EditProduct.waiting_for_new_description)
async def edit_desc_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect("dripzone.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET description = ? WHERE id = ?", (message.text, data["edit_id"]))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer("✅ Опис оновлено!")


@dp.callback_query(F.data.startswith("set_price_"))
async def edit_price_start(callback: types.CallbackQuery, state: FSMContext):
    prod_id = callback.data.split("_")[2]
    await state.update_data(edit_id=prod_id)
    await state.set_state(EditProduct.waiting_for_new_price)
    await callback.message.answer("Введи нову ціну:")
    await callback.answer()

@dp.message(EditProduct.waiting_for_new_price)
async def edit_price_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect("dripzone.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET price = ? WHERE id = ?", (message.text, data["edit_id"]))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer("✅ Ціну оновлено!")


# --- Каталог ---
@dp.message(F.text.in_(["🔥 Каталог брендів", "🔥 Каталог брендов"]))
async def show_catalog(message: types.Message):
    conn = sqlite3.connect("dripzone.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, price, photo FROM products")
    products = cursor.fetchall()
    conn.close()
    
    if not products:
        await message.answer("Каталог поки порожній / Каталог пока пуст.")
        return
    
    for prod in products:
        prod_id, name, desc, price, photo = prod[0], prod[1], prod[2], prod[3], prod[4]
        text = f"<b>{name}</b>\n\n{desc}\n\n💰 <b>Ціна:</b> {price}"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Додати в кошик / Добавить в корзину", callback_data=f"buy_{prod_id}")]
        ])
        
        if photo:
            await message.answer_photo(photo=photo, caption=text, parse_mode="HTML", reply_markup=kb)
        else:
            await message.answer(text, parse_mode="HTML", reply_markup=kb)


# --- Flask для Render ---
app = Flask(__name__)

@app.route("/")
def index():
    return "DripZone Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


async def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("Бот і Flask успішно запущені!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
