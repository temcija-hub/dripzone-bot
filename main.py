import asyncio
import logging
import os
import re
import sqlite3
import time
import urllib.request
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from flask import Flask
from threading import Thread

BOT_TOKEN = os.getenv("BOT_TOKEN", "8889115088:AAE9c82-FDe1DoSczwUboBwn5-EtajpfKwY")
ADMIN_ID = 2125409043

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class AdminStates(StatesGroup):
    waiting_for_new_price = State()
    waiting_for_new_desc = State()
    waiting_for_add_key = State()
    waiting_for_add_name = State()
    waiting_for_add_price = State()
    waiting_for_add_desc = State()
    waiting_for_add_photo = State()

def init_db():
    conn = sqlite3.connect("dripzone.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_key TEXT,
            item_name TEXT,
            item_price TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_name TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def add_user(user_id):
    conn = sqlite3.connect("dripzone.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect("dripzone.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders")
    orders_count = cursor.fetchone()[0]
    conn.close()
    return users_count, orders_count

app = Flask("")

@app.route("/")
def home():
    return "DripZone Bot is alive 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

def self_ping():
    time.sleep(10)
    while True:
        try:
            render_url = os.environ.get("RENDER_EXTERNAL_URL")
            url = render_url if render_url else "http://127.0.0.1:10000/"
            urllib.request.urlopen(url)
        except Exception:
            pass
        time.sleep(240)

PRODUCTS = {
    "dior": {
        "name": "Зіпка Dior",
        "price": "1950 грн",
        "category": "hoodies",
        "desc": (
            "<b>🏷 DIOR</b>\n"
            "💵 Ціна: 1950 грн\n"
            "📏 <b>Розміри:</b>\n"
            "• S: Довжина виробу: 67 см | Плече + рукав: 75 см | Обхват грудей: 53 см\n"
            "• M: Довжина виробу: 69 см | Плече + рукав: 80 см | Обхват грудей: 55 см\n\n"
            "📝 <b>Опис:</b> Матеріал: трьох нить ✅\n"
            "Якість 1:1 оригінал ✅\n\n"
            "Доставка 1-2 дні 📦"
        ),
        "file_id": "AgACAgIAAxkBAAIPLmrt4vNwRc8m2iQfw_-W3NKl0vGtAAI_HmsbmmpxSwABU2C581C6tgEAAwIAA3kAAz0E",
    },
    "essentials": {
        "name": "Худі Essentials",
        "price": "1950 грн",
        "category": "hoodies",
        "desc": (
            "<b>🏷 Essentials</b>\n"
            "💵 Ціна: 1950 грн\n"
            "📏 <b>Розміри:</b>\n"
            "• S: Довжина: 68.5 см | Ширина (напівобхват): 49 см | Плечі: 42 см | Рукав: 23.5 см\n\n"
            "📝 <b>Опис:</b> Матеріал: трьох нить ✅\n"
            "Якість 1:1 оригінал ✅\n\n"
            "Доставка 1-2 дні 📦"
        ),
        "file_id": "AgACAgIAAxkBAAIPEmrt4K9Wy_kOTZyJGzwXufHjDx54AAIvHmsbmmpxS9Zd79PH6rmxAQADAgADeQADPQQ",
    },
    "hellstar": {
        "name": "Худі Hellstar",
        "price": "2000 грн",
        "category": "hoodies",
        "desc": (
            "<b>🏷 Hellstar</b>\n"
            "💵 Ціна: 2000 грн\n"
            "📏 <b>Розміри:</b>\n"
            "• S: Плечі: 43 см | Грудь (полуобхват): 40 см | Рукав: 59 см | Длина: 67 см\n"
            "• M: Плечі: 45 см | Грудь (полуобхват): 42 см | Рукав: 60 см | Длина: 69 см\n\n"
            "📝 <b>Опис:</b> Матеріал: Бавовна ✅\n"
            "Якість 1:1 оригінал ✅\n\n"
            "Доставка 1-2 дні 📦"
        ),
        "file_id": "AgACAgIAAxkBAAIOz2rt3I9WAu30D6tgMDQkv35o4LQeAAIXHmsbmmpxS5SavIyPLdFbAQADAgADeQADPQQ",
    },
    "gallery": {
        "name": "Штани Gallery Dept",
        "price": "2000 грн",
        "category": "pants",
        "desc": (
            "<b>🏷 GALLERY DEPT</b>\n"
            "💵 Ціна: 2000 грн\n"
            "📏 <b>Розміри:</b>\n"
            "• S: Ширина (полупояс): 38 см | Длина: 98 см\n"
            "• M: Ширина (полупояс): 41 см | Длина: 101 см\n\n"
            "📝 <b>Опис:</b> Материал: хлопок ✅\n"
            "Качество 1:1 оригинал ✅\n\n"
            "Доставка 1-2 дня 📦"
        ),
        "file_id": "AgACAgIAAxkBAAINb2rtqdbMGQ1-UvEupvHTyQboacu4AAIRHmsbtDlwS2jgzwyjxRmzAQADAgADeQADPQQ",
    },
}

def get_reply_keyboard(user_id):
    keyboard = [
        [KeyboardButton(text="🛍 Каталог"), KeyboardButton(text="🛒 Кошик")],
        [KeyboardButton(text="📏 Розміри"), KeyboardButton(text="⭐ Відгуки")],
        [KeyboardButton(text="📞 З'вязок з менеджером")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton(text="⚙️ Адмін-панель")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    add_user(message.from_user.id)
    await message.answer(
        "Вітаємо у **DripZone**! 🔥\nОбирай стильний одяг та оформлюй замовлення в кілька кліків.",
        reply_markup=get_reply_keyboard(message.from_user.id),
        parse_mode="Markdown",
    )

@dp.message(F.text == "🛍 Каталог")
async def text_catalog(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👖 Штани", callback_data="cat_pants")],
            [InlineKeyboardButton(text="🧥 Кофти / Худі", callback_data="cat_hoodies")],
            [InlineKeyboardButton(text="👟 Кросівки", callback_data="cat_sneakers")],
            [InlineKeyboardButton(text="👕 Футболки", callback_data="cat_tshirts")],
            [InlineKeyboardButton(text="🕶 Аксесуари", callback_data="cat_accessories")],
        ]
    )
    await message.answer("Обери категорію товарів:", reply_markup=keyboard)

@dp.message(F.text == "🛒 Кошик")
async def text_cart(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("dripzone.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, item_name, item_price FROM cart WHERE user_id = ?", (user_id,))
    items = cursor.fetchall()
    conn.close()

    if not items:
        await message.answer("🛒 Ваш кошик наразі порожній.")
        return

    cart_text = "🛒 <b>Ваш кошик:</b>\n\n"
    total_price = 0
    
    for item_id, name, price in items:
        cart_text += f"• <b>{name}</b> — {price}\n"
        digits = re.sub(r"\D", "", price)
        if digits:
            total_price += int(digits)

    cart_text += f"\n💵 <b>Загальна сума:</b> {total_price} грн"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Оформити замовлення", callback_data="checkout_cart")],
            [InlineKeyboardButton(text="🗑 Очистити кошик", callback_data="clear_cart")]
        ]
    )
    await message.answer(cart_text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "clear_cart")
async def clear_cart(callback: types.CallbackQuery):
    conn = sqlite3.connect("dripzone.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (callback.from_user.id,))
    conn.commit()
    conn.close()
    await callback.message.edit_text("🛒 Ваш кошик очищено.")
    await callback.answer()

@dp.callback_query(F.data == "checkout_cart")
async def checkout_cart(callback: types.CallbackQuery):
    user = callback.from_user
    conn = sqlite3.connect("dripzone.db")
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, item_price FROM cart WHERE user_id = ?", (user.id,))
    items = cursor.fetchall()

    if not items:
        await callback.answer("Кошик порожній!", show_alert=True)
        conn.close()
        return

    items_list_str = ""
    for name, price in items:
        items_list_str += f"• {name} ({price})\n"
        cursor.execute("INSERT INTO orders (user_id, item_name) VALUES (?, ?)", (user.id, name))

    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user.id,))
    conn.commit()
    conn.close()

    username_str = f"@{user.username}" if user.username else f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

    admin_text = (
        "🚨 <b>НОВЕ ЗАМОВЛЕННЯ З КОШИКА!</b>\n\n"
        f"📦 <b>Товари:</b>\n{items_list_str}\n"
        f"👤 Покупець: {username_str}\n"
        f"🆔 ID: <code>{user.id}</code>"
    )
    try:
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
    except Exception as e:
        print(f"Помилка відправки адміну: {e}")

    buyer_text = (
        "✅ <b>Замовлення успішно оформлено!</b>\n\n"
        "📋 <b>Що робити далі:</b>\n"
        "1. Наш менеджер вже отримав список товарів і скоро напише вам.\n"
        "2. Або ви можете самі написати йому напряму для швидкого оформлення доставки:\n"
        "👉 Посилання на менеджера: @Armenhik_gang"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Написати менеджеру", url="https://t.me/Armenhik_gang")],
            [InlineKeyboardButton(text="⬅️ Головне меню", callback_data="back_home")]
        ]
    )

    await callback.message.edit_text(buyer_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer("Замовлення успішно відправлено!", show_alert=True)

@dp.message(F.text == "📏 Розміри")
async def text_sizes(message: types.Message):
    await message.answer("📏 Таблиця розмірів:\n\nS, M, L, XL — уточнюйте детальні заміри у менеджера.")

@dp.message(F.text == "⭐ Відгуки")
async def text_reviews(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Перейти до відгуків", url="https://t.me/dripproe")]
        ]
    )
    await message.answer("⭐ Усі реальні відгуки про наш магазин читайте у нашому каналі:", reply_markup=keyboard)

