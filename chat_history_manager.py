import sqlite3

DB_NAME = "chat_history.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            player_id TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_message(player_id, role, content):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO chat_history (player_id, role, content) VALUES (?, ?, ?)",
        (str(player_id), role, content)
    )
    conn.commit()
    conn.close()

def load_history(player_id, limit=10):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT role, content FROM chat_history WHERE player_id = ? ORDER BY timestamp DESC LIMIT ?",
        (str(player_id), limit)
    )
    rows = c.fetchall()
    conn.close()
    return [{"role": role, "content": content} for role, content in reversed(rows)]

def delete_history(player_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM chat_history WHERE player_id = ?", (str(player_id),))
    conn.commit()
    conn.close()
