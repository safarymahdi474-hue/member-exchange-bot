import aiosqlite
from config import DB_PATH


async def get_db():
    return await aiosqlite.connect(DB_PATH)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                coins INTEGER DEFAULT 0,
                referrer_id INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL UNIQUE,
                channel_name TEXT NOT NULL,
                coins_reward INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_channel_joins (
                user_id INTEGER,
                channel_id TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, channel_id)
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                channel_id TEXT NOT NULL,
                channel_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                coins_spent INTEGER NOT NULL,
                status TEXT DEFAULT 'active',
                cancel_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS coin_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS gift_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                coins INTEGER NOT NULL,
                max_uses INTEGER NOT NULL,
                used_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS gift_code_uses (
                user_id INTEGER,
                code_id INTEGER,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, code_id)
            );
            CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT,
    permissions TEXT DEFAULT 'full'
);
CREATE TABLE IF NOT EXISTS force_join_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL UNIQUE,
    channel_name TEXT NOT NULL,
    remove_type TEXT DEFAULT 'count',
    remove_value INTEGER DEFAULT 100,
    current_count INTEGER DEFAULT 0,
    expires_at TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS skipped_channels (
    user_id INTEGER,
    channel_id TEXT,
    skipped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, channel_id)
);

            INSERT OR IGNORE INTO settings (key, value) VALUES ('coins_start', '50');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('coins_per_join', '1');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('coins_per_member', '2');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('coins_per_referral', '25');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('min_order', '1');
        """)
        await db.commit()


async def get_setting(key: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return int(row[0]) if row else 0


async def set_setting(key: str, value: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        await db.commit()

CREATE TABLE IF NOT EXISTS skipped_channels (
    user_id INTEGER,
    channel_id TEXT,
    skipped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, channel_id)
);
CREATE TABLE IF NOT EXISTS skipped_channels (
    user_id INTEGER,
    channel_id TEXT,
    skipped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, channel_id)
);

CREATE TABLE IF NOT EXISTS force_join_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL UNIQUE,
    channel_name TEXT NOT NULL,
    remove_type TEXT DEFAULT 'count',
    remove_value INTEGER DEFAULT 100,
    current_count INTEGER DEFAULT 0,
    expires_at TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT,
    permissions TEXT DEFAULT 'full'
);
