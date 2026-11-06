import logging
import os
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from flask import Flask

# Токен берется из защищенных переменных окружения Render
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Flask для работы на Render
app = Flask("")


@app.route("/")
def home():
  return "DripZone Bot is online!"


def run_flask():
  app.run(host="0.0.0.0", port=10000)


# --- СОСТОЯНИЯ ДЛЯ FSM (УПРАВЛЕНИЕ ТОВАРАМИ) ---
class AdminStates(StatesGroup):
  waiting_for_product_name = State()
  waiting_for_category = State()
  waiting_for_price = State()
  waiting_for_sizes = State()
  waiting_for_description = State()
  waiting_for_photo = State()

  edit_new_value = State()


# --- БАЗА ДАННЫХ И ТОВАРЫ ---
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

  # Таблица пользователей для статистики
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    """)

  # Таблица заказов для статистики
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_name TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

  cursor.execute("SELECT COUNT(*) FROM categories")
  if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO categories (name) VALUES ('Худі')")  # 1
    cursor.execute("INSERT INTO categories (name) VALUES ('Штани')")  # 2

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


# --- КНОПКИ ПОД КЛАВИАТУРОЙ (REPLY) ---
def get_reply_keyboard(user_id):
  kb = [
      [KeyboardButton(text="🛍 Каталог"), KeyboardButton(text="🛒 Кошик")],
      [KeyboardButton(text="📦 Розміри"), KeyboardButton(text="⭐ Відгуки")],
      [KeyboardButton(text="📞 Зв'язок з менеджером")],
  ]
  ADMIN_ID = 2125409043
  if user_id == ADMIN_ID:
    kb.append([KeyboardButton(text="⚙️ Адмін-панель")])

  return ReplyKeyboardMarkup(
      keyboard=kb, resize_keyboard=True, input_field_placeholder="Оберіть дію..."
  )


# --- ОБРАБОТЧИКИ КОМАНД И КЛИЕНТСКОЙ ЧАСТИ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
  init_db()
  user_id = message.from_user.id

  # Записываем пользователя в базу для статистики
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute(
      "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,)
  )
  conn.commit()
  conn.close()

  await message.answer(
      "Вітаємо у **DripZone**! 🔥\nОбирайте стиль за допомогою кнопок нижче.",
      reply_markup=get_reply_keyboard(user_id),
      parse_mode="Markdown",
  )


@dp.message(F.text == "🛍 Каталог")
async def btn_catalog(message: types.Message):
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("SELECT id, name FROM categories")
  categories = cursor.fetchall()
  conn.close()

  kb = []
  for cat_id, cat_name in categories:
    kb.append(
        [
            InlineKeyboardButton(
                text=cat_name, callback_data=f"cat_{cat_id}"
            )
        ]
    )

  await message.answer(
      "Оберіть категорію:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
  )


@dp.message(F.text == "🛒 Кошик")
async def btn_cart(message: types.Message):
  await message.answer("Ваш кошик наразі порожній 🛒")


@dp.message(F.text == "📦 Розміри")
async def btn_sizes(message: types.Message):
  await message.answer(
      "📏 Розмірну сітку можно переглянути всередині карток кожного товару"
      " в каталозі."
  )


@dp.message(F.text == "⭐ Відгуки")
async def btn_reviews(message: types.Message):
  await message.answer(
      "⭐ Наші відгуки та репутація: https://t.me/Armenhik_gang"
  )


@dp.message(F.text == "📞 Зв'язок з менеджером")
async def btn_manager(message: types.Message):
  await message.answer(
      "👨‍💻 Зв'язатися з менеджером: https://t.me/Armenhik_gang"
  )


# --- АДМИН-ПАНЕЛЬ ---
@dp.message(F.text == "⚙️ Адмін-панель")
async def admin_panel(message: types.Message):
  ADMIN_ID = 2125409043
  if message.from_user.id != ADMIN_ID:
    return

  kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="📊 Статистика", callback_data="admin_stats"
              )
          ],
          [
              InlineKeyboardButton(
                  text="➕ Додати товар", callback_data="admin_add"
              )
          ],
          [
              InlineKeyboardButton(
                  text="✏️ Редагувати / Видалити товар",
                  callback_data="admin_manage",
              )
          ],
      ]
  )
  await message.answer("⚙️ **Панель адміністратора DripZone:**", reply_markup=kb)


# Кнопка статистики
@dp.callback_query(F.data == "admin_stats")
async def admin_statistics(callback: types.CallbackQuery):
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()

  cursor.execute("SELECT COUNT(*) FROM users")
  users_count = cursor.fetchone()[0]

  cursor.execute("SELECT COUNT(*) FROM products")
  products_count = cursor.fetchone()[0]

  cursor.execute("SELECT COUNT(*) FROM orders")
  orders_count = cursor.fetchone()[0]

  conn.close()

  text = (
      f"📊 <b>Статистика магазину DripZone:</b>\n\n"
      f"👥 Кількість користувачів: <b>{users_count}</b>\n"
      f"📦 Товарів у каталозі: <b>{products_count}</b>\n"
      f"🛒 Замовлень оформлено: <b>{orders_count}</b>"
  )

  kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="⬅️ Назад в адмінку", callback_data="admin_back"
              )
          ]
      ]
  )
  await callback.message.edit_text(
      text, reply_markup=kb, parse_mode="HTML"
  )
  await callback.answer()


@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery):
  kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="📊 Статистика", callback_data="admin_stats"
              )
          ],
          [
              InlineKeyboardButton(
                  text="➕ Додати товар", callback_data="admin_add"
              )
          ],
          [
              InlineKeyboardButton(
                  text="✏️ Редагувати / Видалити товар",
                  callback_data="admin_manage",
              )
          ],
      ]
  )
  await callback.message.edit_text(
      "⚙️ **Панель адміністратора DripZone:**", reply_markup=kb
  )
  await callback.answer()


# Управление товарами (список для изменения/удаления)
@dp.callback_query(F.data == "admin_manage")
async def admin_manage_products(callback: types.CallbackQuery):
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("SELECT id, name, price FROM products")
  products = cursor.fetchall()
  conn.close()

  kb = []
  for prod_id, name, price in products:
    kb.append(
        [
            InlineKeyboardButton(
                text=f"⚙️ {name} ({price})",
                callback_data=f"adm_edit_{prod_id}",
            )
        ]
    )
  kb.append(
      [
          InlineKeyboardButton(
              text="⬅️ Назад в адмінку", callback_data="admin_back"
          )
      ]
  )

  await callback.message.edit_text(
      "Оберіть товар для редагування або видалення:",
      reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
  )
  await callback.answer()


# Меню конкретного товара для админа
@dp.callback_query(F.data.startswith("adm_edit_"))
async def admin_product_options(callback: types.CallbackQuery):
  prod_id = int(callback.data.split("_")[2])
  kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="💰 Змінити ціну", callback_data=f"set_p_{prod_id}"
              ),
              InlineKeyboardButton(
                  text="📏 Змінити розміри", callback_data=f"set_s_{prod_id}"
              ),
          ],
          [
              InlineKeyboardButton(
                  text="📝 Змінити опис", callback_data=f"set_d_{prod_id}"
              )
          ],
          [
              InlineKeyboardButton(
                  text="❌ Видалити товар", callback_data=f"adm_del_{prod_id}"
              )
          ],
          [
              InlineKeyboardButton(
                  text="⬅️ До списку товарів", callback_data="admin_manage"
              )
          ],
      ]
  )
  await callback.message.edit_text(
      "Оберіть, що саме потрібно зробити з цим товаром:", reply_markup=kb
  )
  await callback.answer()


# Удаление товара
@dp.callback_query(F.data.startswith("adm_del_"))
async def admin_delete_product(callback: types.CallbackQuery):
  prod_id = int(callback.data.split("_")[2])
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
  conn.commit()
  conn.close()

  await callback.answer("Товар успішно видалено! ✅", show_alert=True)
  await admin_manage_products(callback)


# Изменение цены, размеров или описания через состояние
@dp.callback_query(F.data.regexp(r"^set_[psd]_\d+$"))
async def admin_start_edit(callback: types.CallbackQuery, state: FSMContext):
  data = callback.data.split("_")
  action = data[1]
  prod_id = int(data[2])

  await state.update_data(edit_prod_id=prod_id, edit_action=action)
  await state.set_state(AdminStates.edit_new_value)

  names = {"p": "нову ціну (наприклад: 2100 грн)", "s": "нові розміри", "d": "новий опис"}
  await callback.message.answer(f"Введіть {names[action]}:")
  await callback.answer()


@dp.message(AdminStates.edit_new_value)
async def admin_save_new_value(message: types.Message, state: FSMContext):
  data = await state.get_data()
  prod_id = data["edit_prod_id"]
  action = data["edit_action"]
  new_value = message.text

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()

  if action == "p":
    cursor.execute("UPDATE products SET price = ? WHERE id = ?", (new_value, prod_id))
  elif action == "s":
    cursor.execute("UPDATE products SET sizes = ? WHERE id = ?", (new_value, prod_id))
  elif action == "d":
    cursor.execute("UPDATE products SET description = ? WHERE id = ?", (new_value, prod_id))

  conn.commit()
  conn.close()

  await state.clear()
  await message.answer("Дані товару успішно оновлено! ✅")


# --- ДОБАВЛЕНИЕ ТОВАРА (ПОШАГОВО) ---
@dp.callback_query(F.data == "admin_add")
async def admin_add_start(callback: types.CallbackQuery, state: FSMContext):
  await state.set_state(AdminStates.waiting_for_product_name)
  await callback.message.answer("Введіть назву нового товару:")
  await callback.answer()


@dp.message(AdminStates.waiting_for_product_name)
async def admin_add_name(message: types.Message, state: FSMContext):
  await state.update_data(name=message.text)
  await state.set_state(AdminStates.waiting_for_category)

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("SELECT id, name FROM categories")
  categories = cursor.fetchall()
  conn.close()

  kb = []
  for cat_id, cat_name in categories:
    kb.append(
        [
            InlineKeyboardButton(
                text=cat_name, callback_data=f"addcat_{cat_id}"
            )
        ]
    )
  await message.answer(
      "Оберіть категорію для товару:",
      reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
  )


@dp.callback_query(F.data.startswith("addcat_"), AdminStates.waiting_for_category)
async def admin_add_category(callback: types.CallbackQuery, state: FSMContext):
  cat_id = int(callback.data.split("_")[1])
  await state.update_data(category_id=cat_id)
  await state.set_state(AdminStates.waiting_for_price)
  await callback.message.answer("Введіть ціну товару (наприклад: 2000 грн):")
  await callback.answer()


@dp.message(AdminStates.waiting_for_price)
async def admin_add_price(message: types.Message, state: FSMContext):
  await state.update_data(price=message.text)
  await state.set_state(AdminStates.waiting_for_sizes)
  await message.answer("Введіть розмірну сітку:")


@dp.message(AdminStates.waiting_for_sizes)
async def admin_add_sizes(message: types.Message, state: FSMContext):
  await state.update_data(sizes=message.text)
  await state.set_state(AdminStates.waiting_for_description)
  await message.answer("Введіть опис товару (матеріал, якість тощо):")


@dp.message(AdminStates.waiting_for_description)
async def admin_add_description(message: types.Message, state: FSMContext):
  await state.update_data(description=message.text)
  await state.set_state(AdminStates.waiting_for_photo)
  await message.answer("Надішліть фотографію товару:")


@dp.message(AdminStates.waiting_for_photo, F.photo)
async def admin_add_photo(message: types.Message, state: FSMContext):
  photo_id = message.photo[-1].file_id
  data = await state.get_data()

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT INTO products (category_id, name, price, sizes, description, photo_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
      (
          data["category_id"],
          data["name"],
          data["price"],
          data["sizes"],
          data["description"],
          photo_id,
      ),
  )
  conn.commit()
  conn.close()

  await state.clear()
  await message.answer("Товар успішно додано до каталогу! 🎉")


# --- КЛИЕНТСКАЯ ЧАСТЬ КАТАЛОГА ---
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
            InlineKeyboardButton(
                text=f"{name} — {price}", callback_data=f"prod_{prod_id}"
            )
        ]
    )
  kb.append(
      [
          InlineKeyboardButton(
              text="⬅️ Назад до категорій", callback_data="catalog"
          )
      ]
  )

  await callback.message.edit_text(
      "Оберіть товар:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
  )
  await callback.answer()


@dp.callback_query(F.data == "catalog")
async def back_to_catalog(callback: types.CallbackQuery):
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("SELECT id, name FROM categories")
  categories = cursor.fetchall()
  conn.close()

  kb = []
  for cat_id, cat_name in categories:
    kb.append(
        [
            InlineKeyboardButton(
                text=cat_name, callback_data=f"cat_{cat_id}"
            )
        ]
    )

  await callback.message.edit_text(
      "Оберіть категорію:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
  )
  await callback.answer()


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

  # Сохраняем имя товара в callback_data кнопки заказа, чтобы засчитать заказ
  kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="🛒 Замовити", callback_data=f"order_{prod_id}"
              )
          ],
          [
              InlineKeyboardButton(
                  text="⬅️ До каталогу", callback_data="catalog"
              )
          ],
      ]
  )

  if photo_id and photo_id != "":
    try:
      await callback.message.answer_photo(
          photo=photo_id, caption=text, reply_markup=kb, parse_mode="HTML"
      )
      await callback.message.delete()
    except Exception:
      await callback.message.answer(
          text, reply_markup=kb, parse_mode="HTML"
      )
  else:
    await callback.message.edit_text(
        text, reply_markup=kb, parse_mode="HTML"
    )
  await callback.answer()


# Фиксация заказа при нажатии на «Замовити»
@dp.callback_query(F.data.startswith("order_"))
async def make_order(callback: types.CallbackQuery):
  prod_id = int(callback.data.split("_")[1])
  user_id = callback.from_user.id

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("SELECT name FROM products WHERE id = ?", (prod_id,))
  prod = cursor.fetchone()

  if prod:
    prod_name = prod[0]
    cursor.execute(
        "INSERT INTO orders (user_id, product_name) VALUES (?, ?)",
        (user_id, prod_name),
    )
    conn.commit()
  conn.close()

  # Отправляем клиенту ссылку на менеджера для оплаты/связи
  await callback.answer(
      "Замовлення прийнято! Переходимо до менеджера... ✅", show_alert=True
  )
  await callback.message.answer(
      "📦 Дякуємо за замовлення!\nДля оформлення та уточнення деталей"
      " зверніться до менеджера: https://t.me/Armenhik_gang"
  )


# --- ЗАПУСК ---
async def main():
  init_db()

  try:
    await bot.delete_my_commands()
  except Exception:
    pass

  import threading

  t = threading.Thread(target=run_flask)
  t.daemon = True
  t.start()

  await dp.start_polling(bot)


if __name__ == "__main__":
  import asyncio

  asyncio.run(main())
