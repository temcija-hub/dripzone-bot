import threading
from flask import Flask

app = Flask('')


@app.route('/')
def home():
  return 'Bot is running!'


def run_web():
  app.run(host='0.0.0.0', port=10000)


threading.Thread(target=run_web).daemon = True

import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery

API_TOKEN = "8889115088:AAGJ_IO4jvhmXm8g8c2osXmk29iCbW_ACVo"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ДЛЯ ТОВАРОВ ---
conn = sqlite3.connect("dripzone.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price INTEGER,
    discount_price INTEGER DEFAULT 0
)
""")
conn.commit()


# --- СТАРТ И ГЛАВНОЕ МЕНЮ ---
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog_main")],
        [InlineKeyboardButton(text="⚙️ Керування товарами", callback_data="admin_menu")]
    ])
    await message.answer("Вітаю у DRIPZONE Shop! Вибери потрібний розділ:", reply_markup=markup)


# --- АДМИН-МЕНЮ ---
@dp.callback_query(F.data == "admin_menu")
async def admin_menu_handler(callback: CallbackQuery):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Вибрати товар для зміни", callback_data="show_items_list")],
        [InlineKeyboardButton(text="⬅️ Головне меню", callback_data="back_to_main")]
    ])
    await callback.message.edit_text("⚙️ Меню адміністратора:", reply_markup=markup)
    await callback.answer()


# --- ВЫВОД СПИСКА ТОВАРОВ ---
@dp.callback_query(F.data.in_(["show_items_list", "back_to_items_list"]))
async def show_items_list(callback: CallbackQuery):
    cursor.execute("SELECT id, name, price, discount_price FROM items")
    items = cursor.fetchall()

    if not items:
        cursor.execute("INSERT INTO items (name, price, discount_price) VALUES (?, ?, ?)", ("Gallery Dept", 2290, 2000))
        cursor.execute("INSERT INTO items (name, price, discount_price) VALUES (?, ?, ?)", ("DIOR GREY", 2000, 0))
        cursor.execute("INSERT INTO items (name, price, discount_price) VALUES (?, ?, ?)", ("HELLSTAR", 2100, 0))
        cursor.execute("INSERT INTO items (name, price, discount_price) VALUES (?, ?, ?)", ("ESSENTIALS", 2150, 0))
        conn.commit()
        cursor.execute("SELECT id, name, price, discount_price FROM items")
        items = cursor.fetchall()

    buttons = []
    for item_id, name, price, discount_price in items:
        if discount_price > 0:
            item_text = f"🔥 {name} ({price} ➡️ {discount_price} грн)"
        else:
            item_text = f"⚙️ {name} ({price} грн)"
        buttons.append([InlineKeyboardButton(text=item_text, callback_data=f"edit_item_{item_id}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад в адмінку", callback_data="admin_menu")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("⚙️ Вибери товар для зміни чи налаштування знижки:", reply_markup=markup)
    await callback.answer()


# --- МЕНЮ РЕДАКТИРОВАНИЯ ТОВАРА ---
@dp.callback_query(F.data.startswith("edit_item_"))
async def process_edit_item(callback: CallbackQuery):
    item_id = callback.data.split("_")[2]

    cursor.execute("SELECT name, price, discount_price FROM items WHERE id = ?", (item_id,))
    item = cursor.fetchone()

    if not item:
        await callback.answer("Товар не знайдено!", show_alert=True)
        return

    name, price, discount_price = item

    if discount_price > 0:
        price_info = f"💰 Ціна: <s>{price} грн</s> <b>{discount_price} грн 🔥</b>"
    else:
        price_info = f"💰 Ціна: {price} грн"

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Акція (2290 ➡️ 2000)", callback_data=f"set_sale_2000_{item_id}")],
        [InlineKeyboardButton(text="❌ Сбросить скидку", callback_data=f"clear_disc_{item_id}")],
        [InlineKeyboardButton(text="🗑 Удалить товар", callback_data=f"delete_item_{item_id}")],
        [InlineKeyboardButton(text="⬅️ Назад до списку", callback_data="back_to_items_list")]
    ])

    await callback.message.edit_text(
        f"⚙️ Управління товаром:\n📌 Назва: <b>{name}</b>\n{price_info}\n\nВибери дію:",
        reply_markup=markup,
        parse_mode="HTML"
    )
    await callback.answer()


# --- УСТАНОВКА АКЦИИ ---
@dp.callback_query(F.data.startswith("set_sale_2000_"))
async def set_sale_2000(callback: CallbackQuery):
    item_id = callback.data.split("_")[3]
    cursor.execute("UPDATE items SET price = ?, discount_price = ? WHERE id = ?", (2290, 2000, item_id))
    conn.commit()

    await callback.answer("Акция успешно настроена! 🔥", show_alert=True)
    await process_edit_item(callback)


# --- СБРОС СКИДКИ ---
@dp.callback_query(F.data.startswith("clear_disc_"))
async def clear_discount(callback: CallbackQuery):
    item_id = callback.data.split("_")[2]
    cursor.execute("UPDATE items SET discount_price = 0 WHERE id = ?", (item_id,))
    conn.commit()

    await callback.answer("Скидку скасовано! ❌", show_alert=True)
    await process_edit_item(callback)


# --- УДАЛЕНИЕ ТОВАРА ---
@dp.callback_query(F.data.startswith("delete_item_"))
async def process_delete_item(callback: CallbackQuery):
    item_id = callback.data.split("_")[2]
    cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()

    await callback.answer("Товар успішно видалено! ✅", show_alert=True)
    await show_items_list(callback)


# --- ВОЗВРАТ В ГЛАВНОЕ МЕНЮ ---
@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog_main")],
        [InlineKeyboardButton(text="⚙️ Керування товарами", callback_data="admin_menu")]
    ])
    await callback.message.edit_text("Головне меню:", reply_markup=markup)
    await callback.answer()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
