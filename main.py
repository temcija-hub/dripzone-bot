import asyncio
import logging
import os
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyParameters, ReplyKeyboardMarkup
from flask import Flask
from threading import Thread

BOT_TOKEN = os.getenv("BOT_TOKEN", "8889115088:AAE9c82-FDe1DoSczwUboBwn5-EtajpfKwY")
ADMIN_ID = 2125409043

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАНИХ SQLite (для статистики) ---
def init_db():
  conn = sqlite3.connect("dripzone.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
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

# --- ФЛАСК ДЛЯ UPTIME ---
app = Flask("")

@app.route("/")
def home():
  return "DripZone Bot is alive and running 24/7!"

def run_flask():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)

def keep_alive():
  t = Thread(target=run_flask)
  t.start()

# --- КАТАЛОГ ТОВАРІВ ---
PRODUCTS = {
    "dior": {
        "name": "Футболка Dior",
        "price": "1200 грн",
        "desc": "Стильна брендова футболка Dior. Преміум якість.",
        "file_id": "AgACAgIAAxkBAAIPLmrt4vNwRc8m2iQfw_-W3NKl0vGtAAI_HmsbmmpxSwABU2C581C6tgEAAwIAA3kAAz0E",
    },
    "essentials": {
        "name": "Худі Essentials",
        "price": "2100 грн",
        "desc": "Тепле оверсайз худі Fear of God Essentials.",
        "file_id": "AgACAgIAAxkBAAIPEmrt4K9Wy_kOTZyJGzwXufHjDx54AAIvHmsbmmpxS9Zd79PH6rmxAQADAgADeQADPQQ",
    },
    "hellstar": {
        "name": "Худі Hellstar",
        "price": "2300 грн",
        "desc": "Яскравий та унікальний принт Hellstar.",
        "file_id": "AgACAgIAAxkBAAIOz2rt3I9WAu30D6tgMDQkv35o4LQeAAIXHmsbmmpxS5SavIyPLdFbAQADAgADeQADPQQ",
    },
    "gallery": {
        "name": "Свитшот Gallery Dept",
        "price": "1900 грн",
        "desc": "Фірмовий стиль та унікальний дизайн Gallery Dept.",
        "file_id": "AgACAgIAAxkBAAINb2rtqdbMGQ1-UvEupvHTyQboacu4AAIRHmsbtDlwS2jgzwyjxRmzAQADAgADeQADPQQ",
    },
}

# --- КЛАВІАТУРА ВНИЗУ ---
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

# --- КНОПКИ НИЖНЬОГО МЕНЮ ---
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
  await message.answer("🛒 Ваш кошик наразі порожній.")

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
          [InlineKeyboardButton(text="⬅️ Головне меню", callback_data="back_home")]
      ]
  )
  await message.answer("⚙️ Панель адміністратора DripZone:", reply_markup=keyboard)

# --- РОБОТА З КАТЕГОРІЯМИ ТОВАРІВ ---
@dp.callback_query(F.data.startswith("cat_"))
async def show_category_items(callback: types.CallbackQuery):
  cat = callback.data.split("_")[1]
  
  if cat == "tshirts":
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Футболка Dior (1200 грн)", callback_data="item_dior")],
            [InlineKeyboardButton(text="⬅️ Назад до категорій", callback_data="back_catalog")]
        ]
    )
    text = "👕 Футболки в наявності:"
  elif cat == "hoodies":
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Худі Essentials (2100 грн)", callback_data="item_essentials")],
            [InlineKeyboardButton(text="Худі Hellstar (2300 грн)", callback_data="item_hellstar")],
            [InlineKeyboardButton(text="Свитшот Gallery Dept (1900 грн)", callback_data="item_gallery")],
            [InlineKeyboardButton(text="⬅️ Назад до категорій", callback_data="back_catalog")]
        ]
    )
    text = "🧥 Кофти та худі в наявності:"
  else:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад до категорій", callback_data="back_catalog")]
        ]
    )
    text = "📦 У цій категорії товари скоро з'являться!"

  await callback.message.edit_text(text, reply_markup=keyboard)
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
          [InlineKeyboardButton(text="🛒 Купити", callback_data=f"buy_{item_key}")],
          [InlineKeyboardButton(text="⬅️ До каталогу", callback_data="back_catalog")],
      ]
  )

  text = f"<b>{item['name']}</b>\n\nЦіна: {item['price']}\n{item['desc']}"

  try:
    await callback.message.delete()
  except Exception:
    pass

  if item["file_id"]:
    await callback.message.answer_photo(
        photo=item["file_id"], caption=text, reply_markup=keyboard, parse_mode="HTML"
    )
  else:
    await callback.message.answer(
        text, reply_markup=keyboard, parse_mode="HTML"
    )

  await callback.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
  item_key = callback.data.split("_")[1]
  item = PRODUCTS.get(item_key)
  
  # Записуємо замовлення в БД
  conn = sqlite3.connect("dripzone.db")
  cursor = conn.cursor()
  cursor.execute("INSERT INTO orders (user_id, item_name) VALUES (?, ?)", (callback.from_user.id, item['name']))
  conn.commit()
  conn.close()

  await callback.answer("✅ Замовлення оформлено! Менеджер зв'яжеться з вами.", show_alert=True)

@dp.callback_query(F.data == "back_home")
async def back_home(callback: types.CallbackQuery):
  await callback.message.delete()
  await callback.message.answer(
      "Головне меню DripZone:",
      reply_markup=get_reply_keyboard(callback.from_user.id)
  )
  await callback.answer()

# --- АДМІН-ПАНЕЛЬ (СТАТИСТИКА) ---
@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
  if callback.from_user.id != ADMIN_ID:
    await callback.answer("Немає доступу!", show_alert=True)
    return

  users_count, orders_count = get_stats()
  catalog_items_count = len(PRODUCTS)

  text = (
      "📊 **Статистика бота DripZone:**\n\n"
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

@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery):
  if callback.from_user.id != ADMIN_ID:
    return
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
          [InlineKeyboardButton(text="⬅️ Головне меню", callback_data="back_home")]
      ]
  )
  await callback.message.edit_text("⚙️ Панель адміністратора DripZone:", reply_markup=keyboard)
  await callback.answer()


async def main():
  keep_alive()
  print("Бот та Flask-сервер успішно запущено!")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
