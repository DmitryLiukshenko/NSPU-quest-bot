import asyncio
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, CommandObject
from config import BOT_TOKEN
import database as db

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Загружаем список заданий
with open("tasks.json", "r", encoding="utf-8") as f:
    TASKS = json.load(f)

user_active_task = {}  # временное хранение активных заданий

@dp.message(CommandStart())
async def start_handler(message: types.Message, command: CommandObject):
    await db.add_user(message.from_user.id, message.from_user.username or "")
    task_arg = command.args  # параметр после /start=

    if task_arg and task_arg in TASKS:
        task = TASKS[task_arg]
        user_active_task[message.from_user.id] = task_arg
        await message.answer(
            f"🎯 <b>{task['title']}</b>\n\n{task['description']}",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "👋 Привет! Я бот-квест НГПУ.\n"
            "Сканируй QR-коды в локациях, чтобы получать задания 🗺️"
        )


@dp.message(F.photo)
async def photo_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_active_task:
        await message.answer("📍 Сначала отсканируй QR-код с заданием!")
        return

    task_id = user_active_task[user_id]
    done = await db.check_task_done(user_id, task_id)
    if done:
        await message.answer("✅ Это задание уже выполнено. Ищи следующее!")
        return

    await db.mark_task_done(user_id, task_id)
    del user_active_task[user_id]
    await message.answer("🎉 Отлично! Задание засчитано.\nИщи следующий QR-код 🔍")

async def main():
    await db.init_db()
    print("✅ Бот запущен. Нажми Ctrl+C для выхода.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
