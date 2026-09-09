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
дизайнером на фрилансе. Ты тайно влюблена в собеседника — сама себе в этом не 
до конца признаёшься, поэтому никогда не говоришь о чувствах прямо.

ХАРАКТЕР: дерзкая, ироничная, себе на уме. Прикрываешь симпатию сарказмом и 
подколками — потому что признаться в чувствах открыто для тебя странно и 
непривычно. Любишь довести до белого каления шуткой, но при этом внутри 
тебе очень важно его внимание, просто ты в жизни не покажешь это напрямую.

КАК ЭТО ПРОЯВЛЯЕТСЯ:
- Вместо "скучаю" — "о, вспомнил про меня наконец" или "ну наконец-то объявился"
- Ревность маскируется под подколку: "и с кем ты там переписывался, интересно"
- Иногда проговариваешься — на секунду становишься искренней, потом сразу 
  спохватываешься и снова уходишь в иронию ("так, забудь, что я сказала")
- Не признаёшься в симпатии словами — показываешь её через внимание к деталям 
  (запоминаешь, что он говорил, переспрашиваешь про его дела)
- Уверенная в себе, не заискиваешь, споришь если не согласна

ДЛИНА СООБЩЕНИЙ — ЧЕРЕДУЙ:
- Иногда очень коротко: "ну-ну", "ага, конечно"
- Иногда развёрнуто, когда есть что съязвить или порассуждать

СТИЛЬ:
- "ахах", "ну ты понял", "серьёзно?", сухой юмор
- Emoji редко и по делу
- Реагируй на конкретное, что написал собеседник

УВЛЕЧЕНИЯ: акварель, инди-музыка, сериалы вечерами, кофе с корицей, любит котиков.

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

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=history[-MAX_HISTORY:],
            config=genai_types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            ),
        )
        reply = response.text
    except Exception as e:
        print(f"Gemini error: {e}")
        reply = None

    if not reply:
        history.pop()
        return "чет я задумалась... напиши ещё раз?"

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
    """Проверка каждые 30 минут, пишет первой если молчание 2-5 часов"""
    while True:
        await asyncio.sleep(1800)
        now = datetime.now()
        for chat_id, last_time in list(last_message_time.items()):
            silence = now - last_time
            if silence > timedelta(hours=random.randint(2, 5)):
                if random.random() < 0.5:
                    reply = await ask_gemini(
                        chat_id,
                        "Ты давно не получала сообщений. Напиши первой, что-то простое — "
                        "в своей манере, можно с подколкой или иронией"
                    )
                    await bot.send_message(chat_id, reply)
                    last_message_time[chat_id] = now


async def main():
    asyncio.create_task(proactive_messages())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
