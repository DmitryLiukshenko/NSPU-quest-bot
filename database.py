import aiosqlite
import os
import shutil
from datetime import datetime

DB_NAME = "database.db"
BACKUP_DIR = "backups"

async def init_db():
    # 🧩 Создание резервной копии перед проверкой структуры
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if os.path.exists(DB_NAME):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_path = os.path.join(BACKUP_DIR, f"database_backup_{timestamp}.db")
        try:
            shutil.copy2(DB_NAME, backup_path)
            print(f"💾 Резервная копия базы создана: {backup_path}")
        except Exception as e:
            print(f"[⚠️] Не удалось создать резервную копию базы: {e}")

    # 🔹 Проверка структуры таблиц
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT
            )
        """)

        # Таблица прогресса
        await db.execute("""
            CREATE TABLE IF NOT EXISTS progress (
                user_id INTEGER,
                task_id TEXT,
                completed INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)
        await db.commit()

        # 🔒 Проверка и добавление уникального индекса
        try:
            await db.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_progress_unique
                ON progress (user_id, task_id)
            """)
            await db.commit()
        except Exception as e:
            print(f"[⚠️] Ошибка при создании уникального индекса: {e}")

        print("✅ База данных проверена и готова к работе")

# 🔹 Добавление пользователя
async def add_user(user_id: int, username: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        await db.commit()

# 🔹 Отметить выполнение задания
async def mark_task_done(user_id: int, task_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO progress (user_id, task_id, completed)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, task_id)
            DO UPDATE SET completed = 1
        """, (user_id, task_id))
        await db.commit()

# 🔹 Снять отметку о выполнении
async def unmark_task_done(user_id: int, task_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE progress
            SET completed = 0
            WHERE user_id = ? AND task_id = ?
        """, (user_id, task_id))
        await db.commit()

# 🔹 Проверить, выполнено ли задание
async def check_task_done(user_id: int, task_id: str) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("""
            SELECT completed FROM progress WHERE user_id = ? AND task_id = ?
        """, (user_id, task_id)) as cursor:
            row = await cursor.fetchone()
            return bool(row and row[0] == 1)

# 🔹 Получить прогресс пользователя
async def get_user_progress(user_id: int) -> dict:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT task_id, completed FROM progress WHERE user_id = ?", (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return {task_id: bool(completed) for task_id, completed in rows}
