import asyncio
import os
import ipaddress
import socket
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from ipyapi import AsyncIPyAPI

# --- Веб-сервер для UptimeRobot ---
app = Flask('')

@app.route('/')
def home():
    return "Бот работает 24/7!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- Настройки бота ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Привет! Я OSINT-бот для поиска по IP и доменам.\n\n"
        "Отправь мне:\n"
        "• IP-адрес (например, `8.8.8.8`)\n"
        "• Домен (например, `vk.com`)\n\n"
        "Я найду его местоположение и провайдера.",
        parse_mode="Markdown"
    )

@dp.message()
async def handle_ip(message: types.Message):
    text = message.text.strip()
    
    target_ip = None
    is_domain = False

    try:
        ip_obj = ipaddress.ip_address(text)
        if ip_obj.is_private:
            await message.answer("❌ Это приватный (локальный) IP. Я могу искать только публичные адреса.")
            return
        target_ip = text
    except ValueError:
        try:
            target_ip = socket.gethostbyname(text)
            is_domain = True
        except socket.gaierror:
            await message.answer("❌ Это не похоже ни на IP, ни на домен. Попробуй формат: `8.8.8.8` или `vk.com`", parse_mode="Markdown")
            return

    await message.answer(f"🔎 Ищу информацию по `{text}`...", parse_mode="Markdown")
    
    try:
        async with AsyncIPyAPI() as client:
            loc = await client.get_location(target_ip)
            
            country_code = loc.country_code.lower() if loc.country_code else "un"
            flag = "".join(chr(127397 + ord(c)) for c in country_code.upper())
            map_link = f"https://www.google.com/maps?q={loc.latitude},{loc.longitude}"
            
            response_text = (
                f"📍 **Результат поиска**\n"
                f"Запрос: `{text}`\n"
            )
            if is_domain:
                response_text += f"IP домена: `{target_ip}`\n"
            
            response_text += (
                f"\n{flag} **Страна:** {loc.country_name}\n"
                f"🏙 **Город:** {loc.city}\n"
                f"🗺 **Регион:** {loc.region}\n"
                f"🏢 **Провайдер:** {loc.org}\n"
                f"⏰ **Часовой пояс:** {loc.timezone}\n\n"
                f"[Открыть на карте]({map_link})"
            )
            
            await message.answer(response_text, parse_mode="Markdown", disable_web_page_preview=True)
            
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при запросе к API. Возможно, IP не найден. Детали: {e}")

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive()
    asyncio.run(main())