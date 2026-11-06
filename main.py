import asyncio
import logging
import os
import sqlite3
import threading
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from flask import Flask

# 1. Настройка Flask для Render
app = Flask('')


@app.route('/')
def home():
  return 'Bot is running!'


def run_web():
  port = int(os.environ.get('PORT', 10000))
  app.run(host='0.0.0.0', port=port)


t = threading.Thread(target=run_web)
t.daemon = True
t.start()

# 2. Инициализация БД
conn = sqlite3.connect('dripzone.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        name TEXT,
        description TEXT,
        price TEXT,
        photo_id TEXT
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS cart (
        user_id INTEGER,
        product_id INTEGER,
        product_name TEXT,
        price TEXT
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        lang TEXT DEFAULT 'uk'
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER
    )
''')
conn.commit()

# 3. Безопасная инициализация бота через переменную окружения Render
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
  raise ValueError('Не задан токен бота в переменных окружения BOT_TOKEN!')

bot = Bot(token=TOKEN)
dp = Dispatcher()


class AdminState(StatesGroup):
  waiting_for_category = State()
  waiting_for_photo = State()
  waiting_for_name = State()
  waiting_for_description = State()
  waiting_for_price = State()


texts = {
    'uk': {
        'welcome': (
            'Вітаю у DRIPZONE Shop! Вибери потрібний розділ нижче:'
        ),
        'catalog': '🔥 Каталог брендів',
        'cart': '🛒 Кошик',
        'reviews': '💬 Відгуки',
        'manager': '💬 Зв\'язок з менеджером',
        'stats': '📊 Статистика',
        'admin': '⚙️ Адмін панель',
        'empty_cart': '🛒 Ваш кошик порожній.',
        'cart_title': '🛒 **Ваш кошик:**\n\n',
        'checkout_btn': '🚀 Оформити замовлення',
        'clear_btn': '🗑 Очистити кошик',
        'order_success': (
            '✅ Дякуємо за замовлення! Менеджер скоро зв\'яжеться з вами.'
        ),
        'manager_text': (
            '📱 З усіх питань пиши нашому менеджеру: @Armenhik_gang'
        ),
        'reviews_text': (
            '💬 Натисни кнопку нижче, щоб переглянути відгуки наших покупців:'
        ),
        'reviews_btn': '💬 Перейти до відгуків',
        'empty_cat': '📦 У цій категорії поки немає товарів.',
        'choose_cat': '📁 Вибери категорію одягу чи аксесуарів:',
        'add_cart_btn': '🛒 Додати в кошик',
    },
    'ru': {
        'welcome': (
            'Приветствую в DRIPZONE Shop! Выбери нужный раздел ниже:'
        ),
        'catalog': '🔥 Каталог брендов',
        'cart': '🛒 Корзина',
        'reviews': '💬 Отзывы',
        'manager': '💬 Связь с менеджером',
        'stats': '📊 Статистика',
        'admin': '⚙️ Админ панель',
        'empty_cart': '🛒 Ваша корзина пуста.',
        'cart_title': '🛒 **Ваша корзина:**\n\n',
        'checkout_btn': '🚀 Оформить заказ',
        'clear_btn': '🗑 Очистить корзину',
        'order_success': (
            '✅ Спасибо за заказ! Менеджер скоро свяжется с вами.'
        ),
        'manager_text': '📱 По всем вопросам пиши нашему менеджеру: @Armenhik_gang',
        'reviews_text': (
            '💬 Нажми кнопку ниже, чтобы посмотреть отзывы наших покупателей:'
        ),
        'reviews_btn': '💬 Перейти к отзывам',
        'empty_cat': '📦 В этой категории пока нет товаров.',
        'choose_cat': '📁 Выбери категорию одежды или аксессуаров:',
        'add_cart_btn': '🛒 Добавить в корзину',
    },
}


def get_user_lang(user_id):
  cursor.execute('SELECT lang FROM users WHERE user_id = ?', (user_id,))
  row = cursor.fetchone()
  return row[0] if row else 'uk'


def get_main_keyboard(lang='uk'):
  t = texts[lang]
  return ReplyKeyboardMarkup(
      keyboard=[
          [KeyboardButton(text=t['catalog']), KeyboardButton(text=t['cart'])],
          [KeyboardButton(text=t['reviews']), KeyboardButton(text=t['manager'])],
          [KeyboardButton(text=t['stats']), KeyboardButton(text=t['admin'])],
      ],
      resize_keyboard=True,
  )


def translate_text(text, lang):
  if lang == 'uk':
    return text
  replacements = {
      'Футболки': 'Футболки',
      'Худі': 'Худи',
      'Кофти': 'Кофты',
      'Штани': 'Брюки',
      'Кросівки': 'Кроссовки',
      'Аксесуари': 'Аксессуары',
  }
  for k, v in replacements.items():
    text = text.replace(k, v)
  return text


@dp.message(Command('start'))
async def send_welcome(message: types.Message):
  cursor.execute(
      'INSERT OR IGNORE INTO users (user_id, lang) VALUES (?, ?)',
      (message.from_user.id, 'uk'),
  )
  conn.commit()

  lang_kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text='🇺🇦 Українська', callback_data='lang_uk'
              ),
              InlineKeyboardButton(text='🇷🇺 Русский', callback_data='lang_ru'),
          ]
      ]
  )
  await message.answer(
      'Виберіть мову / Выберите язык:', reply_markup=lang_kb
  )


@dp.callback_query(F.data.startswith('lang_'))
async def set_language(callback: types.CallbackQuery):
  await callback.answer()
  lang = callback.data.split('_')[1]
  cursor.execute(
      'UPDATE users SET lang = ? WHERE user_id = ?',
      (lang, callback.from_user.id),
  )
  conn.commit()
  t = texts[lang]
  await callback.message.answer(
      t['welcome'], reply_markup=get_main_keyboard(lang)
  )


@dp.message(F.text.in_(['🔥 Каталог брендів', '🔥 Каталог брендов']))
async def show_categories(message: types.Message):
  lang = get_user_lang(message.from_user.id)
  t = texts[lang]
  kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text='👕 Футболки', callback_data='cat_Футболки')],
          [InlineKeyboardButton(text='🧥 Худі', callback_data='cat_Худі')],
          [InlineKeyboardButton(text='🧶 Кофти', callback_data='cat_Кофти')],
          [InlineKeyboardButton(text='👖 Штани', callback_data='cat_Штани')],
          [InlineKeyboardButton(text='👟 Кросівки', callback_data='cat_Кросівки')],
          [
              InlineKeyboardButton(
                  text='🧢 Аксесуари', callback_data='cat_Аксесуари'
              )
          ],
      ]
  )
  await message.answer(t['choose_cat'], reply_markup=kb)


@dp.callback_query(F.data.startswith('cat_'))
async def show_products_by_category(callback: types.CallbackQuery):
  await callback.answer()
  lang = get_user_lang(callback.from_user.id)
  t = texts[lang]
  category = callback.data.split('_', 1)[1]

  cursor.execute(
      'SELECT id, name, description, price, photo_id FROM products WHERE'
      ' category = ?',
      (category,),
  )
  products = cursor.fetchall()
  translated_cat = translate_text(category, lang)

  if not products:
    await callback.message.answer(t['empty_cat'])
  else:
    for p in products:
      prod_name = translate_text(p[1], lang)
      prod_desc = translate_text(p[2] or '', lang)
      caption = f'📦 **{prod_name}**\n📝 {prod_desc}\n💵 Ціна: {p[3]}'

      kb = InlineKeyboardMarkup(
          inline_keyboard=[
              [
                  InlineKeyboardButton(
                      text=t['add_cart_btn'], callback_data=f'buy_{p[0]}'
                  )
              ]
          ]
      )
      if p[4]:
        await callback.message.answer_photo(
            photo=p[4], caption=caption, reply_markup=kb, parse_mode='Markdown'
        )
      else:
        await callback.message.answer(
            caption, reply_markup=kb, parse_mode='Markdown'
        )


@dp.callback_query(F.data.startswith('buy_'))
async def cb_buy(callback: types.CallbackQuery):
  product_id = int(callback.data.split('_')[1])
  cursor.execute(
      'SELECT name, price FROM products WHERE id = ?', (product_id,)
  )
  product = cursor.fetchone()

  if product:
    cursor.execute(
        'INSERT INTO cart (user_id, product_id, product_name, price) VALUES'
        ' (?, ?, ?, ?)',
        (callback.from_user.id, product_id, product[0], product[1]),
    )
    conn.commit()
    await callback.answer('Товар додано до кошика! ✅', show_alert=True)
  else:
    await callback.answer('Товар не знайдено!', show_alert=True)


@dp.message(F.text.in_(['🛒 Кошик', '🛒 Корзина']))
async def show_cart(message: types.Message):
  lang = get_user_lang(message.from_user.id)
  t = texts[lang]
  cursor.execute(
      'SELECT product_name, price FROM cart WHERE user_id = ?',
      (message.from_user.id,),
  )
  items = cursor.fetchall()

  if not items:
    await message.answer(t['empty_cart'])
  else:
    text = t['cart_title']
    for item in items:
      p_name = translate_text(item[0], lang)
      text += f'• {p_name} — {item[1]}\n'

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t['checkout_btn'], callback_data='checkout'
                )
            ],
            [
                InlineKeyboardButton(
                    text=t['clear_btn'], callback_data='clear_cart'
                )
            ],
        ]
    )
    await message.answer(text, reply_markup=kb, parse_mode='Markdown')


@dp.callback_query(F.data == 'clear_cart')
async def cb_clear_cart(callback: types.CallbackQuery):
  await callback.answer('Очищено')
  cursor.execute('DELETE FROM cart WHERE user_id = ?', (callback.from_user.id,))
  conn.commit()
  await callback.message.answer('🗑 Кошик очищено.')


@dp.callback_query(F.data == 'checkout')
async def cb_checkout(callback: types.CallbackQuery):
  lang = get_user_lang(callback.from_user.id)
  t = texts[lang]
  await callback.answer('Замовлення оформлено')
  cursor.execute(
      'INSERT INTO orders (user_id) VALUES (?)', (callback.from_user.id,)
  )
  cursor.execute('DELETE FROM cart WHERE user_id = ?', (callback.from_user.id,))
  conn.commit()
  await callback.message.answer(t['order_success'])


@dp.message(F.text.in_(['💬 Відгуки', '💬 Отзывы']))
async def show_reviews(message: types.Message):
  lang = get_user_lang(message.from_user.id)
  t = texts[lang]
  reviews_kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text=t['reviews_btn'], url='https://t.me/dripproe')]
      ]
  )
  await message.answer(t['reviews_text'], reply_markup=reviews_kb)


@dp.message(
    F.text.in_(["💬 Зв'язок з менеджером", '💬 Связь с менеджером'])
)
async def show_manager(message: types.Message):
  lang = get_user_lang(message.from_user.id)
  t = texts[lang]
  await message.answer(t['manager_text'])


@dp.message(F.text.in_(['📊 Статистика', '📊 Статистика']))
async def show_stats(message: types.Message):
  cursor.execute('SELECT COUNT(*) FROM users')
  users_count = cursor.fetchone()[0]
  cursor.execute('SELECT COUNT(*) FROM products')
  products_count = cursor.fetchone()[0]
  cursor.execute('SELECT COUNT(*) FROM orders')
  orders_count = cursor.fetchone()[0]

  stats_text = (
      '📊 **Статистика магазину:**\n\n'
      f'👥 Користувачів у боті: `{users_count}`\n'
      f'📦 Товарів у каталозі: `{products_count}`\n'
      f'🛍 Успішних замовлень: `{orders_count}`'
  )
  await message.answer(stats_text, parse_mode='Markdown')


@dp.message(F.text.in_(['⚙️ Адмін панель', '⚙️ Админ панель']))
async def show_admin(message: types.Message):
  kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text='➕ Додати товар', callback_data='add_product'
              )
          ]
      ]
  )
  await message.answer('⚙️ **Панель адміністратора:**', reply_markup=kb)


@dp.callback_query(F.data == 'add_product')
async def cb_add_product(callback: types.CallbackQuery, state: FSMContext):
  await callback.answer()
  kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text='👕 Футболки', callback_data='setcat_Футболки')],
          [InlineKeyboardButton(text='🧥 Худі', callback_data='setcat_Худі')],
          [InlineKeyboardButton(text='🧶 Кофти', callback_data='setcat_Кофти')],
          [InlineKeyboardButton(text='👖 Штани', callback_data='setcat_Штани')],
          [InlineKeyboardButton(text='👟 Кросівки', callback_data='setcat_Кросівки')],
          [
              InlineKeyboardButton(
                  text='🧢 Аксесуари', callback_data='setcat_Аксесуари'
              )
          ],
      ]
  )
  await callback.message.answer(
      'Вибери категорію для нового товару:', reply_markup=kb
  )


@dp.callback_query(F.data.startswith('setcat_'))
async def process_category(callback: types.CallbackQuery, state: FSMContext):
  await callback.answer()
  category = callback.data.split('_', 1)[1]
  await state.update_data(category=category)
  await callback.message.answer(
      f'Категорія: **{category}**.\nНадішли **фотографію** товару:'
  )
  await state.set_state(AdminState.waiting_for_photo)


@dp.message(AdminState.waiting_for_photo, F.photo)
async def process_product_photo(message: types.Message, state: FSMContext):
  photo_id = message.photo[-1].file_id
  await state.update_data(photo_id=photo_id)
  await message.answer('Тепер введи **назву** товару:')
  await state.set_state(AdminState.waiting_for_name)


@dp.message(AdminState.waiting_for_name)
async def process_product_name(message: types.Message, state: FSMContext):
  await state.update_data(name=message.text)
  await message.answer('Тепер введи **опис** товару (матеріали, деталі тощо):')
  await state.set_state(AdminState.waiting_for_description)


@dp.message(AdminState.waiting_for_description)
async def process_product_desc(message: types.Message, state: FSMContext):
  await state.update_data(description=message.text)
  await message.answer('Тепер введи **ціну** товару (наприклад, 1200 грн):')
  await state.set_state(AdminState.waiting_for_price)


@dp.message(AdminState.waiting_for_price)
async def process_product_price(message: types.Message, state: FSMContext):
  data = await state.get_data()
  category = data.get('category')
  photo_id = data.get('photo_id')
  name = data.get('name')
  description = data.get('description')
  price = message.text

  cursor.execute(
      'INSERT INTO products (category, name, description, price, photo_id)'
      ' VALUES (?, ?, ?, ?, ?)',
      (category, name, description, price, photo_id),
  )
  conn.commit()

  await state.clear()
  await message.answer('✅ Товар успішно додано з фото та описом!')


async def main():
  logging.basicConfig(level=logging.INFO)
  await dp.start_polling(bot)


if __name__ == '__main__':
  asyncio.run(main())
