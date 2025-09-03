import sqlite3

DATABASE_FILE = 'tracker.db'

connection = sqlite3.connect(DATABASE_FILE)
cursor = connection.cursor()

# Drop the old table if it exists to ensure the new schema is applied
cursor.execute("DROP TABLE IF EXISTS anime")

# Create the new, more detailed anime table
create_anime_table = """
CREATE TABLE IF NOT EXISTS anime (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aid INTEGER NOT NULL UNIQUE,
    title TEXT NOT NULL,
    total_episodes INTEGER NOT NULL,
    watched_episodes INTEGER DEFAULT 0,
    image_url TEXT,
    description TEXT,
    start_date TEXT,
    end_date TEXT,
    anime_type TEXT
);
"""
cursor.execute(create_anime_table)

# --- Tables for caching and rate limiting ---
create_cache_table = """
CREATE TABLE IF NOT EXISTS api_cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    fetched_at REAL NOT NULL
)
"""
cursor.execute(create_cache_table)

create_ratelimit_table = """
CREATE TABLE IF NOT EXISTS rate_limit (
    id INTEGER PRIMARY KEY CHECK (id=1),
    last_ts REAL NOT NULL
)
"""
cursor.execute(create_ratelimit_table)
cursor.execute("INSERT OR IGNORE INTO rate_limit (id, last_ts) VALUES (1, 0)")


print(f"Database '{DATABASE_FILE}' and all tables re-initialized successfully.")
connection.commit()
connection.close()