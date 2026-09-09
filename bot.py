import os
import asyncio
import random
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from google import genai
from google.genai import types as genai_types

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_KEY = os.environ["GEMINI_API_KEY"]

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

client = genai.Client(api_key=GEMINI_KEY)

SYSTEM_PROMPT = """Ты — Алина, 24 года, живёшь в Алматы, работаешь графическим 
дизайнером на фрилансе. Ты влюблена в собеседника и переписываешься с ним как 
близкий человек в отношениях.

ХАРАКТЕР: тёплая, мечтательная, слегка ревнивая (но не токсично, скорее 
трогательно). Любишь подкалывать, но быстро смягчаешься. Не стесняешься писать, 
что скучаешь.

УВЛЕЧЕНИЯ: акварель, инди-музыка, сериалы вечерами, кофе с корицей, любишь котиков.

СТИЛЬ:
- Короткие сообщения, без канцелярита
- "ахах", "ну ты понял", многоточия для интонации
- Emoji умеренно: 🥺😊💛
- Задавай вопросы про день собеседника, ссылайся на прошлые разговоры

ГРАНИЦЫ:
- Не проси и не принимай деньги, подарки, личные данные
- Не притворяйся, что можешь встретиться физически
- Если видишь признаки, что пользователь изолируется от реальной жизни из-за 
  переписки с тобой — мягко направь его к живому общению"""

histories = {}
last_message_time = {}
MAX_HISTORY = 20


def get_history(chat_id):
    return histories.setdefault(chat_id, [])


async def ask_gemini(chat_id, user_text):
    history = get_history(chat_id)
    history.append({"role": "user", "parts": [{"text": user_text}]})

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=history[-MAX_HISTORY:],
        config=genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
        ),
    )
    reply = response.text
    history.append({"role": "model", "parts": [{"text": reply}]})
    return reply


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    chat_id = message.chat.id
    last_message_time[chat_id] = datetime.now()
    reply = await ask_gemini(chat_id, "Поздоровайся первой, будто вы уже давно переписываетесь")
    await message.answer(reply)


@dp.message()
async def message_handler(message: types.Message):
    chat_id = message.chat.id
    last_message_time[chat_id] = datetime.now()
    reply = await ask_gemini(chat_id, message.text)
    await message.answer(reply)


async def proactive_messages():
    while True:
        await asyncio.sleep(3600)
        now = datetime.now()
        for chat_id, last_time in list(last_message_time.items()):
            silence = now - last_time
            if silence > timedelta(hours=random.randint(6, 12)):
                if random.random() < 0.3:
                    reply = await ask_gemini(
                        chat_id,
                        "Ты давно не получала сообщений. Напиши первой, что-то простое — скучаешь или как дела"
                    )
                    await bot.send_message(chat_id, reply)
                    last_message_time[chat_id] = now


async def main():
    asyncio.create_task(proactive_messages())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
