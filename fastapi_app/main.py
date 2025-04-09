from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import JSONResponse
import sqlite3
import hashlib
from pathlib import Path

app = FastAPI()


def create_connection():
    db_path = Path(__file__).parent.parent / 'Jun_cup' / 'db.sqlite3'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def create_users_table():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

create_users_table()


@app.post("/reg/")
async def registration(username: str = Form(...), email: str = Form(...), password: str = Form(...), confirm_password: str = Form(...)) -> JSONResponse:

    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Пароли не совпадают")

    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    conn = create_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, hashed_password)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Такой пользователь уже существует")
    finally:
        conn.close()

    return JSONResponse(status_code=201, content={"message": "Пользователь успешно зарегистрирован"})
