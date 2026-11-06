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
        price TEXT
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
        user_id INTEGER PRIMARY KEY
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER
    )
''')
conn.commit()

# 3. Инициализация бота
TOKEN = '8889115088:AAGJ_IO4jvhmXm8g8c2osXmk29iCbW_ACVo'
bot = Bot(token=TOKEN)
dp = Dispatcher()


class AdminState(StatesGroup):
  waiting_for_category = State()
  waiting_for_name = State()
  waiting_for_price = State()


def get_main_keyboard():
  return ReplyKeyboardMarkup(
      keyboard=[
          [KeyboardButton(text='🔥 Каталог брендів'), KeyboardButton(text='🛒 Кошик')],
          [
              KeyboardButton(text='💬 Відгуки'),
              KeyboardButton(text='💬 Зв\'язок з менеджером'),
          ],
          [
              KeyboardButton(text='📊 Статистика'),
              KeyboardButton(text='⚙️ Адмін панель'),
          ],
      ],
      resize_keyboard=True,
  )


@dp.message(Command('start'))
async def send_welcome(message: types.Message):
  cursor.execute(
      'INSERT OR IGNORE INTO users (user_id) VALUES (?)',
      (message.from_user.id,),
  )
  conn.commit()

  await message.answer(
      'Вітаю у DRIPZONE Shop! Вибери потрібний розділ нижче:',
      reply_markup=get_main_keyboard(),
  )


@dp.message(F.text == '🔥 Каталог брендів')
async def show_categories(message: types.Message):
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
  await message.answer(
      '📁 Вибери категорію одягу чи аксесуарів:', reply_markup=kb
  )


@dp.callback_query(F.data.startswith('cat_'))
async def show_products_by_category(callback: types.CallbackQuery):
  await callback.answer()
  category = callback.data.split('_', 1)[1]
  cursor.execute(
      'SELECT id, name, price FROM products WHERE category = ?', (category,)
  )
  products = cursor.fetchall()

  if not products:
    await callback.message.answer(
        f'📦 У категорії "{category}" поки немає товарів.'
    )
  else:
    await callback.message.answer(
        f'📦 Товари у категорії **{category}**:', parse_mode='Markdown'
    )
    for p in products:
      kb = InlineKeyboardMarkup(
          inline_keyboard=[
              [
                  InlineKeyboardButton(
                      text='🛒 Додати в кошик', callback_data=f'buy_{p[0]}'
                  )
              ]
          ]
      )
      await callback.message.answer(
          f'🔸 **{p[1]}**\n💵 Ціна: {p[2]}',
          reply_markup=kb,
          parse_mode='Markdown',
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
    await callback.answer(f'Товар "{product[0]}" додано до кошика! ✅', show_alert=True)
  else:
    await callback.answer('Товар не знайдено!', show_alert=True)


@dp.message(F.text == '🛒 Кошик')
async def show_cart(message: types.Message):
  cursor.execute(
      'SELECT product_name, price FROM cart WHERE user_id = ?',
      (message.from_user.id,),
  )
  items = cursor.fetchall()

  if not items:
    await message.answer('🛒 Ваш кошик порожній.')
  else:
    text = '🛒 **Ваш кошик:**\n\n'
    for item in items:
      text += f'• {item[0]} — {item[1]}\n'

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='🚀 Оформити замовлення', callback_data='checkout'
                )
            ],
            [
                InlineKeyboardButton(
                    text='🗑 Очистити кошик', callback_data='clear_cart'
                )
            ],
        ]
    )
    await message.answer(text, reply_markup=kb, parse_mode='Markdown')


@dp.callback_query(F.data == 'clear_cart')
async def cb_clear_cart(callback: types.CallbackQuery):
  await callback.answer('Кошик очищено')
  cursor.execute('DELETE FROM cart WHERE user_id = ?', (callback.from_user.id,))
  conn.commit()
  await callback.message.answer('🗑 Ваш кошик очищено.')


@dp.callback_query(F.data == 'checkout')
async def cb_checkout(callback: types.CallbackQuery):
  await callback.answer('Замовлення оформлено')
  cursor.execute(
      'INSERT INTO orders (user_id) VALUES (?)', (callback.from_user.id,)
  )
  cursor.execute('DELETE FROM cart WHERE user_id = ?', (callback.from_user.id,))
  conn.commit()
  await callback.message.answer(
      '✅ Дякуємо за замовлення! Менеджер скоро зв\'яжеться з вами.'
  )


@dp.message(F.text == '💬 Відгуки')
async def show_reviews(message: types.Message):
  reviews_kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text='💬 Перейти до відгуків', url='https://t.me/dripproe'
              )
          ]
      ]
  )
  await message.answer(
      '💬 Натисни кнопку нижче, щоб переглянути відгуки наших покупців:',
      reply_markup=reviews_kb,
  )


@dp.message(F.text == '💬 Зв\'язок з менеджером')
async def show_manager(message: types.Message):
  await message.answer('📱 З усіх питань пиши нашому менеджеру: @Armenhik_gang')


@dp.message(F.text == '📊 Статистика')
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


@dp.message(F.text == '⚙️ Адмін панель')
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
  await message.answer(
      '⚙️ **Панель адміністратора:**', reply_markup=kb, parse_mode='Markdown'
  )


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
      f'Вибрано категорію: **{category}**\nВведи назву товару:',
      parse_mode='Markdown',
  )
  await state.set_state(AdminState.waiting_for_name)


@dp.message(AdminState.waiting_for_name)
async def process_product_name(message: types.Message, state: FSMContext):
  await state.update_data(name=message.text)
  await message.answer('Тепер введи ціну товару (наприклад, 1200 грн):')
  await state.set_state(AdminState.waiting_for_price)


@dp.message(AdminState.waiting_for_price)
async def process_product_price(message: types.Message, state: FSMContext):
  data = await state.get_data()
  category = data.get('category')
  name = data.get('name')
  price = message.text

  cursor.execute(
      'INSERT INTO products (category, name, price) VALUES (?, ?, ?)',
      (category, name, price),
  )
  conn.commit()

  await state.clear()
  await message.answer(
      f'✅ Товар "{name}" ({category}) за ціною "{price}" успішно додано!',
      reply_markup=get_main_keyboard(),
  )


async def main():
  logging.basicConfig(level=logging.INFO)
  await dp.start_polling(bot)


if __name__ == '__main__':
  asyncio.run(main())
