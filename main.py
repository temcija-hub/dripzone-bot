import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from flask import Flask
from threading import Thread

BOT_TOKEN = os.getenv("BOT_TOKEN", "8889115088:AAE9c82-FDe1DoSczwUboBwn5-EtajpfKwY")
ADMIN_ID = 2125409043

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ФЛАСК ДЛЯ UPTIME ---
app = Flask("")


@app.route("/")
def home():
  return "DripZone Bot is alive and running 24/7!"


def run_flask():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


def keep_alive():
  t = Thread(target=run_flask)
  t.start()


# --- ТОВАРЫ С ТВОИМИ FILE_ID ---
PRODUCTS = {
    "dior": {
        "name": "Футболка Dior",
        "price": "1200 грн",
        "desc": "Стильна брендова футболка Dior. Преміум якість.",
        "file_id": "AgACAgIAAxkBAAIPLmrt4vNwRc8m2iQfw_-W3NKl0vGtAAI_HmsbmmpxSwABU2C581C6tgEAAwIAA3kAAz0E",
    },
    "essentials": {
        "name": "Худі Essentials",
        "price": "2100 грн",
        "desc": "Тепле оверсайз худі Fear of God Essentials.",
        "file_id": "AgACAgIAAxkBAAIPEmrt4K9Wy_kOTZyJGzwXufHjDx54AAIvHmsbmmpxS9Zd79PH6rmxAQADAgADeQADPQQ",
    },
    "hellstar": {
        "name": "Худі Hellstar",
        "price": "2300 грн",
        "desc": "Яскравий та унікальний принт Hellstar.",
        "file_id": "AgACAgIAAxkBAAIOz2rt3I9WAu30D6tgMDQkv35o4LQeAAIXHmsbmmpxS5SavIyPLdFbAQADAgADeQADPQQ",
    },
    "gallery": {
        "name": "Свитшот Gallery Dept",
        "price": "1900 грн",
        "desc": "Фірмовий стиль та унікальний дизайн Gallery Dept.",
        "file_id": "AgACAgIAAxkBAAINb2rtqdbMGQ1-UvEupvHTyQboacu4AAIRHmsbtDlwS2jgzwyjxRmzAQADAgADeQADPQQ",
    },
}


def get_main_keyboard(user_id):
  keyboard = [
      [
          InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog"),
          InlineKeyboardButton(text="🛒 Кошик", callback_data="cart"),
      ],
      [
          InlineKeyboardButton(
              text="ℹ️ Про нас / Доставка", callback_data="about"
          )
      ],
  ]
  if user_id == ADMIN_ID:
    keyboard.append(
        [InlineKeyboardButton(text="⚙️ Адмін-панель", callback_data="admin_panel")]
    )
  return InlineKeyboardMarkup(inline_keyboard=keyboard)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
  keyboard = get_main_keyboard(message.from_user.id)
  await message.answer(
      "Вітаємо у **DripZone**! 🔥\nОбирай стильний одяг та оформлюй замовлення в кілька кліків.",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )


@dp.callback_query(F.data == "catalog")
async def show_catalog(callback: types.CallbackQuery):
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text="Діори", callback_data="item_dior")],
          [
              InlineKeyboardButton(
                  text="Essentials", callback_data="item_essentials"
              )
          ],
          [InlineKeyboardButton(text="Hellstar", callback_data="item_hellstar")],
          [
              InlineKeyboardButton(
                  text="Gallery Dept", callback_data="item_gallery"
              )
          ],
          [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_home")],
      ]
  )
  await callback.message.edit_text(
      "Обери товар із каталогу:", reply_markup=keyboard
  )
  await callback.answer()


@dp.callback_query(F.data.startswith("item_"))
async def show_product(callback: types.CallbackQuery):
  item_key = callback.data.split("_")[1]
  item = PRODUCTS.get(item_key)

  if not item:
    await callback.answer("Товар не знайдено!", show_alert=True)
    return

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="🛒 Купити", callback_data=f"buy_{item_key}"
              )
          ],
          [InlineKeyboardButton(text="⬅️ До каталогу", callback_data="catalog")],
      ]
  )

  text = f"<b>{item['name']}</b>\n\nЦіна: {item['price']}\n{item['desc']}"

  try:
    await callback.message.delete()
  except Exception:
    pass

  if item["file_id"]:
    await callback.message.answer_photo(
        photo=item["file_id"], caption=text, reply_markup=keyboard, parse_mode="HTML"
    )
  else:
    await callback.message.answer(
        text, reply_markup=keyboard, parse_mode="HTML"
    )

  await callback.answer()


@dp.callback_query(F.data == "back_home")
async def back_home(callback: types.CallbackQuery):
  keyboard = get_main_keyboard(callback.from_user.id)
  try:
    await callback.message.delete()
  except Exception:
    pass
  await callback.message.answer(
      "Головне меню DripZone:", reply_markup=keyboard
  )
  await callback.answer()


@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
  if callback.from_user.id != ADMIN_ID:
    await callback.answer("У вас немає доступу!", show_alert=True)
    return

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="📊 Статистика", callback_data="admin_stats"
              )
          ],
          [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_home")],
      ]
  )
  await callback.message.edit_text(
      "Панель адміністратора DripZone:", reply_markup=keyboard
  )
  await callback.answer()


@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
  if callback.from_user.id != ADMIN_ID:
    return
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
      ]
  )
  await callback.message.edit_text(
      "📊 Статистика бота:\n\n• Активних користувачів: 1\n• Замовлень: 0",
      reply_markup=keyboard,
  )
  await callback.answer()


async def main():
  keep_alive()
  print("Бот та Flask-сервер успішно запущено!")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
