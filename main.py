import asyncio
import logging
import os
import threading
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from flask import Flask

# Flask-сервер для удержания порта Render
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

# Инициализация бота
TOKEN = '8889115088:AAGJ_IO4jvhmXm8g8c2osXmk29iCbW_ACVo'
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Кнопки главного меню
shop_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='📦 Каталог', callback_data='catalog')],
        [InlineKeyboardButton(text='🛒 Кошик', callback_data='cart')],
        [InlineKeyboardButton(text='💬 Відгуки', callback_data='reviews')],
        [InlineKeyboardButton(text='📏 Розміри', callback_data='sizes')],
        [
            InlineKeyboardButton(
                text='⚙️ Адмін панель', callback_data='admin_panel'
            )
        ],
        [InlineKeyboardButton(text='📊 Статистика', callback_data='statistics')],
    ]
)


@dp.message(Command('start'))
async def send_welcome(message: types.Message):
  await message.answer(
      'Вітаю у DRIPZONE Shop! Вибери потрібний розділ:',
      reply_markup=shop_keyboard,
  )


# Обработчики нажатий на инлайн-кнопки
@dp.callback_query(F.data == 'catalog')
async def cb_catalog(callback: types.CallbackQuery):
  await callback.message.answer('📦 Розділ каталогу наповнюється...')
  await callback.answer()


@dp.callback_query(F.data == 'cart')
async def cb_cart(callback: types.CallbackQuery):
  await callback.message.answer('🛒 Ваш кошик порожній.')
  await callback.answer()


@dp.callback_query(F.data == 'reviews')
async def cb_reviews(callback: types.CallbackQuery):
  await callback.message.answer('💬 Тут будуть відгуки покупців.')
  await callback.answer()


@dp.callback_query(F.data == 'sizes')
async def cb_sizes(callback: types.CallbackQuery):
  await callback.message.answer('📏 Доступні розміри: S, M, L, XL, XXL.')
  await callback.answer()


@dp.callback_query(F.data == 'admin_panel')
async def cb_admin(callback: types.CallbackQuery):
  await callback.message.answer('⚙️ Панель адміністратора.')
  await callback.answer()


@dp.callback_query(F.data == 'statistics')
async def cb_stats(callback: types.CallbackQuery):
  await callback.message.answer('📊 Статистика магазину.')
  await callback.answer()


async def main():
  logging.basicConfig(level=logging.INFO)
  await dp.start_polling(bot)


if __name__ == '__main__':
  asyncio.run(main())
