import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random

conn = sqlite3.connect("restaurant.db")
c = conn.cursor()
c.execute("PRAGMA foreign_keys = ON")

# ── SCHEMA ────────────────────────────────────────────────────────────────────

c.execute('''CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT "официант"
                  CHECK(role IN ("администратор","менеджер","официант","повар","бармен","кладовщик")),
    created_at    TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS employees (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name  TEXT NOT NULL,
    phone      TEXT,
    role       TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS menu (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL,
    category TEXT,
    price    REAL NOT NULL,
    weight   TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS tables (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    number   INTEGER NOT NULL UNIQUE,
    capacity INTEGER NOT NULL,
    status   TEXT NOT NULL DEFAULT "свободен"
             CHECK(status IN ("свободен","занят","забронирован"))
)''')

c.execute('''CREATE TABLE IF NOT EXISTS reservations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id     INTEGER NOT NULL,
    guest_name   TEXT NOT NULL,
    guest_phone  TEXT,
    reserved_at  TEXT NOT NULL,
    guests_count INTEGER DEFAULT 1,
    comment      TEXT,
    FOREIGN KEY (table_id) REFERENCES tables(id) ON DELETE CASCADE
)''')

c.execute('''CREATE TABLE IF NOT EXISTS orders (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id   INTEGER NOT NULL,
    user_id    INTEGER,
    status     TEXT NOT NULL DEFAULT "открыт"
               CHECK(status IN ("открыт","готовится","готов","закрыт","отменен")),
    total      REAL DEFAULT 0,
    comment    TEXT,
    created_at TEXT,
    FOREIGN KEY (table_id) REFERENCES tables(id) ON DELETE RESTRICT,
    FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE SET NULL
)''')

c.execute('''CREATE TABLE IF NOT EXISTS order_items (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    menu_id  INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    price    REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id)  ON DELETE CASCADE,
    FOREIGN KEY (menu_id)  REFERENCES menu(id)    ON DELETE RESTRICT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS warehouse (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    unit           TEXT NOT NULL,
    quantity       REAL NOT NULL DEFAULT 0,
    min_quantity   REAL NOT NULL DEFAULT 0,
    price_per_unit REAL DEFAULT 0,
    expiry_date    TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS loyalty_guests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    phone         TEXT NOT NULL UNIQUE,
    email         TEXT,
    bonus_points  INTEGER DEFAULT 0,
    registered_at TEXT
)''')

# ── SEED DATA ─────────────────────────────────────────────────────────────────

if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
    c.executemany("INSERT INTO users (username,password_hash,full_name,role) VALUES (?,?,?,?)", [
        ('admin',   generate_password_hash('admin123'),   'Анна Воробьева',  'администратор'),
        ('manager', generate_password_hash('manager123'), 'Дмитрий Смирнов', 'менеджер'),
        ('waiter1', generate_password_hash('waiter123'),  'Мария Петрова',   'официант'),
        ('waiter2', generate_password_hash('waiter123'),  'Елена Козлова',   'официант'),
        ('cook1',   generate_password_hash('cook123'),    'Иван Иванов',     'повар'),
    ])

if c.execute("SELECT COUNT(*) FROM menu").fetchone()[0] == 0:
    c.executemany("INSERT INTO menu (name,category,price,weight) VALUES (?,?,?,?)", [
        ('Цезарь с курицей',        'Салаты',  450.00, '250г'),
        ('Греческий салат',          'Салаты',  380.00, '220г'),
        ('Теплый салат с говядиной', 'Салаты',  520.00, '280г'),
        ('Борщ украинский',          'Супы',    350.00, '300мл'),
        ('Солянка мясная',           'Супы',    420.00, '300мл'),
        ('Крем-суп грибной',         'Супы',    380.00, '280мл'),
        ('Стейк из говядины',        'Горячее', 890.00, '300г'),
        ('Котлета по-киевски',       'Горячее', 550.00, '250г'),
        ('Паста карбонара',          'Горячее', 480.00, '320г'),
        ('Картофель фри',            'Гарниры', 180.00, '150г'),
        ('Рис отварной',             'Гарниры', 120.00, '150г'),
        ('Овощи гриль',              'Гарниры', 220.00, '180г'),
        ('Эспрессо',                 'Напитки', 150.00, '50мл'),
        ('Капучино',                 'Напитки', 220.00, '200мл'),
        ('Латте',                    'Напитки', 250.00, '250мл'),
        ('Тирамису',                 'Десерты', 380.00, '150г'),
        ('Чизкейк',                  'Десерты', 350.00, '140г'),
        ('Медовик',                  'Десерты', 320.00, '130г'),
        ('Брускетта с помидорами',   'Закуски', 250.00, '120г'),
        ('Сырная тарелка',           'Закуски', 550.00, '200г'),
        ('Мясная тарелка',           'Закуски', 650.00, '250г'),
    ])

if c.execute("SELECT COUNT(*) FROM tables").fetchone()[0] == 0:
    c.executemany("INSERT INTO tables (number,capacity,status) VALUES (?,?,?)", [
        (1,2,'свободен'),(2,2,'свободен'),(3,4,'занят'),(4,4,'занят'),
        (5,4,'занят'),(6,4,'свободен'),(7,6,'занят'),(8,6,'свободен'),
        (9,6,'занят'),(10,8,'свободен'),(11,8,'занят'),(12,8,'занят'),
    ])

