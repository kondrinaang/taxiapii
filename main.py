from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import uvicorn
from typing import List

app = FastAPI()
DB_PATH = "taxi.db"


# =================================================
# Подключение к БД
# =================================================
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# =================================================
# Инициализация БД
# =================================================
def init_db():
    with get_connection() as conn:

        # Справочник статусов
        conn.execute("""
        CREATE TABLE IF NOT EXISTS statuses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """)

        # Водители
        conn.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            rating REAL NOT NULL,
            is_deleted INTEGER DEFAULT 0
        )
        """)

        # Машины
        conn.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_number TEXT NOT NULL UNIQUE,
            mark TEXT NOT NULL,
            color TEXT NOT NULL,
            distance_km REAL NOT NULL,
            status_id INTEGER NOT NULL,
            driver_id INTEGER,
            is_deleted INTEGER DEFAULT 0,
            FOREIGN KEY(driver_id) REFERENCES drivers(id),
            FOREIGN KEY(status_id) REFERENCES statuses(id)
        )
        """)

        # -------------------------
        # Заполнение справочника
        # -------------------------
        status_count = conn.execute("SELECT COUNT(*) FROM statuses").fetchone()[0]
        if status_count == 0:
            conn.executemany(
                "INSERT INTO statuses (name) VALUES (?)",
                [("FREE",), ("BUSY",), ("REPAIR",)]
            )

        # -------------------------
        # Первичное заполнение
        # -------------------------
        driver_count = conn.execute("SELECT COUNT(*) FROM drivers").fetchone()[0]
        if driver_count == 0:
            conn.executemany(
                "INSERT INTO drivers (full_name, phone, rating) VALUES (?, ?, ?)",
                [
                    ("Иван Петров", "+79990000001", 4.8),
                    ("Алексей Смирнов", "+79990000002", 4.5),
                    ("Дмитрий Иванов", "+79990000003", 4.2),
                ]
            )

        car_count = conn.execute("SELECT COUNT(*) FROM cars").fetchone()[0]
        if car_count == 0:
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


# =================================================
# MODELS
# =================================================
class DriverCreate(BaseModel):
    full_name: str
    phone: str
    rating: float


class CarCreate(BaseModel):
    car_number: str
    mark: str
    color: str
    distance_km: float
    status_id: int
    driver_id: int | None = None



class DistanceResponse(BaseModel):
    id: int
    car_number: str
    distance_km: float


# =================================================
# СОЗДАНИЕ ВОДИТЕЛЯ
# =================================================
@app.post("/admin/v1/drivers", status_code=201)
def create_driver(driver: DriverCreate):

    if driver.rating < 0 or driver.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 0 and 5")

    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO drivers (full_name, phone, rating) VALUES (?, ?, ?)",
            (driver.full_name, driver.phone, driver.rating)
        )
        driver_id = cursor.lastrowid

    return {"id": driver_id}


# =================================================
# СОЗДАНИЕ МАШИНЫ
# =================================================
@app.post("/admin/v1/cars", status_code=201)
def create_car(car: CarCreate):

    if car.distance_km <= 0:
        raise HTTPException(status_code=400, detail="Distance must be greater than 0")

    with get_connection() as conn:

        # Проверка статуса
        status = conn.execute(
            "SELECT id FROM statuses WHERE id = ?",
            (car.status_id,)
        ).fetchone()

        if not status:
            raise HTTPException(status_code=400, detail="Status not found")

        # Проверка водителя
        if car.driver_id:
            driver = conn.execute(
                "SELECT id FROM drivers WHERE id = ? AND is_deleted = 0",
                (car.driver_id,)
            ).fetchone()

            if not driver:
                raise HTTPException(status_code=400, detail="Driver not found")

        cursor = conn.execute("""
            INSERT INTO cars 
            (car_number, mark, color, distance_km, status_id, driver_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            car.car_number,
            car.mark,
            car.color,
            car.distance_km,
            car.status_id,
            car.driver_id
        ))

        car_id = cursor.lastrowid

    return {"id": car_id}


# =================================================
# SOFT DELETE ВОДИТЕЛЯ
# =================================================
@app.patch("/admin/v1/drivers/{driver_id}")
def soft_delete_driver(driver_id: int):

    with get_connection() as conn:
        result = conn.execute(
            "UPDATE drivers SET is_deleted = 1 WHERE id = ?",
            (driver_id,)
        )

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Driver not found")

    return {"id": driver_id}


# =================================================
# SOFT DELETE МАШИНЫ
# =================================================
@app.patch("/admin/v1/cars/{car_id}")
def soft_delete_car(car_id: int):

    with get_connection() as conn:
        result = conn.execute(
            "UPDATE cars SET is_deleted = 1 WHERE id = ?",
            (car_id,)
        )

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Car not found")

    return {"id": car_id}


# =================================================
# ПОЛУЧЕНИЕ ВОДИТЕЛЕЙ
# =================================================
@app.get("/admin/v1/drivers")
def get_drivers():

    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM drivers WHERE is_deleted = 0"
        )
        drivers = [dict(row) for row in cursor.fetchall()]

    return {"drivers": drivers}


# =================================================
# ПОЛУЧЕНИЕ МАШИН
# =================================================
@app.get("/admin/v1/cars")
def get_cars():

    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT cars.id,
                   car_number,
                   mark,
                   color,
                   distance_km,
                   statuses.name as status,
                   driver_id
            FROM cars
            JOIN statuses ON cars.status_id = statuses.id
            WHERE cars.is_deleted = 0
        """)
        cars = [dict(row) for row in cursor.fetchall()]

    return {"cars": cars}

