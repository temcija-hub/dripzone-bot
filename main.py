import asyncio
import logging
import os
import threading
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from flask import Flask

# 1. Настройка Flask (Gunicorn будет обращаться к переменной 'app')
app = Flask('')


@app.route('/')
def home():
  return 'Bot is running!'


# 2. Инициализация бота aiogram v3
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


# Функция запуска поллинга бота в фоне
async def run_bot():
  logging.basicConfig(level=logging.INFO)
  await dp.start_polling(bot)


def start_background_loop():
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  loop.run_until_complete(run_bot())


# Запускаем бота в отдельном потоке, пока Gunicorn держит веб-сервер Flask
threading.Thread(target=start_background_loop, daemon=True).start()

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
