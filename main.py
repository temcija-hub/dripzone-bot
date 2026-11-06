import logging
import os
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from flask import Flask

# Токен берется из защищенных переменных окружения Render (переменная должна называться BOT_TOKEN)
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Flask для роботи на Render
app = Flask("")


@app.route("/")
def home():
  return "DripZone Bot is online!"


def run_flask():
  app.run(host="0.0.0.0", port=10000)


# --- БАЗА ДАНИХ ТА ТОВАРИ ---
def init_db():
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            name TEXT,
            price TEXT,
            sizes TEXT,
            description TEXT,
            photo_id TEXT,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    """)

  cursor.execute("SELECT COUNT(*) FROM categories")
  if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO categories (name) VALUES ('Худі')")  # 1
    cursor.execute("INSERT INTO categories (name) VALUES ('Штани')")  # 2

    # Усі 4 товари зашиті намертво у базу даних
    default_products = [
        (
            1,
            "DIOR",
            "1950 грн",
            (
                "S:\n Довжина виробу: 67 см\n Плече + рукав: 75 см\n Обхват"
                " грудей: 53 см\n\nM:\n Довжина виробу: 69 см\n Плече +"
                " рукав: 80 см\n Обхват грудей: 55 см"
            ),
            "Матеріал: трьох нить ✅\nЯкість 1:1 оригінал ✅\nДоставка 1-2 дні 📦",
            "",
        ),
        (
            1,
            "Essentials",
            "1950 грн",
            (
                "S:\n Довжина: 68.5 см\n Ширина (напівобхват): 49 см\n Плечі:"
                " 42 см\n Рукав: 23.5 см"
            ),
            (
                "Матеріал: трьох нить ✅\nЯкість 1:1 оригінал"
                " ✅\n\nДоставка 1-2 дні 📦"
            ),
            "",
        ),
        (
            1,
            "Hellstar",
            "2000 грн",
            (
                "S:\n Плечі: 43 см\n Грудь (напівобхват): 40 см\n Рукав: 59"
                " см\n Довжина: 67 см\n\nM:\n Плечі: 45 см\n Грудь"
                " (напівобхват): 42 см\n Рукав: 60 см\n Довжина: 69 см"
            ),
            "Матеріал: Бавовна ✅\nЯкість 1:1 оригінал ✅\n\nДоставка 1-2 дні 📦",
            "",
        ),
        (
            2,
            "GALLERY DEPT",
            "2000 грн",
            (
                "Розмір S:\n Ширина (полупояс): 38 см\n Довжина: 98 см\n\nРозмір"
                " M:\n Ширина (полупояс): 41 см\n Довжина: 101 см"
            ),
            "Материал: хлопок ✅\nКачество 1:1 оригинал ✅\nДоставка 1-2 дня 📦",
            "",
        ),
    ]

    cursor.executemany(
        """
            INSERT INTO products (category_id, name, price, sizes, description, photo_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
        default_products,
    )

  conn.commit()
  conn.close()


# --- КЛАВІАТУРИ ---
def get_main_menu(user_id):
  kb = [[types.InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog")]]
  ADMIN_ID = 2125409043
  if user_id == ADMIN_ID:
    kb.append(
        [types.InlineKeyboardButton(text="⚙️ Адмін-панель", callback_data="admin")]
    )
  return InlineKeyboardMarkup(inline_keyboard=kb)


# --- ОБРОБНИКИ КОМАНД ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
  init_db()
  await message.answer(
      "Вітаємо у **DripZone**! 🔥\nОбирайте стиль у нашому каталозі.",
      reply_markup=get_main_menu(message.from_user.id),
      parse_mode="Markdown",
  )


@dp.callback_query(F.data == "catalog")
async def show_catalog(callback: types.CallbackQuery):
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("SELECT id, name FROM categories")
  categories = cursor.fetchall()
  conn.close()

  kb = []
  for cat_id, cat_name in categories:
    kb.append(
        [
            types.InlineKeyboardButton(
                text=cat_name, callback_data=f"cat_{cat_id}"
            )
        ]
    )
  kb.append(
      [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_home")]
  )

  await callback.message.edit_text(
      "Оберіть категорію:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
  )


@dp.callback_query(F.data == "back_home")
async def back_home(callback: types.CallbackQuery):
  await callback.message.edit_text(
      "Головне меню DripZone:",
      reply_markup=get_main_menu(callback.from_user.id),
  )


@dp.callback_query(F.data.startswith("cat_"))
async def show_products(callback: types.CallbackQuery):
  cat_id = int(callback.data.split("_")[1])
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT id, name, price FROM products WHERE category_id = ?", (cat_id,)
  )
  products = cursor.fetchall()
  conn.close()

  kb = []
  for prod_id, name, price in products:
    kb.append(
        [
            types.InlineKeyboardButton(
                text=f"{name} — {price}", callback_data=f"prod_{prod_id}"
            )
        ]
    )
  kb.append(
      [
          types.InlineKeyboardButton(
              text="⬅️ Назад до категорій", callback_data="catalog"
          )
      ]
  )

  await callback.message.edit_text(
      "Оберіть товар:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
  )


@dp.callback_query(F.data.startswith("prod_"))
async def show_product_card(callback: types.CallbackQuery):
  prod_id = int(callback.data.split("_")[1])
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT name, price, sizes, description, photo_id FROM products WHERE"
      " id = ?",
      (prod_id,),
  )
  product = cursor.fetchone()
  conn.close()

  if not product:
    await callback.answer("Товар не знайдено!", show_alert=True)
    return

  name, price, sizes, description, photo_id = product

  text = (
      f"<b>{name}</b>\n\n"
      f"💰 <b>Ціна:</b> {price}\n"
      f"📏 <b>Розміри:</b>\n{sizes}\n\n"
      f"📝 <b>Опис:</b>\n{description}"
  )

  kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              types.InlineKeyboardButton(
                  text="🛒 Замовити", url="https://t.me/Armenhik_gang"
              )
          ],
          [
              types.InlineKeyboardButton(
                  text="⬅️ До каталогу", callback_data="catalog"
              )
          ],
      ]
  )

  if photo_id:
    await callback.message.answer_photo(
        photo=photo_id, caption=text, reply_markup=kb, parse_mode="HTML"
    )
    try:
      await callback.message.delete()
    except Exception:
      pass
  else:
    await callback.message.edit_text(
        text, reply_markup=kb, parse_mode="HTML"
    )


# --- ЗАПУСК ---
async def main():
  init_db()
  import threading

  t = threading.Thread(target=run_flask)
  t.daemon = True
  t.start()

  await dp.start_polling(bot)


if __name__ == "__main__":
  import asyncio

  asyncio.run(main())
