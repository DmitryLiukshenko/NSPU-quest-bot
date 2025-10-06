import asyncio
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, CommandObject, Command
from config import BOT_TOKEN
import database as db
import os
from datetime import datetime

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
    username = message.from_user.username or "unknown_user"

    if user_id not in user_active_task:
        await message.answer("📍 Сначала отсканируйте QR-код с заданием!")
        return

    task_id = user_active_task[user_id]
    done = await db.check_task_done(user_id, task_id)
    if done:
        await message.answer("✅ Это задание уже выполнено. Ищи следующее!")
        return

    # 📸 Получаем file_id последнего (наиболее качественного) фото
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)

    # Создаём папку для пользователя
    user_folder = f"photos/{user_id}"
    os.makedirs(user_folder, exist_ok=True)

    # Имя файла с датой и заданием
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    photo_path = f"{user_folder}/{task_id}_{timestamp}.jpg"

    # Скачиваем фото
    await bot.download_file(file.file_path, photo_path)

    # Отмечаем выполнение в базе
    await db.mark_task_done(user_id, task_id)
    del user_active_task[user_id]

    await message.answer("🎉 Отлично! Фото получено и задание засчитано.")

    # Показываем прогресс
    progress = await db.get_user_progress(user_id)
    total_tasks = len(TASKS)
    completed = sum(1 for t in TASKS if progress.get(t))
    percent = int((completed / total_tasks) * 100)
    filled_blocks = int(percent / 10)
    empty_blocks = 10 - filled_blocks
    progress_bar = "🟧" * filled_blocks + "⬜" * empty_blocks

    lines = []
    for t_id, task_data in TASKS.items():
        done = progress.get(t_id, False)
        status = "✅" if done else "❌"
        lines.append(f"{status} {task_data['title']}")

    response = (
        f"📊 <b>Ваш прогресс:</b>\n\n"
        f"{progress_bar}  {percent}%\n\n"
        f"Выполнено: <b>{completed}</b> из <b>{total_tasks}</b>\n\n"
        + "\n".join(lines)
    )

    await message.answer(response, parse_mode="HTML")
    await message.answer("🚀 Ищи следующий QR-код, чтобы продолжить квест!")

    print(f"📷 Фото сохранено: {photo_path}")

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

@dp.message(Command("cancel"))
async def cancel_task_handler(message: types.Message):
    user_id = message.from_user.id

    if user_id not in user_active_task:
        await message.answer("❌ У вас нет активного задания для отмены.")
        return

    task_id = user_active_task[user_id]

    # Проверим, было ли задание уже выполнено
    done = await db.check_task_done(user_id, task_id)

    if done:
        await db.unmark_task_done(user_id, task_id)
        await message.answer(
            "♻️ Выполнение задания отменено.\n"
            "Задание теперь отмечено как невыполненное."
        )
    else:
        await message.answer("🔄 Текущее задание отменено.\nМожете начать заново.")

    # В любом случае убираем активное задание
    del user_active_task[user_id]

    # Покажем обновлённый прогресс
    progress = await db.get_user_progress(user_id)
    total_tasks = len(TASKS)
    completed = sum(1 for t in TASKS if progress.get(t))
    percent = int((completed / total_tasks) * 100)

    filled_blocks = int(percent / 10)
    empty_blocks = 10 - filled_blocks
    progress_bar = "🟧" * filled_blocks + "⬜" * empty_blocks

    lines = []
    for t_id, task_data in TASKS.items():
        done = progress.get(t_id, False)
        status = "✅" if done else "❌"
        lines.append(f"{status} {task_data['title']}")

    response = (
        f"📊 <b>Ваш обновлённый прогресс:</b>\n\n"
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
