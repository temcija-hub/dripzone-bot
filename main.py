import asyncio
import logging
import os
import sqlite3
from aiogram import Bot, Dispatcher, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

# Твій Telegram ID (адмін)
ADMIN_ID = 2125409043

router = Router()

CATEGORIES_UA = ["Футболки", "Худі", "Кофти", "Штани", "Кросівки", "Аксесуари"]


class AddProduct(StatesGroup):
  category = State()
  name = State()
  price = State()
  sizes = State()
  description = State()
  photo = State()


class EditProduct(StatesGroup):
  select_product_id = State()
  select_field = State()
  new_value = State()


def init_db():
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            name TEXT,
            price TEXT,
            sizes TEXT,
            description TEXT,
            photo_id TEXT
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            user_id INTEGER,
            product_id INTEGER
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            total_price TEXT
        )
    """)
  conn.commit()
  conn.close()


def get_main_keyboard(user_id: int):
  keyboard = [
      [KeyboardButton(text="🛍 Каталог"), KeyboardButton(text="🛒 Кошик")],
      [
          KeyboardButton(text="📞 Зв'язок з менеджером"),
          KeyboardButton(text="⭐ Відгуки"),
      ],
      [KeyboardButton(text="📏 Розміри")],
  ]
  if user_id == ADMIN_ID:
    keyboard.append([KeyboardButton(text="➕ Додати товар")])
    keyboard.append(
        [
            KeyboardButton(text="✏️ Змінити товар"),
            KeyboardButton(text="🗑 Видалити товар"),
        ]
    )
    keyboard.append([KeyboardButton(text="📊 Статистика")])

  return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


@router.message(F.text == "/start")
async def cmd_start(message: Message):
  user_id = message.from_user.id

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
  conn.commit()
  conn.close()

  keyboard = get_main_keyboard(user_id)
  await message.answer(
      "Вітаю у магазині DripZone! Головне меню:", reply_markup=keyboard
  )


@router.message(F.text.in_(["🛍 Каталог"]))
async def show_catalog_categories(message: Message):
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()

  keyboard_list = []
  for cat in CATEGORIES_UA:
    cursor.execute(
        "SELECT COUNT(*) FROM products WHERE category = ?", (cat,)
    )
    count = cursor.fetchone()[0]
    keyboard_list.append([
        InlineKeyboardButton(
            text=f"{cat} ({count})", callback_data=f"cat_{cat}"
        )
    ])

  conn.close()
  keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_list)
  await message.answer("Оберіть категорію товарів:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("cat_"))
async def show_products_by_category(callback: CallbackQuery):
  category = callback.data.split("_", 1)[1]

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        SELECT id, name, price, sizes, description, photo_id 
        FROM products WHERE category = ?
    """,
      (category,),
  )
  products = cursor.fetchall()
  conn.close()

  await callback.message.delete()

  if not products:
    await callback.message.answer(
        f"У категорії <b>{category}</b> наразі немає товарів.", parse_mode="HTML"
    )
    return

  await callback.message.answer(
      f"📦 Товари в категорії <b>{category}</b>:", parse_mode="HTML"
  )

  for prod in products:
    prod_id, name, price, sizes, description, photo_id = prod

    text = (
        f"🆔 <b>ID товару:</b> {prod_id}\n"
        f"🏷 <b>{name}</b>\n"
        f"💵 Ціна: {price}\n"
        f"📏 Розміри: {sizes}\n"
        f"📝 Опис: {description}"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Додати в кошик", callback_data=f"buy_{prod_id}"
                )
            ]
        ]
    )

    if photo_id:
      await callback.message.answer_photo(
          photo=photo_id, caption=text, parse_mode="HTML", reply_markup=kb
      )
    else:
      await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
  await callback.answer()


@router.callback_query(F.data.startswith("buy_"))
async def add_to_cart(callback: CallbackQuery):
  prod_id = callback.data.split("_")[1]
  user_id = callback.from_user.id

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO cart (user_id, product_id) VALUES (?, ?)", (user_id, prod_id)
  )
  conn.commit()
  conn.close()

  await callback.answer("✅ Товар додано до кошику!", show_alert=True)


