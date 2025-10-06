import aiosqlite

DB_NAME = "database.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS progress (
                user_id INTEGER,
                task_id TEXT,
                completed INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                UNIQUE(user_id, task_id)
            )
        """)
        await db.commit()


async def add_user(user_id: int, username: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        await db.commit()

async def mark_task_done(user_id: int, task_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO progress (user_id, task_id, completed)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, task_id)
            DO UPDATE SET completed = 1
        """, (user_id, task_id))
        await db.commit()


async def check_task_done(user_id: int, task_id: str) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("""
            SELECT completed FROM progress WHERE user_id = ? AND task_id = ?
        """, (user_id, task_id)) as cursor:
            row = await cursor.fetchone()
            return bool(row and row[0] == 1)

async def get_user_progress(user_id: int) -> dict:
    """Возвращает словарь {task_id: completed}"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT task_id, completed FROM progress WHERE user_id = ?", (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return {task_id: bool(completed) for task_id, completed in rows}

async def unmark_task_done(user_id: int, task_id: str):
    """Отменяет выполнение задания"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE progress
            SET completed = 0
            WHERE user_id = ? AND task_id = ?
        """, (user_id, task_id))
        await db.commit()

