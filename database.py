import aiosqlite
import os

DB_PATH = "devices.db"

async def init_db():
    """Buat tabel jika belum ada"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                location TEXT
            )
        """)
        await db.commit()

async def get_all_devices():
    """Ambil semua perangkat"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, name, location FROM devices ORDER BY name")
        rows = await cursor.fetchall()
        return [{"id": row[0], "name": row[1], "location": row[2] or ""} for row in rows]

async def add_device(device_id: str, name: str, location: str = ""):
    """Tambah perangkat baru"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO devices (id, name, location) VALUES (?, ?, ?)",
            (device_id, name, location)
        )
        await db.commit()

async def remove_device(device_id: str):
    """Hapus perangkat"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM devices WHERE id = ?", (device_id,))
        await db.commit()
