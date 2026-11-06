import asyncio
import logging
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

# Твой Telegram ID (админ)
ADMIN_ID = 2125409043

router = Router()

CATEGORIES = [
    "Футболки",
    "Худі",
    "Кофти",
    "Штани",
    "Кросівки",
    "Аксесуари",
]


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


# Функция инициализации базы данных (пользователи, товары, заказы)
def init_db():
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  # Таблица товаров
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
  # Таблица пользователей (для статистики)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    """)
  # Таблица заказов (для статистики)
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


# Команда /start с фиксацией пользователя в базе
@router.message(F.text == "/start")
async def cmd_start(message: Message):
  user_id = message.from_user.id

  # Сохраняем уникального пользователя в базу
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute(
      "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,)
  )
  conn.commit()
  conn.close()

  keyboard = get_main_keyboard(user_id)
  await message.answer(
      "Вітаю у магазині DripZone! Оберіть потрібний розділ:", reply_markup=keyboard
  )


# --- КАТАЛОГ С КОЛИЧЕСТВОМ ТОВАРОВ ---
@router.message(F.text == "🛍 Каталог")
async def show_catalog_categories(message: Message):
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()

  keyboard_list = []
  for cat in CATEGORIES:
    # Считаем, сколько товаров в каждой категории
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
      "SELECT id, name, price, sizes, description, photo_id FROM products WHERE"
      " category = ?",
      (category,),
  )
  products = cursor.fetchall()
  conn.close()

  await callback.message.delete()

  if not products:
    await callback.message.answer(
        f"У категорії <b>{category}</b> наразі немає товарів.",
        parse_mode="HTML",
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

    if photo_id:
      await callback.message.answer_photo(
          photo=photo_id, caption=text, parse_mode="HTML"
      )
    else:
      await callback.message.answer(text, parse_mode="HTML")
  await callback.answer()


@router.message(F.text == "🛒 Кошик")
async def show_cart(message: Message):
  # Пример добавления заказа при оформлении (для тестов статистики)
  # Можешь вызывать сохранение в orders, когда пользователь оформляет заказ
  await message.answer(
      "Ваш кошик порожній. (Тут згодом буде оформлення замовлення)"
  )


@router.message(F.text == "📞 Зв'язок з менеджером")
async def contact_manager(message: Message):
  await message.answer(
      "З приводу замовлень звертайтесь до менеджера: @Armenhik_gang"
  )


@router.message(F.text == "⭐ Відгуки")
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


@router.message(F.text == "📏 Розміри")
async def show_sizes(message: Message):
  await message.answer(
      "Таблиця розмірів:\nS - обхват грудей...\nM - ...\nL - ..."
  )


# ================= СЕКЦИЯ АДМИНА: СТАТИСТИКА =================
@router.message(F.text == "📊 Статистика")
async def show_statistics(message: Message):
  if message.from_user.id != ADMIN_ID:
    await message.answer("❌ У вас немає прав.")
    return

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()

  # Считаем количество пользователей
  cursor.execute("SELECT COUNT(*) FROM users")
  total_users = cursor.fetchone()[0]

  # Считаем количество сделанных заказов
  cursor.execute("SELECT COUNT(*) FROM orders")
  total_orders = cursor.fetchone()[0]

  # Считаем общее количество товаров
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


# ================= СЕКЦИЯ АДМИНА: ДОБАВЛЕНИЕ ТОВАРА =================
@router.message(F.text == "➕ Додати товар")
async def start_add_product(message: Message, state: FSMContext):
  if message.from_user.id != ADMIN_ID:
    await message.answer("❌ У вас немає прав.")
    return

  keyboard_list = []
  for cat in CATEGORIES:
    keyboard_list.append(
        [InlineKeyboardButton(text=cat, callback_data=f"addcat_{cat}")]
    )

  keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_list)
  await message.answer(
      "Оберіть категорію для нового товару (або напишіть /cancel для скасування):",
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
  await message.answer("Введіть ціну товару (наприклад: 1500 грн):")


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

  user_id = message.from_user.id
  await message.answer(
      "✅ Товар успішно додано!", reply_markup=get_main_keyboard(user_id)
  )
  await state.clear()


@router.message(AddProduct.photo)
async def process_photo_invalid(message: Message):
  await message.answer("Будь ласка, надішліть саме фото товару.")


# ================= СЕКЦИЯ АДМИНА: УДАЛЕНИЕ ТОВАРА =================
@router.message(F.text == "🗑 Видалити товар")
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


# ================= СЕКЦИЯ АДМИНА: ИЗМЕНЕНИЕ ТОВАРА =================
@router.message(F.text == "✏️ Змінити товар")
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
  await message.answer(
      "Оберіть товар, який хочете змінити:", reply_markup=keyboard
  )


@router.callback_query(F.data.startswith("edit_"))
async def choose_field_to_edit(callback: CallbackQuery, state: FSMContext):
  prod_id = callback.data.split("_")[1]
  await state.update_data(product_id=prod_id)

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text="💵 Змінити ціну", callback_data="field_price")],
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
      "Що саме ви хочете змінити в цьому товарі?", reply_markup=keyboard
  )
  await state.set_state(EditProduct.select_field)
  await callback.answer()


@router.callback_query(
    EditProduct.select_field, F.data.startswith("field_")
)
async def process_field_choice(callback: CallbackQuery, state: FSMContext):
  field = callback.data.split("_")[1]
  await state.update_data(field=field)

  field_names = {
      "price": "нову ціну",
      "sizes": "нові розміри",
      "description": "новий опис",
  }

  await callback.message.edit_text(
      f"Введіть {field_names[field]} для цього товару:"
  )
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

  user_id = message.from_user.id
  await message.answer(
      "✅ Параметр товару успішно оновлено!",
      reply_markup=get_main_keyboard(user_id),
  )
  await state.clear()


# Отмена процесса
@router.message(F.text == "/cancel")
async def cancel_handler(message: Message, state: FSMContext):
  current_state = await state.get_state()
  if current_state is None:
    return
  await state.clear()
  user_id = message.from_user.id
  await message.answer("❌ Дію скасовано.", reply_markup=get_main_keyboard(user_id))


# Запуск бота
async def main():
  init_db()  # Создаем базы данных при старте
  logging.basicConfig(level=logging.INFO)
  bot = Bot(token="ТВОЙ_ТОКЕН_БОТА")
  dp = Dispatcher(storage=MemoryStorage())
  dp.include_router(router)
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
