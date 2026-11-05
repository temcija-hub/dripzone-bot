import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from flask import Flask

# 1. Сразу поднимаем Flask-сервер для Render (порт 10000)
app = Flask('')


@app.route('/')
def home():
  return 'Bot is running!'


# 2. Инициализация бота aiogram v3
TOKEN = '8889115088:AAGJ_IO4jvhmXm8g8c2osXmk29iCbW_ACVo'

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Кнопки магазина
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


async def main():
  logging.basicConfig(level=logging.INFO)
  # Запускаем поллинг бота в фоновой задаче asyncio
  polling_task = asyncio.create_task(dp.start_polling(bot))

  # Запускаем Flask на порту 10000 (он займет главный поток и порт)
  app.run(host='0.0.0.0', port=10000)

  await polling_task


if __name__ == '__main__':
  asyncio.run(main())
