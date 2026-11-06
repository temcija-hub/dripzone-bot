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
ADMIN_ID = 123456789  


# Состояния для FSM (добавление и редактирование)
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


# --- Команда /start ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = [
        [types.KeyboardButton(text="🛍 Каталог товаров")],
        [types.KeyboardButton(text="🛒 Корзина")]
    ]
    markup = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Добро пожаловать в DripZone! Выберите действие:", reply_markup=markup)
    
    # Если это админ, показываем кнопку админ-панели
    if message.from_user.id == ADMIN_ID:
        admin_kb = types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="⚙️ Админ-панель")]], 
            resize_keyboard=True
        )
        await message.answer("Вам доступна панель администратора:", reply_markup=admin_kb)


# --- Админ-панель ---
@dp.message(F.text == "⚙️ Админ-панель")
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="add_product")],
        [InlineKeyboardButton(text="📦 Управление товарами", callback_data="manage_products")]
    ])
    await message.answer("Панель администратора:", reply_markup=kb)


# --- Добавление товара (Шаг 1) ---
@dp.callback_query(F.data == "add_product")
async def start_add_product(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await state.set_state(AddProduct.waiting_for_name)
    await callback.message.answer("Введите название товара:")
    await callback.answer()


@dp.message(AddProduct.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddProduct.waiting_for_description)
    await message.answer("Введите описание товара:")


@dp.message(AddProduct.waiting_for_description)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddProduct.waiting_for_price)
    await message.answer("Введите цену товара:")


@dp.message(AddProduct.waiting_for_price)
async def process_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await state.set_state(AddProduct.waiting_for_photo)
    await message.answer("Отправьте фото товара (картинку):")


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
    await message.answer("✅ Товар успешно добавлен!")


# --- Управление и просмотр товаров для админа ---
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
        await callback.message.answer("📭 Товаров пока нет.")
        await callback.answer()
        return
    
    for prod in products:
        prod_id, name, price = prod[0], prod[1], prod[2]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить", callback_data=f"edit_prod_{prod_id}")],
            [InlineKeyboardButton(text="❌ Удалить", callback_data=f"del_prod_{prod_id}")]
        ])
        await callback.message.answer(f"📦 <b>{name}</b>\n💰 Цена: {price}", parse_mode="HTML", reply_markup=kb)
    
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
    
    await callback.message.edit_text("✅ Товар удален!")
    await callback.answer()


# --- Меню редактирования товара ---
@dp.callback_query(F.data.startswith("edit_prod_"))
async def edit_product_menu(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    prod_id = callback.data.split("_")[2]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Название", callback_data=f"set_name_{prod_id}")],
        [InlineKeyboardButton(text="📄 Описание", callback_data=f"set_desc_{prod_id}")],
        [InlineKeyboardButton(text="💰 Цена", callback_data=f"set_price_{prod_id}")]
    ])
    await callback.message.edit_text("Что именно вы хотите изменить?", reply_markup=kb)
    await callback.answer()


# Редактирование названия
@dp.callback_query(F.data.startswith("set_name_"))
async def edit_name_start(callback: types.CallbackQuery, state: FSMContext):
    prod_id = callback.data.split("_")[2]
    await state.update_data(edit_id=prod_id)
    await state.set_state(EditProduct.waiting_for_new_name)
    await callback.message.answer("Введи новое название:")
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
    await message.answer("✅ Название обновлено!")


# Редактирование описания
@dp.callback_query(F.data.startswith("set_desc_"))
async def edit_desc_start(callback: types.CallbackQuery, state: FSMContext):
    prod_id = callback.data.split("_")[2]
    await state.update_data(edit_id=prod_id)
    await state.set_state(EditProduct.waiting_for_new_description)
    await callback.message.answer("Введи новое описание:")
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
    await message.answer("✅ Описание обновлено!")


# Редактирование цены
@dp.callback_query(F.data.startswith("set_price_"))
async def edit_price_start(callback: types.CallbackQuery, state: FSMContext):
    prod_id = callback.data.split("_")[2]
    await state.update_data(edit_id=prod_id)
    await state.set_state(EditProduct.waiting_for_new_price)
    await callback.message.answer("Введи новую цену:")
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
    await message.answer("✅ Цена обновлена!")


# --- Каталог для пользователей ---
@dp.message(F.text == "🛍 Каталог товаров")
async def show_catalog(message: types.Message):
    conn = sqlite3.connect("dripzone.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, price, photo FROM products")
    products = cursor.fetchall()
    conn.close()
    
    if not products:
        await message.answer("К сожалению, каталог пока пуст.")
        return
    
    for prod in products:
        prod_id, name, desc, price, photo = prod[0], prod[1], prod[2], prod[3], prod[4]
        text = f"<b>{name}</b>\n\n{desc}\n\n💰 <b>Цена:</b> {price}"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{prod_id}")]
        ])
        
        if photo:
            await message.answer_photo(photo=photo, caption=text, parse_mode="HTML", reply_markup=kb)
        else:
            await message.answer(text, parse_mode="HTML", reply_markup=kb)


# --- Flask для Render (чтобы веб-сервис не падал по таймауту) ---
app = Flask(__name__)

@app.route("/")
def index():
    return "DripZone Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# --- Запуск бота ---
async def main():
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("Бот и Flask успешно запущены!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
