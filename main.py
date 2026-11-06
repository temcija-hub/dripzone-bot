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

CATEGORIES_UA = ["Футболки", "Худі", "Кофти", "Штани", "Кросівки", "Аксесуари"]
CATEGORIES_RU = ["Футболки", "Худи", "Кофты", "Брюки", "Кроссовки", "Аксессуары"]


class AddProduct(StatesGroup):
  category = State()
  name = State()
  price = State()
  sizes = State()
  desc_ua = State()
  desc_ru = State()
  photo = State()


class EditProduct(StatesGroup):
  select_product_id = State()
  select_field = State()
  new_value = State()


def init_db():
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  # Название одно (английское), а описания два (desc_ua, desc_ru)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            name TEXT,
            price TEXT,
            sizes TEXT,
            desc_ua TEXT,
            desc_ru TEXT,
            photo_id TEXT
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            lang TEXT DEFAULT 'uk'
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


def get_user_lang(user_id: int):
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
  row = cursor.fetchone()
  conn.close()
  return row[0] if row else "uk"


def get_main_keyboard(user_id: int):
  lang = get_user_lang(user_id)

  if lang == "ru":
    keyboard = [
        [KeyboardButton(text="🛍 Каталог"), KeyboardButton(text="🛒 Корзина")],
        [
            KeyboardButton(text="📞 Связь с менеджером"),
            KeyboardButton(text="⭐ Отзывы"),
        ],
        [KeyboardButton(text="📏 Размеры")],
    ]
    if user_id == ADMIN_ID:
      keyboard.append([KeyboardButton(text="➕ Добавить товар")])
      keyboard.append(
          [
              KeyboardButton(text="✏️ Изменить товар"),
              KeyboardButton(text="🗑 Удалить товар"),
          ]
      )
      keyboard.append([KeyboardButton(text="📊 Статистика")])
  else:
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
  cursor.execute(
      "INSERT OR IGNORE INTO users (user_id, lang) VALUES (?, 'uk')", (user_id,)
  )
  conn.commit()
  conn.close()

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="🇺🇦 Українська", callback_data="setlang_uk"
              ),
              InlineKeyboardButton(
                  text="🇷🇺 Русский", callback_data="setlang_ru"
              ),
          ]
      ]
  )
  await message.answer(
      "Оберіть мову / Выберите язык:", reply_markup=keyboard
  )


@router.callback_query(F.data.startswith("setlang_"))
async def process_language_choice(callback: CallbackQuery):
  user_id = callback.from_user.id
  lang = callback.data.split("_")[1]

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
  conn.commit()
  conn.close()

  await callback.message.delete()
  keyboard = get_main_keyboard(user_id)

  text = (
      "Язык успешно изменен на русский! Добро пожаловать в магазин DripZone!"
      if lang == "ru"
      else "Мову успішно змінено на українську! Вітаю у магазині DripZone!"
  )
  await callback.message.answer(text, reply_markup=keyboard)
  await callback.answer()


@router.message(F.text.in_(["🛍 Каталог"]))
async def show_catalog_categories(message: Message):
  user_id = message.from_user.id
  lang = get_user_lang(user_id)
  categories = CATEGORIES_RU if lang == "ru" else CATEGORIES_UA

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()

  keyboard_list = []
  for cat in categories:
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

  text = (
      "Выберите категорию товаров:"
      if lang == "ru"
      else "Оберіть категорію товарів:"
  )
  await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("cat_"))
