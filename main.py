import asyncio
import logging
import os
import sqlite3
import threading
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
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
conn.commit()

# 3. Инициализация бота
TOKEN = '8889115088:AAGJ_IO4jvhmXm8g8c2osXmk29iCbW_ACVo'
bot = Bot(token=TOKEN)
dp = Dispatcher()


class AdminState(StatesGroup):
  waiting_for_name = State()
  waiting_for_price = State()


# Постоянная клавиатура снизу
def get_main_keyboard():
  return ReplyKeyboardMarkup(
      keyboard=[
          [KeyboardButton(text='📦 Каталог'), KeyboardButton(text='🛒 Кошик')],
          [KeyboardButton(text='💬 Відгуки'), KeyboardButton(text='📏 Розміри')],
          [
              KeyboardButton(text='📊 Статистика'),
              KeyboardButton(text='⚙️ Адмін панель'),
          ],
      ],
      resize_keyboard=True,
  )


@dp.message(Command('start'))
async def send_welcome(message: types.Message):
  await message.answer(
      'Вітаю у DRIPZONE Shop! Вибери потрібний розділ нижче:',
      reply_markup=get_main_keyboard(),
  )


@dp.message(F.text == '📦 Каталог')
async def show_catalog(message: types.Message):
  cursor.execute('SELECT id, name, price FROM products')
  products = cursor.fetchall()
  if not products:
    await message.answer(
        '📦 Каталог наразі порожній.\nАдмін може додати товари через панель.'
    )
  else:
    for p in products:
      kb = types.InlineKeyboardMarkup(
          inline_keyboard=[
              [
                  types.InlineKeyboardButton(
                      text='🛒 Додати в кошик', callback_data=f'buy_{p[0]}'
                  )
              ]
          ]
      )
      await message.answer(
          f'📦 **{p[1]}**\n💵 Ціна: {p[2]}',
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

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text='🚀 Оформити замовлення', callback_data='checkout'
                )
            ],
            [
                types.InlineKeyboardButton(
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
  cursor.execute('DELETE FROM cart WHERE user_id = ?', (callback.from_user.id,))
  conn.commit()
  await callback.message.answer(
      '✅ Дякуємо за замовлення! Менеджер скоро зв\'яжеться з вами.'
  )


@dp.message(F.text == '💬 Відгуки')
async def show_reviews(message: types.Message):
  await message.answer('💬 Відгуки покупців у нашому каналі.')


@dp.message(F.text == '📏 Розміри')
async def show_sizes(message: types.Message):
  await message.answer('📏 Доступні розміри: S, M, L, XL, XXL.')


@dp.message(F.text == '📊 Статистика')
async def show_stats(message: types.Message):
  cursor.execute('SELECT COUNT(*) FROM products')
  count = cursor.fetchone()[0]
  await message.answer(f'📊 Товарів у каталозі: {count}')


@dp.message(F.text == '⚙️ Адмін панель')
async def show_admin(message: types.Message):
  kb = types.InlineKeyboardMarkup(
      inline_keyboard=[
          [
              types.InlineKeyboardButton(
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
  await callback.message.answer('Введи назву нового товару:')
  await state.set_state(AdminState.waiting_for_name)


@dp.message(AdminState.waiting_for_name)
async def process_product_name(message: types.Message, state: FSMContext):
  await state.update_data(name=message.text)
  await message.answer('Тепер введи ціну товару (наприклад, 1200 грн):')
  await state.set_state(AdminState.waiting_for_price)


@dp.message(AdminState.waiting_for_price)
async def process_product_price(message: types.Message, state: FSMContext):
  data = await state.get_data()
  name = data.get('name')
  price = message.text

  cursor.execute(
      'INSERT INTO products (name, price) VALUES (?, ?)', (name, price)
  )
  conn.commit()

  await state.clear()
  await message.answer(
      f'✅ Товар "{name}" за ціною "{price}" успішно додано до каталогу!',
      reply_markup=get_main_keyboard(),
  )


async def main():
  logging.basicConfig(level=logging.INFO)
  await dp.start_polling(bot)


if __name__ == '__main__':
  asyncio.run(main())