@router.message(F.text.in_(["🛒 Кошик"]))
async def show_cart(message: Message):
  user_id = message.from_user.id

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        SELECT products.id, products.name, products.price 
        FROM cart 
        JOIN products ON cart.product_id = products.id 
        WHERE cart.user_id = ?
    """,
      (user_id,),
  )
  items = cursor.fetchall()
  conn.close()

  if not items:
    await message.answer("Ваш кошик порожній 🛒")
    return

  text = "🛒 <b>Ваш кошик:</b>\n\n"
  for item in items:
    text += f"▪️ {item[1]} — <b>{item[2]}</b>\n"

  kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="📦 Оформити замовлення", callback_data="checkout"
              )
          ],
          [
              InlineKeyboardButton(
                  text="🗑 Очистити кошик", callback_data="clear_cart"
              )
          ],
      ]
  )

  await message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "clear_cart")
async def clear_cart(callback: CallbackQuery):
  user_id = callback.from_user.id

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
  conn.commit()
  conn.close()

  await callback.message.edit_text("🗑 Кошик очищено!")
  await callback.answer()


@router.callback_query(F.data == "checkout")
async def checkout_order(callback: CallbackQuery):
  user_id = callback.from_user.id
  username = callback.from_user.username
  name = callback.from_user.full_name

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        SELECT products.name, products.price 
        FROM cart 
        JOIN products ON cart.product_id = products.id 
        WHERE cart.user_id = ?
    """,
      (user_id,),
  )
  items = cursor.fetchall()

  cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
  cursor.execute(
      "INSERT INTO orders (user_id, total_price) VALUES (?, ?)",
      (user_id, "Оформлено"),
  )
  conn.commit()
  conn.close()

  if not items:
    await callback.answer("Кошик порожній!", show_alert=True)
    return

  order_text = f"🚨 <b>Нове замовлення!</b>\n\nВід: {name} (@{username}, ID: <code>{user_id}</code>)\n\n"
  for item in items:
    order_text += f"▪️ {item[1]} — {item[2]}\n"

  try:
    await callback.bot.send_message(ADMIN_ID, order_text, parse_mode="HTML")
  except Exception as e:
    print(f"Не удалось отправить заказ админу: {e}")

  await callback.message.edit_text(
      "✅ Замовлення успішно оформлено! Менеджер зв'яжеться з вами найближчим"
      " часом."
  )
  await callback.answer()


@router.message(F.text.in_(["📞 Зв'язок з менеджером"]))
async def contact_manager(message: Message):
  await message.answer(
      "З приводу замовлень звертайтесь до менеджера: @Armenhik_gang"
  )


@router.message(F.text.in_(["⭐ Відгуки"]))
async def show_reviews(message: Message):
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="💬 Перейти до каналу з відгуками",
                  url="https://t.me/dripproe",
              )
          ]
      ]
  )
  await message.answer(
      "Переглянути реальні відгуки наших покупців можна у нашому каналі:",
      reply_markup=keyboard,
  )


@router.message(F.text.in_(["📏 Розміри"]))
async def show_sizes(message: Message):
  text = (
      "📐 <b>Таблиця розмірів:</b>\n\n"
      "<b>Штани:</b>\n"
      "• Розмір S: ширина (напівпояс) — 38 см, довжина — 98 см\n"
      "• Розмір M: ширина (напівпояс) — 41 см, довжина — 101 см\n\n"
      "Матеріал: бавовна ✅\n"
      "Якість 1:1 оригінал ✅\n\n"
      "Доставка 1-2 дні 📦"
  )
  await message.answer(text, parse_mode="HTML")


