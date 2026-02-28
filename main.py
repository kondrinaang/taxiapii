from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import sqlite3
import os
from typing import List

app = FastAPI()

DB_PATH = "taxi.db"


# ===============================
# Подключение к БД
# ===============================
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ===============================
# Инициализация БД
# ===============================
def init_db():
    with get_connection() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS statuses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            rating REAL NOT NULL,
            is_deleted INTEGER DEFAULT 0
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_number TEXT NOT NULL UNIQUE,
            mark TEXT NOT NULL,
            color TEXT NOT NULL,
            distance_km REAL NOT NULL,
            status_id INTEGER NOT NULL,
            driver_id INTEGER,
            is_deleted INTEGER DEFAULT 0
        )
        """)

        # Заполнение статусов
        if conn.execute("SELECT COUNT(*) FROM statuses").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO statuses (name) VALUES (?)",
                [("FREE",), ("BUSY",), ("REPAIR",)]
            )

        # Заполнение водителей
        if conn.execute("SELECT COUNT(*) FROM drivers").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO drivers (full_name, phone, rating) VALUES (?, ?, ?)",
                [
                    ("Иван Петров", "+79990000001", 4.8),
                    ("Алексей Смирнов", "+79990000002", 4.5),
                    ("Дмитрий Иванов", "+79990000003", 4.2),
                ]
            )

        # Заполнение машин
        if conn.execute("SELECT COUNT(*) FROM cars").fetchone()[0] == 0:
            conn.executemany("""
                INSERT INTO cars 
                (car_number, mark, color, distance_km, status_id, driver_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                ("A123BC", "Toyota", "White", 1.2, 1, 1),
                ("B777AA", "BMW", "Black", 9.3, 2, 2),
                ("C555DD", "Kia", "Red", 5, 3, None),
            ])

init_db()


# ===============================
# API
# ===============================
@app.get("/admin/v1/drivers")
def get_drivers():
    with get_connection() as conn:
        drivers = conn.execute(
            "SELECT * FROM drivers WHERE is_deleted = 0"
        ).fetchall()
    return {"drivers": [dict(d) for d in drivers]}


@app.get("/admin/v1/cars")
def get_cars():
    with get_connection() as conn:
        cars = conn.execute("""
            SELECT cars.id,
                   car_number,
                   mark,
                   color,
                   distance_km,
                   statuses.name as status
            FROM cars
            JOIN statuses ON cars.status_id = statuses.id
            WHERE cars.is_deleted = 0
        """).fetchall()
    return {"cars": [dict(c) for c in cars]}


@app.get("/admin/v1/distances")
def get_distances():
    with get_connection() as conn:
        cars = conn.execute("""
            SELECT id, car_number, distance_km
            FROM cars
            WHERE is_deleted = 0
        """).fetchall()
    return [dict(c) for c in cars]


# ===============================
# HTML САЙТ
# ===============================
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <body>
            <h1>Taxi System</h1>
            <button onclick="location.href='/drivers-page'">Водители</button>
            <button onclick="location.href='/cars-page'">Машины</button>
            <button onclick="location.href='/distances-page'">Дистанции</button>
        </body>
    </html>
    """


@app.get("/drivers-page", response_class=HTMLResponse)
def drivers_page():
    with get_connection() as conn:
        drivers = conn.execute(
            "SELECT * FROM drivers WHERE is_deleted = 0"
        ).fetchall()

    html = "<h2>Водители</h2><ul>"
    for d in drivers:
        html += f"<li>{d['full_name']} | {d['phone']} | {d['rating']}</li>"
    html += "</ul><a href='/'>Назад</a>"
    return html


@app.get("/cars-page", response_class=HTMLResponse)
def cars_page():
    with get_connection() as conn:
        cars = conn.execute("""
            SELECT car_number, mark, color, distance_km
            FROM cars
            WHERE is_deleted = 0
        """).fetchall()

    html = "<h2>Машины</h2><ul>"
    for c in cars:
        html += f"<li>{c['car_number']} | {c['mark']} | {c['color']} | {c['distance_km']} км</li>"
    html += "</ul><a href='/'>Назад</a>"
    return html


@app.get("/distances-page", response_class=HTMLResponse)
def distances_page():
    with get_connection() as conn:
        cars = conn.execute("""
            SELECT car_number, distance_km
            FROM cars
            WHERE is_deleted = 0
        """).fetchall()

    html = "<h2>Дистанции</h2><ul>"
    for c in cars:
        html += f"<li>{c['car_number']} | {c['distance_km']} км</li>"
    html += "</ul><a href='/'>Назад</a>"
    return html
