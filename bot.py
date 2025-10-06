import asyncio
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, CommandObject, Command
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


@dp.message(Command("progress"))
async def progress_handler(message: types.Message):
    user_id = message.from_user.id
    progress = await db.get_user_progress(user_id)

    # Если пользователь ещё не выполнял ничего
    if not progress:
        await message.answer("📋 У вас пока нет выполненных заданий.\nСканируйте первый QR-код, чтобы начать!")
        return

    # Подсчёт прогресса
    total_tasks = len(TASKS)
    completed = sum(1 for t in TASKS if progress.get(t))
    percent = int((completed / total_tasks) * 100)

    # Создаём визуальный прогресс-бар
    filled_blocks = int(percent / 10)
    empty_blocks = 10 - filled_blocks
    progress_bar = "🟧" * filled_blocks + "⬜" * empty_blocks

    # Формируем список заданий
    lines = []
    for task_id, task_data in TASKS.items():
        done = progress.get(task_id, False)
        status = "✅" if done else "❌"
        lines.append(f"{status} {task_data['title']}")

    # Итоговое сообщение
    response = (
        f"📊 <b>Ваш прогресс:</b>\n\n"
        f"{progress_bar}  {percent}%\n\n"
        f"Выполнено: <b>{completed}</b> из <b>{total_tasks}</b>\n\n"
        + "\n".join(lines)
    )

    await message.answer(response, parse_mode="HTML")


async def main():
    await db.init_db()
    print("✅ Бот запущен. Нажми Ctrl+C для выхода.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