@router.message(F.text.in_(["📊 Статистика"]))
async def show_statistics(message: Message):
  if message.from_user.id != ADMIN_ID:
    await message.answer("❌ У вас немає прав.")
    return

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()

  cursor.execute("SELECT COUNT(*) FROM users")
  total_users = cursor.fetchone()[0]

  cursor.execute("SELECT COUNT(*) FROM orders")
  total_orders = cursor.fetchone()[0]

  cursor.execute("SELECT COUNT(*) FROM products")
  total_products = cursor.fetchone()[0]

  cursor.execute("SELECT id, name, category, price FROM products")
  products = cursor.fetchall()
  conn.close()

  stats_text = (
      f"📊 <b>Статистика магазину DripZone:</b>\n\n"
      f"👥 <b>Користувачів у боті:</b> {total_users}\n"
      f"🛒 <b>Зроблено замовлень:</b> {total_orders}\n"
      f"📦 <b>Всього товарів у базі:</b> {total_products}\n\n"
  )

  if products:
    stats_text += "<b>Список товарів:</b>\n"
    for prod_id, name, cat, price in products:
      stats_text += f"• ID {prod_id} [{cat}]: {name} — {price}\n"
  else:
    stats_text += "<i>Каталог поки порожній.</i>"

  await message.answer(stats_text, parse_mode="HTML")


# ================= ДОДАВАННЯ ТОВАРУ (АДМІН) =================
@router.message(F.text.in_(["➕ Додати товар"]))
async def start_add_product(message: Message, state: FSMContext):
  if message.from_user.id != ADMIN_ID:
    await message.answer("❌ У вас немає прав.")
    return

  keyboard_list = []
  for cat in CATEGORIES_UA:
    keyboard_list.append(
        [InlineKeyboardButton(text=cat, callback_data=f"addcat_{cat}")]
    )

  keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_list)
  await message.answer(
      "Оберіть категорію для нового товару (або напишіть /cancel для"
      " скасування):",
      reply_markup=keyboard,
  )
  await state.set_state(AddProduct.category)


@router.callback_query(AddProduct.category, F.data.startswith("addcat_"))
async def process_category_choice(callback: CallbackQuery, state: FSMContext):
  category = callback.data.split("_", 1)[1]
  await state.update_data(category=category)

  await callback.message.edit_text(
      f"Обрано категорію: <b>{category}</b>\n\nВведіть назву товару:",
      parse_mode="HTML",
  )
  await state.set_state(AddProduct.name)
  await callback.answer()


@router.message(AddProduct.name)
async def process_name(message: Message, state: FSMContext):
  await state.update_data(name=message.text)
  await state.set_state(AddProduct.price)
  await message.answer("Введіть ціну товару (наприклад: 2100 грн):")


@router.message(AddProduct.price)
async def process_price(message: Message, state: FSMContext):
  await state.update_data(price=message.text)
  await state.set_state(AddProduct.sizes)
  await message.answer("Введіть доступні розміри (наприклад: S, M, L, XL):")


@router.message(AddProduct.sizes)
async def process_sizes(message: Message, state: FSMContext):
  await state.update_data(sizes=message.text)
  await state.set_state(AddProduct.description)
  await message.answer("Введіть опис товару:")


@router.message(AddProduct.description)
async def process_description(message: Message, state: FSMContext):
  await state.update_data(description=message.text)
  await state.set_state(AddProduct.photo)
  await message.answer("Надішліть фото товару:")