@app.get("/admin/v1/cars/{car_id}")
def get_car_by_id(car_id: int):

    with get_connection() as conn:
        car = conn.execute("""
            SELECT cars.id,
                   car_number,
                   mark,
                   color,
                   distance_km,
                   statuses.name as status,
                   driver_id
            FROM cars
            JOIN statuses ON cars.status_id = statuses.id
            WHERE cars.id = ? AND cars.is_deleted = 0
        """, (car_id,)).fetchone()

        if not car:
            raise HTTPException(status_code=404, detail="Car not found")

    return dict(car)


@app.put("/admin/v1/drivers/{driver_id}")
def update_driver(driver_id: int, driver: DriverCreate):

    with get_connection() as conn:
        result = conn.execute("""
            UPDATE drivers
            SET full_name = ?, phone = ?, rating = ?
            WHERE id = ? AND is_deleted = 0
        """, (driver.full_name, driver.phone, driver.rating, driver_id))

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Driver not found")

    return {"id": driver_id}


@app.put("/admin/v1/cars/{car_id}")
def update_car(car_id: int, car: CarCreate):

    with get_connection() as conn:

        # Проверка статуса
        status = conn.execute(
            "SELECT id FROM statuses WHERE id = ?",
            (car.status_id,)
        ).fetchone()

        if not status:
            raise HTTPException(status_code=400, detail="Status not found")

        # Проверка водителя
        if car.driver_id:
            driver = conn.execute(
                "SELECT id FROM drivers WHERE id = ? AND is_deleted = 0",
                (car.driver_id,)
            ).fetchone()

            if not driver:
                raise HTTPException(status_code=400, detail="Driver not found")

        result = conn.execute("""
            UPDATE cars
            SET car_number = ?,
                mark = ?,
                color = ?,
                distance_km = ?,
                status_id = ?,
                driver_id = ?
            WHERE id = ? AND is_deleted = 0
        """, (
            car.car_number,
            car.mark,
            car.color,
            car.distance_km,
            car.status_id,
            car.driver_id,
            car_id
        ))

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Car not found")

    return {"id": car_id}


@app.get("/admin/v1/distances", response_model=List[DistanceResponse])
def get_distances():

    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT id, car_number, distance_km
            FROM cars
            WHERE is_deleted = 0
        """)
        distances = [dict(row) for row in cursor.fetchall()]

    return distances







from fastapi.responses import HTMLResponse


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <head>
            <title>Taxi System</title>
        </head>
        <body>
            <h1>Taxi Management System</h1>

            <button onclick="location.href='/drivers-page'">
                Водители
            </button>

            <button onclick="location.href='/cars-page'">
                Машины
            </button>

            <button onclick="location.href='/distances-page'">
                Дистанции
            </button>
        </body>
    </html>
    """

@app.get("/drivers-page", response_class=HTMLResponse)
def drivers_page():

    with get_connection() as conn:
        drivers = conn.execute(
            "SELECT * FROM drivers WHERE is_deleted = 0"
        ).fetchall()

    html = """
    <h2>Список водителей</h2>
    <ul>
    """

    for d in drivers:
        html += f"<li>{d['full_name']} | Телефон: {d['phone']} | Рейтинг: {d['rating']}</li>"

    html += """
    </ul>
    <br>
    <a href="/">Назад</a>
    """

    return html


@app.get("/cars-page", response_class=HTMLResponse)
def cars_page():

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

    html = """
    <h2>Список машин</h2>
    <ul>
    """

    for c in cars:
        html += f"<li>{c['car_number']} | {c['mark']} | {c['color']} | Дистанция: {c['distance_km']} | Статус: {c['status']}</li>"

    html += """
    </ul>
    <br>
    <a href="/">Назад</a>
    """

    return html


@app.get("/distances-page", response_class=HTMLResponse)
def distances_page():

    with get_connection() as conn:
        cars = conn.execute("""
            SELECT car_number, distance_km
            FROM cars
            WHERE is_deleted = 0
        """).fetchall()

    html = """
    <h2>Дистанции автомобилей</h2>
    <ul>
    """

    for c in cars:
        html += f"<li>Машина {c['car_number']} | Дистанция: {c['distance_km']} км</li>"

    html += """
    </ul>
    <br>
    <a href="/">Назад</a>
    """

    return html



if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