async def show_products_by_category(callback: CallbackQuery):
  category = callback.data.split("_", 1)[1]
  user_id = callback.from_user.id
  lang = get_user_lang(user_id)

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        SELECT id, name, price, sizes, desc_ua, desc_ru, photo_id 
        FROM products WHERE category = ?
    """,
      (category,),
  )
  products = cursor.fetchall()
  conn.close()

  await callback.message.delete()

  if not products:
    msg = (
        f"В категории <b>{category}</b> пока нет товаров."
        if lang == "ru"
        else f"У категорії <b>{category}</b> наразі немає товарів."
    )
    await callback.message.answer(msg, parse_mode="HTML")
    return

  header = (
      f"📦 Товары в категории <b>{category}</b>:"
      if lang == "ru"
      else f"📦 Товари в категорії <b>{category}</b>:"
  )
  await callback.message.answer(header, parse_mode="HTML")

  for prod in products:
    prod_id, name, price, sizes, desc_ua, desc_ru, photo_id = prod
    description = desc_ru if lang == "ru" else desc_ua

    if lang == "ru":
      text = (
          f"🆔 <b>ID товара:</b> {prod_id}\n"
          f"🏷 <b>{name}</b>\n"
          f"💵 Цена: {price}\n"
          f"📏 Размеры: {sizes}\n"
          f"📝 Описание: {description}"
      )
    else:
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


@router.message(F.text.in_(["🛒 Кошик", "🛒 Корзина"]))
async def show_cart(message: Message):
  user_id = message.from_user.id
  lang = get_user_lang(user_id)
  text = (
      "Ваша корзина пуста." if lang == "ru" else "Ваш кошик порожній."
  )
  await message.answer(text)


@router.message(F.text.in_(["📞 Зв'язок з менеджером", "📞 Связь с менеджером"]))
async def contact_manager(message: Message):
  user_id = message.from_user.id
  lang = get_user_lang(user_id)
  text = (
      "По поводу заказов обращайтесь к менеджеру: @Armenhik_gang"
      if lang == "ru"
      else "З приводу замовлень звертайтесь до менеджера: @Armenhik_gang"
  )
  await message.answer(text)


@router.message(F.text.in_(["⭐ Відгуки", "⭐ Отзывы"]))
async def show_reviews(message: Message):
  user_id = message.from_user.id
  lang = get_user_lang(user_id)
  btn_text = (
      "💬 Перейти в канал с отзывами"
      if lang == "ru"
      else "💬 Перейти до каналу з відгуками"
  )
  resp_text = (
      "Посмотреть реальные отзывы наших покупателей можно в нашем канале:"
      if lang == "ru"
      else "Переглянути реальні відгуки наших покупців можна у нашому каналі:"
  )

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text=btn_text, url="https://t.me/dripproe")]
      ]
  )
  await message.answer(resp_text, reply_markup=keyboard)


@router.message(F.text.in_(["📏 Розміри", "📏 Размеры"]))
async def show_sizes(message: Message):
  user_id = message.from_user.id
  lang = get_user_lang(user_id)
  text = (
      "Таблица размеров:\nS - ...\nM - ...\nL - ..."
      if lang == "ru"
      else "Таблиця розмірів:\nS - ...\nM - ...\nL - ..."
  )
  await message.answer(text)


@router.message(F.text.in_(["📊 Статистика"]))
async def show_statistics(message: Message):
  if message.from_user.id != ADMIN_ID:
    await message.answer("❌ У вас нет прав.")
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
      f"📊 <b>Статистика магазина DripZone:</b>\n\n"
      f"👥 <b>Пользователей в боте:</b> {total_users}\n"
      f"🛒 <b>Сделано заказов:</b> {total_orders}\n"
      f"📦 <b>Всего товаров в базе:</b> {total_products}\n\n"
  )

  if products:
    stats_text += "<b>Список товаров:</b>\n"
    for prod_id, name, cat, price in products:
      stats_text += f"• ID {prod_id} [{cat}]: {name} — {price}\n"
  else:
    stats_text += "<i>Каталог пока пуст.</i>"

  await message.answer(stats_text, parse_mode="HTML")


# ================= ДОБАВЛЕНИЕ ТОВАРА (АДМИН) =================
@router.message(F.text.in_(["➕ Додати товар", "➕ Добавить товар"]))
async def start_add_product(message: Message, state: FSMContext):
  if message.from_user.id != ADMIN_ID:
    await message.answer("❌ У вас нет прав.")
    return

  keyboard_list = []
  for cat in CATEGORIES_UA:
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
      f"Обрано категорію: <b>{category}</b>\n\nВведіть назву товару (англійською):",
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
  await state.set_state(AddProduct.desc_ua)
  await message.answer("Введіть опис товару <b>українською</b>:", parse_mode="HTML")


@router.message(AddProduct.desc_ua)
async def process_desc_ua(message: Message, state: FSMContext):
  await state.update_data(desc_ua=message.text)
  await state.set_state(AddProduct.desc_ru)
  await message.answer("Введіть опис товару <b>російською</b>:", parse_mode="HTML")


@router.message(AddProduct.desc_ru)
async def process_desc_ru(message: Message, state: FSMContext):
  await state.update_data(desc_ru=message.text)
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
        INSERT INTO products (category, name, price, sizes, desc_ua, desc_ru, photo_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
      (
          data["category"],
          data["name"],
          data["price"],
          data["sizes"],
          data["desc_ua"],
          data["desc_ru"],
          photo_id,
      ),
  )
  conn.commit()
  conn.close()

  user_id = message.from_user.id
  lang = get_user_lang(user_id)
  success_msg = (
      "✅ Товар успешно добавлен!" if lang == "ru" else "✅ Товар успішно додано!"
  )

  await message.answer(
      success_msg, reply_markup=get_main_keyboard(user_id)
  )
  await state.clear()


@router.message(AddProduct.photo)
async def process_photo_invalid(message: Message):
  user_id = message.from_user.id
  lang = get_user_lang(user_id)
  text = (
      "Пожалуйста, отправьте именно фото товара."
      if lang == "ru"
      else "Будь ласка, надішліть саме фото товару."
  )
  await message.answer(text)


@router.message(F.text.in_(["🗑 Видалити товар", "🗑 Удалить товар"]))
async def start_delete_product(message: Message):
  if message.from_user.id != ADMIN_ID:
    await message.answer("❌ У вас нет прав.")
    return

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("SELECT id, name, category FROM products")
  products = cursor.fetchall()
  conn.close()

  user_id = message.from_user.id
  lang = get_user_lang(user_id)

  if not products:
    text = (
        "В базе нет товаров для удаления."
        if lang == "ru"
        else "В базі немає товарів для видалення."
    )
    await message.answer(text)
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
  text = (
      "Выберите товар для удаления:"
      if lang == "ru"
      else "Оберіть товар для видалення:"
  )
  await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("del_"))
async def process_delete_callback(callback: CallbackQuery):
  prod_id = callback.data.split("_")[1]
  user_id = callback.from_user.id
  lang = get_user_lang(user_id)

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
  conn.commit()
  conn.close()

  msg = (
      f"✅ Товар с ID {prod_id} успешно удален из базы!"
      if lang == "ru"
      else f"✅ Товар з ID {prod_id} успішно видалено з бази!"
  )
  await callback.message.edit_text(msg)
  await callback.answer()


@router.message(F.text.in_(["✏️ Змінити товар", "✏️ Изменить товар"]))
async def start_edit_product(message: Message, state: FSMContext):
  if message.from_user.id != ADMIN_ID:
    await message.answer("❌ У вас нет прав.")
    return

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("SELECT id, name, category FROM products")
  products = cursor.fetchall()
  conn.close()

  user_id = message.from_user.id
  lang = get_user_lang(user_id)

  if not products:
    text = (
        "В базе нет товаров для редактирования."
        if lang == "ru"
        else "В базі немає товарів для редагування."
    )
    await message.answer(text)
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
  text = (
      "Выберите товар, который хотите изменить:"
      if lang == "ru"
      else "Оберіть товар, який хочете змінити:"
  )
  await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("edit_"))
async def choose_field_to_edit(callback: CallbackQuery, state: FSMContext):
  prod_id = callback.data.split("_")[1]
  await state.update_data(product_id=prod_id)
  user_id = callback.from_user.id
  lang = get_user_lang(user_id)

  if lang == "ru":
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💵 Изменить цену", callback_data="field_price"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📏 Изменить размеры", callback_data="field_sizes"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 Изменить описание",
                    callback_data="field_description",
                )
            ],
        ]
    )
    msg = "Что именно вы хотите изменить в этом товаре?"
  else:
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
    msg = "Що саме ви хочете змінити в цьому товарі?"

  await callback.message.edit_text(msg, reply_markup=kb)
  await state.set_state(EditProduct.select_field)
  await callback.answer()


@router.callback_query(
    EditProduct.select_field, F.data.startswith("field_")
)
async def process_field_choice(callback: CallbackQuery, state: FSMContext):
  field = callback.data.split("_")[1]
  await state.update_data(field=field)
  user_id = callback.from_user.id
  lang = get_user_lang(user_id)

  if lang == "ru":
    if field == "description":
      msg = "Введите новое описание на <b>украинском</b>:"
    elif field == "price":
      msg = "Введите новую цену:"
    else:
      msg = "Введите новые размеры:"
  else:
    if field == "description":
      msg = "Введіть новий опис <b>українською</b>:"
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

  if field == "description":
    cursor.execute(
        "UPDATE products SET desc_ua = ?, desc_ru = ? WHERE id = ?",
        (new_value, new_value, prod_id),
    )
  else:
    query = f"UPDATE products SET {field} = ? WHERE id = ?"
    cursor.execute(query, (new_value, prod_id))

  conn.commit()
  conn.close()

  user_id = message.from_user.id
  lang = get_user_lang(user_id)
  msg = (
      "✅ Параметр товара успешно обновлен!"
      if lang == "ru"
      else "✅ Параметр товару успішно оновлено!"
  )

  await message.answer(msg, reply_markup=get_main_keyboard(user_id))
  await state.clear()


@router.message(F.text == "/cancel")
async def cancel_handler(message: Message, state: FSMContext):
  current_state = await state.get_state()
  if current_state is None:
    return
  await state.clear()
  user_id = message.from_user.id
  lang = get_user_lang(user_id)
  msg = "❌ Действие отменено." if lang == "ru" else "❌ Дію скасовано."
  await message.answer(msg, reply_markup=get_main_keyboard(user_id))


async def main():
  init_db()
  logging.basicConfig(level=logging.INFO)
  bot = Bot(token="ТВОЙ_ТОКЕН_БОТА")
  dp = Dispatcher(storage=MemoryStorage())
  dp.include_router(router)
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
