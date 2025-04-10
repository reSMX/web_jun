from fastapi import FastAPI, UploadFile, Form, HTTPException, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import pandas as pd
import sqlite3
import hashlib
from pathlib import Path
from back import process_with_yolo

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
CSV_DIR = "csv_logs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CSV_DIR, exist_ok=True)

def create_connection():
    db_path = Path(__file__).parent / 'Jun_cup' / 'db.sqlite3'
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
async def registration(
    response: Response,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...)
) -> JSONResponse:
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
        user_id = cursor.lastrowid
        response.set_cookie(key="user_id", value=str(user_id), max_age=60*60*24)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Такой пользователь уже существует")
    finally:
        conn.close()

    return JSONResponse(status_code=201, content={"message": "Пользователь успешно зарегистрирован"})

@app.post("/login/")
async def login(response: Response, email: str = Form(...), password: str = Form(...)) -> JSONResponse:
    conn = create_connection()
    cursor = conn.cursor()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    try:
        cursor.execute(
            "SELECT * FROM users WHERE email = ? AND password = ?",
            (email, hashed_password)
        )
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=400, detail="Неверные имя пользователя или пароль")
    finally:
        conn.close()

    return JSONResponse(status_code=200, content={"message": "Успешный вход"})

@app.post("/upload/")
async def upload_image(file: UploadFile, username: str = Form(...)):
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[-1]
    raw_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
    csv_path = os.path.join(CSV_DIR, f"{username}.csv")

    with open(raw_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        detections = process_with_yolo(raw_path, username, file_id)
    except Exception as e:
        return JSONResponse({"error": f"Failed to process image: {str(e)}"}, status_code=500)

    df = pd.DataFrame(detections)
    if os.path.exists(csv_path):
        df.to_csv(csv_path, mode='a', index=False, header=False)
    else:
        df.to_csv(csv_path, index=False)

    return JSONResponse({
        "message": "Image uploaded and processed by YOLO.",
        "detections_count": len(detections),
        "results": detections
    })