@router.message(AddProduct.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
  photo_id = message.photo[-1].file_id
  data = await state.get_data()

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT INTO products (category, name, price, sizes, description, photo_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
      (
          data["category"],
          data["name"],
          data["price"],
          data["sizes"],
          data["description"],
          photo_id,
      ),
  )
  conn.commit()
  conn.close()

  await message.answer(
      "✅ Товар успішно додано!", reply_markup=get_main_keyboard(message.from_user.id)
  )
  await state.clear()


@router.message(AddProduct.photo)
async def process_photo_invalid(message: Message):
  await message.answer("Будь ласка, надішліть саме фото товару.")


@router.message(F.text.in_(["🗑 Видалити товар"]))
async def start_delete_product(message: Message):
  if message.from_user.id != ADMIN_ID:
    await message.answer("❌ У вас немає прав.")
    return

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("SELECT id, name, category FROM products")
  products = cursor.fetchall()
  conn.close()

  if not products:
    await message.answer("В базі немає товарів для видалення.")
    return

  keyboard_list = []
  for prod_id, name, cat in products:
    keyboard_list.append([
        InlineKeyboardButton(
            text=f"🗑 [{cat}] {name} (ID: {prod_id})",
            callback_data=f"del_{prod_id}",
        )
    ])

  keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_list)
  await message.answer("Оберіть товар для видалення:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("del_"))
async def process_delete_callback(callback: CallbackQuery):
  prod_id = callback.data.split("_")[1]

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
  conn.commit()
  conn.close()

  await callback.message.edit_text(
      f"✅ Товар з ID {prod_id} успішно видалено з бази!"
  )
  await callback.answer()


@router.message(F.text.in_(["✏️ Змінити товар"]))
async def start_edit_product(message: Message, state: FSMContext):
  if message.from_user.id != ADMIN_ID:
    await message.answer("❌ У вас немає прав.")
    return

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("SELECT id, name, category FROM products")
  products = cursor.fetchall()
  conn.close()

  if not products:
    await message.answer("В базі немає товарів для редагування.")
    return

  keyboard_list = []
  for prod_id, name, cat in products:
    keyboard_list.append([
        InlineKeyboardButton(
            text=f"✏️ [{cat}] {name} (ID: {prod_id})",
            callback_data=f"edit_{prod_id}",
        )
    ])

  keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_list)
  await message.answer("Оберіть товар, який хочете змінити:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("edit_"))
async def choose_field_to_edit(callback: CallbackQuery, state: FSMContext):
  prod_id = callback.data.split("_")[1]
  await state.update_data(product_id=prod_id)

  kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="💵 Змінити ціну", callback_data="field_price"
              )
          ],
          [
              InlineKeyboardButton(
                  text="📏 Змінити розміри", callback_data="field_sizes"
              )
          ],
          [
              InlineKeyboardButton(
                  text="📝 Змінити опис", callback_data="field_description"
              )
          ],
      ]
  )
  await callback.message.edit_text(
      "Що саме ви хочете змінити в цьому товарі?", reply_markup=kb
  )
  await state.set_state(EditProduct.select_field)
  await callback.answer()


@router.callback_query(
    EditProduct.select_field, F.data.startswith("field_")
)
async def process_field_choice(callback: CallbackQuery, state: FSMContext):
  field = callback.data.split("_")[1]
  await state.update_data(field=field)

  if field == "description":
    msg = "Введіть новий опис:"
  elif field == "price":
    msg = "Введіть нову ціну:"
  else:
    msg = "Введіть нові розміри:"

  await callback.message.edit_text(msg, parse_mode="HTML")
  await state.set_state(EditProduct.new_value)
  await callback.answer()


@router.message(EditProduct.new_value)
async def save_new_field_value(message: Message, state: FSMContext):
  data = await state.get_data()
  prod_id = data["product_id"]
  field = data["field"]
  new_value = message.text

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  query = f"UPDATE products SET {field} = ? WHERE id = ?"
  cursor.execute(query, (new_value, prod_id))
  conn.commit()
  conn.close()

  await message.answer(
      "✅ Параметр товару успішно оновлено!",
      reply_markup=get_main_keyboard(message.from_user.id),
  )
  await state.clear()


@router.message(F.text == "/cancel")
async def cancel_handler(message: Message, state: FSMContext):
  current_state = await state.get_state()
  if current_state is None:
    return
  await state.clear()
  await message.answer(
      "❌ Дію скасовано.", reply_markup=get_main_keyboard(message.from_user.id)
  )


# --- Flask для Render ---
from flask import Flask
import threading

app = Flask(__name__)


@app.route("/")
def index():
  return "DripZone Bot is running!"


def run_flask():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


async def main():
  init_db()
  logging.basicConfig(level=logging.INFO)

  flask_thread = threading.Thread(target=run_flask)
  flask_thread.daemon = True
  flask_thread.start()

  TOKEN = os.environ.get("BOT_TOKEN")
  bot = Bot(token=TOKEN)
  dp = Dispatcher(storage=MemoryStorage())
  dp.include_router(router)

  print("Бот і Flask успішно запущені!")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
