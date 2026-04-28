import sqlite3

DATABASE_NAME = 'blog.db'

def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # 允许通过列名访问数据
    return conn

def init_db():
    """初始化数据库结构：创建用户表和文章表"""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. 创建用户表 (users)
    cursor.execute("
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);")

    # 2. 创建文章表 (posts)
    cursor.execute("
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);")

    conn.commit()
    conn.close()
    print("Database initialized successfully: users and posts tables created.")

if __name__ == '__main__':
    init_db()