@dp.message(F.text == "📞 З'вязок з менеджером")
async def text_manager(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Написати менеджеру", url="https://t.me/Armenhik_gang")]
        ]
    )
    await message.answer("📩 З питань замовлень та наявності звертайтесь до менеджера:", reply_markup=keyboard)

@dp.message(F.text == "⚙️ Адмін-панель")
async def text_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📝 Редагувати / Додати товари", callback_data="admin_edit_menu")],
            [InlineKeyboardButton(text="⬅️ Головне меню", callback_data="back_home")]
        ]
    )
    await message.answer("⚙️ Панель адміністратора DripZone:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("cat_"))
async def show_category_items(callback: types.CallbackQuery):
    cat = callback.data.split("_")[1]
    
    items_buttons = []
    for key, item in PRODUCTS.items():
        if item.get("category") == cat:
            items_buttons.append([InlineKeyboardButton(text=f"{item['name']} ({item['price']})", callback_data=f"item_{key}")])
    
    items_buttons.append([InlineKeyboardButton(text="⬅️ Назад до категорій", callback_data="back_catalog")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=items_buttons)
    
    category_names = {
        "pants": "👖 Штани в наявності:",
        "hoodies": "🧥 Кофти та худі в наявності:",
        "sneakers": "👟 Кросівки в наявності:",
        "tshirts": "👕 Футболки в наявності:",
        "accessories": "🕶 Аксесуари в наявності:"
    }
    
    await callback.message.edit_text(category_names.get(cat, "📦 Товари:"), reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "back_catalog")
async def back_to_catalog(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👖 Штани", callback_data="cat_pants")],
            [InlineKeyboardButton(text="🧥 Кофти / Худі", callback_data="cat_hoodies")],
            [InlineKeyboardButton(text="👟 Кросівки", callback_data="cat_sneakers")],
            [InlineKeyboardButton(text="👕 Футболки", callback_data="cat_tshirts")],
            [InlineKeyboardButton(text="🕶 Аксесуари", callback_data="cat_accessories")],
        ]
    )
    await callback.message.edit_text("Обери категорію товарів:", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("item_"))
async def show_product(callback: types.CallbackQuery):
    item_key = callback.data.split("_")[1]
    item = PRODUCTS.get(item_key)

    if not item:
        await callback.answer("Товар не знайдено!", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Купити (Додати в кошик)", callback_data=f"buy_{item_key}")],
            [InlineKeyboardButton(text="⬅️ До каталогу", callback_data="back_catalog")],
        ]
    )

    try:
        await callback.message.delete()
    except Exception:
        pass

    if item["file_id"]:
        await callback.message.answer_photo(
            photo=item["file_id"], caption=item["desc"], reply_markup=keyboard, parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            item["desc"], reply_markup=keyboard, parse_mode="HTML"
        )

    await callback.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    item_key = callback.data.split("_")[1]
    item = PRODUCTS.get(item_key)
    user_id = callback.from_user.id
    
    conn = sqlite3.connect("dripzone.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO cart (user_id, item_key, item_name, item_price) VALUES (?, ?, ?, ?)", 
                   (user_id, item_key, item['name'], item['price']))
    conn.commit()
    conn.close()

    await callback.answer(f"✅ Товар «{item['name']}» додано до кошика!", show_alert=True)

