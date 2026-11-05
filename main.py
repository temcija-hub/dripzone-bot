import asyncio
import logging
import os
import threading
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from flask import Flask

# 1. Настройка Flask-сервера для удержания порта 10000 на Render
app = Flask('')


@app.route('/')
def home():
  return 'Bot is running!'


def run_web():
  app.run(host='0.0.0.0', port=10000)


# Запускаем веб-сервер в фоновом потоке
threading.Thread(target=run_web).daemon = True

# 2. Инициализация бота aiogram v3
TOKEN = '8889115088:AAGJ_IO4jvhmXm8g8c2osXmk29iCbW_ACVo'

bot = Bot(token=TOKEN)
dp = Dispatcher()


# Обработчик команды /start
@dp.message(Command('start'))
async def send_welcome(message: types.Message):
  await message.answer('Дрип зона на связи! Бот успешно запущен 🛒')


# 3. Основная функция запуска бота
async def main():
  logging.basicConfig(level=logging.INFO)
  await dp.start_polling(bot)


if __name__ == '__main__':
  asyncio.run(main())