if c.execute("SELECT COUNT(*) FROM warehouse").fetchone()[0] == 0:
    c.executemany("INSERT INTO warehouse (name,unit,quantity,min_quantity,price_per_unit,expiry_date) VALUES (?,?,?,?,?,?)", [
        ('Говядина',         'кг',  45.0,  10.0, 650.0,  '2026-04-10'),
        ('Курица (филе)',     'кг',  38.0,  8.0,  280.0,  '2026-04-08'),
        ('Картофель',        'кг',  120.0, 20.0, 35.0,   '2026-05-01'),
        ('Помидоры',         'кг',  25.0,  5.0,  90.0,   '2026-04-07'),
        ('Огурцы',           'кг',  18.0,  5.0,  75.0,   '2026-04-09'),
        ('Мука пшеничная',   'кг',  80.0,  15.0, 55.0,   '2026-08-01'),
        ('Масло сливочное',  'кг',  12.0,  3.0,  520.0,  '2026-04-20'),
        ('Яйца',             'шт',  240.0, 50.0, 9.5,    '2026-04-15'),
        ('Сыр пармезан',     'кг',  8.5,   2.0,  1200.0, '2026-05-10'),
        ('Кофе (зерно)',     'кг',  15.0,  3.0,  1800.0, '2026-07-01'),
        ('Сахар',            'кг',  50.0,  10.0, 65.0,   '2026-12-01'),
        ('Соль',             'кг',  30.0,  5.0,  25.0,   '2027-01-01'),
        ('Оливковое масло',  'л',   8.0,   2.0,  650.0,  '2026-09-01'),
        ('Молоко',           'л',   40.0,  10.0, 85.0,   '2026-04-06'),
        ('Сливки 33%',       'л',   15.0,  4.0,  180.0,  '2026-04-08'),
        ('Грибы шампиньоны', 'кг',  12.0,  3.0,  160.0,  '2026-04-07'),
        ('Лосось',           'кг',  6.0,   2.0,  1100.0, '2026-04-05'),
        ('Тесто слоёное',    'кг',  8.0,   2.0,  220.0,  '2026-04-12'),
        ('Томатная паста',   'кг',  10.0,  2.0,  95.0,   '2026-10-01'),
        ('Чеснок',           'кг',  5.0,   1.0,  120.0,  '2026-06-01'),
    ])

if c.execute("SELECT COUNT(*) FROM loyalty_guests").fetchone()[0] == 0:
    c.executemany("INSERT INTO loyalty_guests (name,phone,email,bonus_points,registered_at) VALUES (?,?,?,?,?)", [
        ('Иванов Игорь',    '+7-900-111-22-33', 'ivanov@mail.ru',   1250, '2024-03-15'),
        ('Смирнова Анна',   '+7-900-222-33-44', 'smirnova@mail.ru', 870,  '2024-05-20'),
        ('Козлов Дмитрий',  '+7-900-333-44-55', '',                 430,  '2024-07-10'),
        ('Петрова Наталья', '+7-900-444-55-66', 'petrova@yandex.ru',2100, '2023-12-01'),
        ('Сидоров Артём',   '+7-900-555-66-77', '',                 150,  '2025-01-15'),
    ])

# Generate orders for analytics
if c.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0:
    user_ids = [r[0] for r in c.execute("SELECT id FROM users WHERE role IN ('официант')").fetchall()]
    table_ids= [r[0] for r in c.execute("SELECT id FROM tables").fetchall()]
    menu_ids = [r[0] for r in c.execute("SELECT id, price FROM menu").fetchall()]
    menu_prices = {r[0]: r[1] for r in c.execute("SELECT id, price FROM menu").fetchall()}

    import random
    for days_ago in range(30, 0, -1):
        dt = datetime.now() - timedelta(days=days_ago)
        for _ in range(random.randint(8, 18)):
            tid = random.choice(table_ids)
            uid = random.choice(user_ids) if user_ids else None
            sel_items = random.sample(list(menu_prices.keys()), random.randint(1, 4))
            total = sum(menu_prices[m] * random.randint(1, 3) for m in sel_items)
            ts = dt.strftime('%Y-%m-%d') + f' {random.randint(12,22):02d}:{random.randint(0,59):02d}:00'
            cur2 = c.execute(
                "INSERT INTO orders (table_id,user_id,status,total,comment,created_at) VALUES (?,?,?,?,?,?)",
                (tid, uid, 'закрыт', total, '', ts)
            )
            oid = cur2.lastrowid
            for mid in sel_items:
                qty = random.randint(1, 3)
                c.execute("INSERT INTO order_items (order_id,menu_id,quantity,price) VALUES (?,?,?,?)",
                          (oid, mid, qty, menu_prices[mid]))

    # A few active orders
    for tid, uid, status in [(3, user_ids[0] if user_ids else None, 'готовится'),
                              (5, user_ids[0] if user_ids else None, 'готов'),
                              (7, user_ids[0] if user_ids else None, 'открыт')]:
        sel_items = random.sample(list(menu_prices.keys()), 2)
        total = sum(menu_prices[m] for m in sel_items)
        cur2 = c.execute(
            "INSERT INTO orders (table_id,user_id,status,total,created_at) VALUES (?,?,?,?,?)",
            (tid, uid, status, total, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        oid = cur2.lastrowid
        for mid in sel_items:
            c.execute("INSERT INTO order_items (order_id,menu_id,quantity,price) VALUES (?,?,?,?)",
                      (oid, mid, 1, menu_prices[mid]))

conn.commit()
conn.close()
print("✓ База данных инициализирована")
print("\nТестовые аккаунты:")
print("  admin   / admin123   (администратор)")
print("  manager / manager123 (менеджер)")
print("  waiter1 / waiter123  (официант)")