@dp.callback_query(F.data == "back_home")
async def back_home(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "Головне меню DripZone:",
        reply_markup=get_reply_keyboard(callback.from_user.id)
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Немає доступу!", show_alert=True)
        return

    users_count, orders_count = get_stats()
    catalog_items_count = len(PRODUCTS)

    text = (
        "📊 <b>Статистика бота DripZone:</b>\n\n"
        f"👥 Кількість користувачів: <b>{users_count}</b>\n"
        f"📦 Товарів у каталозі: <b>{catalog_items_count}</b>\n"
        f"🛒 Всього замовлень: <b>{orders_count}</b>"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_edit_menu")
async def admin_edit_menu(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    buttons = []
    for key, item in PRODUCTS.items():
        buttons.append([
            InlineKeyboardButton(text=f"✏️ {item['name']}", callback_data=f"adm_edit_{key}"),
            InlineKeyboardButton(text=f"❌ Видалити", callback_data=f"adm_del_{key}")
        ])
    
    buttons.append([InlineKeyboardButton(text="➕ Додати новий товар", callback_data="adm_add_item")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("⚙️ <b>Керування товарами:</b>\nОбери товар для редагування або додай новий:", reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("adm_del_"))
async def admin_delete_item(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    item_key = callback.data.split("_")[2]
    if item_key in PRODUCTS:
        del PRODUCTS[item_key]
        await callback.answer("✅ Товар успішно видалено!", show_alert=True)
    else:
        await callback.answer("Товар не знайдено.", show_alert=True)
    
    await admin_edit_menu(callback)

@dp.callback_query(F.data.startswith("adm_edit_"))
async def admin_edit_item_menu(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    item_key = callback.data.split("_")[2]
    item = PRODUCTS.get(item_key)
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💵 Змінити ціну", callback_data=f"set_price_{item_key}")],
            [InlineKeyboardButton(text="📝 Змінити опис / розміри", callback_data=f"set_desc_{item_key}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_edit_menu")]
        ]
    )
    await callback.message.edit_text(f"Редагування товару: <b>{item['name']}</b>", reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("set_price_"))
async def start_change_price(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    item_key = callback.data.split("_")[2]
    await state.update_data(editing_key=item_key)
    await callback.message.answer("Введи нову ціну (наприклад: <code>2100 грн</code>):", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_new_price)
    await callback.answer()

@dp.message(AdminStates.waiting_for_new_price)
async def save_new_price(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    key = data.get("editing_key")
    new_price = message.text
    
    if key in PRODUCTS:
        PRODUCTS[key]["price"] = new_price
        await message.answer(f"✅ Ціну успішно змінено на <b>{new_price}</b>!", parse_mode="HTML")
    
    await state.clear()

@dp.callback_query(F.data.startswith("set_desc_"))
async def start_change_desc(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    item_key = callback.data.split("_")[2]
    await state.update_data(editing_key=item_key)
    await callback.message.answer("Введи новий повний опис та розміри для товару:", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_new_desc)
    await callback.answer()

@dp.message(AdminStates.waiting_for_new_desc)
async def save_new_desc(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    key = data.get("editing_key")
    new_desc = message.text
    
    if key in PRODUCTS:
        PRODUCTS[key]["desc"] = new_desc
        await message.answer("✅ Опис та розміри успішно оновлено!", parse_mode="HTML")
    
    await state.clear()

@dp.callback_query(F.data == "adm_add_item")
async def start_add_item(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await callback.message.answer("Введи унікальний системний ключ англійською (наприклад: <code>nike_shoes</code>):", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_add_key)
    await callback.answer()

@dp.message(AdminStates.waiting_for_add_key)
async def add_item_key(message: types.Message, state: FSMContext):
    await state.update_data(new_key=message.text.strip())
    await message.answer("Введи назву товару (наприклад: <i>Кросівки Nike</i>):", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_add_name)

@dp.message(AdminStates.waiting_for_add_name)
async def add_item_name(message: types.Message, state: FSMContext):
    await state.update_data(new_name=message.text)
    await message.answer("Введи ціну товару (наприклад: <code>2500 грн</code>):", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_add_price)

@dp.message(AdminStates.waiting_for_add_price)
async def add_item_price(message: types.Message, state: FSMContext):
    await state.update_data(new_price=message.text)
    await message.answer("Введи повний опис та розміри товару:")
    await state.set_state(AdminStates.waiting_for_add_desc)

@dp.message(AdminStates.waiting_for_add_desc)
async def add_item_desc(message: types.Message, state: FSMContext):
    await state.update_data(new_desc=message.text)
    await message.answer("Надішли фотографію для цього товару (картинкою):")
    await state.set_state(AdminStates.waiting_for_add_photo)

@dp.message(AdminStates.waiting_for_add_photo, F.photo)
async def add_item_photo(message: types.Message, state: FSMContext):
    photo_file_id = message.photo[-1].file_id
    data = await state.get_data()
    
    key = data.get("new_key")
    PRODUCTS[key] = {
        "name": data.get("new_name"),
        "price": data.get("new_price"),
        "category": "hoodies",
        "desc": data.get("new_desc"),
        "file_id": photo_file_id
    }
    
    await message.answer("✅ Новий товар успішно додано до каталогу!", reply_markup=get_reply_keyboard(message.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📝 Редагувати / Додати товари", callback_data="admin_edit_menu")],
            [InlineKeyboardButton(text="⬅️ Головне меню", callback_data="back_home")]
        ]
    )
    await callback.message.edit_text("⚙️ Панель адміністратора DripZone:", reply_markup=keyboard)
    await callback.answer()

async def main():
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    ping_thread = Thread(target=self_ping)
    ping_thread.daemon = True
    ping_thread.start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
