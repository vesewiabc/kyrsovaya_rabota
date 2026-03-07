import sqlite3

connection = sqlite3.connect("rest.db")
cursor = connection.cursor()

cursor.execute("PRAGMA foreign_keys = ON")

cursor.execute('''
CREATE TABLE IF NOT EXISTS employees (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name  TEXT NOT NULL,
    phone      TEXT,
    role       TEXT
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS menu (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL,
    category TEXT,
    price    REAL NOT NULL,
    weight   TEXT
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS tables (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    number   INTEGER NOT NULL UNIQUE,
    capacity INTEGER NOT NULL,
    status   TEXT NOT NULL DEFAULT "свободен"
             CHECK(status IN ("свободен", "занят", "забронирован"))
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS reservations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id     INTEGER NOT NULL,
    guest_name   TEXT NOT NULL,
    guest_phone  TEXT,
    reserved_at  TEXT NOT NULL,
    guests_count INTEGER DEFAULT 1,
    comment      TEXT,
    FOREIGN KEY (table_id) REFERENCES tables(id) ON DELETE CASCADE
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id    INTEGER NOT NULL,
    employee_id INTEGER,
    status      TEXT NOT NULL DEFAULT "открыт"
                CHECK(status IN ("открыт", "готовится", "готов", "закрыт", "отменен")),
    total       REAL DEFAULT 0,
    comment     TEXT,
    created_at  TEXT,
    FOREIGN KEY (table_id)    REFERENCES tables(id)    ON DELETE RESTRICT,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE SET NULL
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS order_items (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    menu_id  INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    price    REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (menu_id)  REFERENCES menu(id)   ON DELETE RESTRICT
)''')

if cursor.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 0:
    cursor.executemany(
        "INSERT INTO employees (first_name, last_name, phone, role) VALUES (?,?,?,?)",
        [
            ('Петр',    'Петров',    '7-999-234-56-78',  'Повар'),
            ('Иван',    'Иванов',    '+7-999-123-45-67', 'Повар'),
            ('Мария',   'Петрова',   '+7-999-234-56-78', 'Официант'),
            ('Алексей', 'Сидоров',   '+7-999-345-67-89', 'Шеф-повар'),
            ('Елена',   'Козлова',   '+7-999-456-78-90', 'Официант'),
            ('Дмитрий', 'Смирнов',   '+7-999-567-89-01', 'Бармен'),
            ('Анна',    'Воробьева', '+7-999-678-90-12', 'Администратор'),
            ('Сергей',  'Михайлов',  '+7-999-789-01-23', 'Повар'),
            ('Ольга',   'Новикова',  '+7-999-890-12-34', 'Официант'),
            ('Павел',   'Соколов',   '+7-999-901-23-45', 'Повар'),
            ('Наталья', 'Морозова',  '+7-999-012-34-56', 'Официант'),
        ]
    )

if cursor.execute("SELECT COUNT(*) FROM menu").fetchone()[0] == 0:
    cursor.executemany(
        "INSERT INTO menu (name, category, price, weight) VALUES (?,?,?,?)",
        [
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
        ]
    )

if cursor.execute("SELECT COUNT(*) FROM tables").fetchone()[0] == 0:
    cursor.executemany(
        "INSERT INTO tables (number, capacity, status) VALUES (?,?,?)",
        [
            (1,  2, 'свободен'),
            (2,  2, 'свободен'),
            (3,  4, 'занят'),
            (4,  4, 'занят'),
            (5,  4, 'занят'),
            (6,  4, 'свободен'),
            (7,  6, 'занят'),
            (8,  6, 'свободен'),
            (9,  6, 'занят'),
            (10, 8, 'свободен'),
            (11, 8, 'занят'),
            (12, 8, 'занят'),
        ]
    )

if cursor.execute("SELECT COUNT(*) FROM reservations").fetchone()[0] == 0:
    cursor.executemany(
        "INSERT INTO reservations (table_id, guest_name, guest_phone, reserved_at, guests_count, comment) VALUES (?,?,?,?,?,?)",
        [
            (6,  'Иванов Игорь',   '+7-900-111-22-33', '2025-06-15 19:00', 3, 'День рождения'),
            (8,  'Смирнова Анна',  '+7-900-222-33-44', '2025-06-15 20:00', 5, 'Корпоратив'),
            (10, 'Козлов Дмитрий', '+7-900-333-44-55', '2025-06-16 13:00', 2, ''),
        ]
    )

if cursor.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0:
    cursor.executemany(
        "INSERT INTO orders (table_id, employee_id, status, total, comment) VALUES (?,?,?,?,?)",
        [
            (5,  3, 'готовится', 1250, 'Без лука'),
            (3,  5, 'готов',     890,  ''),
            (7,  3, 'готовится', 2340, 'День рождения, нужна свечка'),
            (1,  9, 'закрыт',    3450, ''),
            (4,  3, 'закрыт',    980,  'Острее'),
            (6,  5, 'закрыт',    2150, 'Вегетарианское'),
            (3,  9, 'закрыт',    1560, ''),
            (5, 11, 'закрыт',    3240, ''),
            (7,  3, 'отменен',   0,    'Столик у окна'),
            (11, 9, 'закрыт',    5430, 'Компания из 6 человек'),
            (12, 5, 'закрыт',    6780, 'Бизнес-ланч'),
            (4, 11, 'готов',     3450, ''),
            (2,  3, 'закрыт',    890,  ''),
            (5, 11, 'закрыт',    2340, ''),
            (9,  5, 'готов',     3780, ''),
        ]
    )

if cursor.execute("SELECT COUNT(*) FROM order_items").fetchone()[0] == 0:
    cursor.executemany(
        "INSERT INTO order_items (order_id, menu_id, quantity, price) VALUES (?,?,?,?)",
        [
            (1,  7,  1, 890), (1,  10, 2, 180),
            (2,  7,  1, 890),
            (3,  8,  2, 550), (3,  16, 2, 380),
            (4,  1,  1, 450), (4,  7,  2, 890),
            (5,  4,  1, 350), (5,  8,  1, 550),
            (6,  2,  1, 380), (6,  12, 1, 220),
            (7,  5,  1, 420), (7,  9,  1, 480),
            (8,  7,  1, 890), (8,  20, 1, 550),
            (10, 7,  2, 890), (10, 3,  1, 520),
            (11, 21, 2, 650), (11, 7,  3, 890),
            (12, 7,  1, 890), (12, 9,  2, 480),
            (13, 4,  1, 350), (13, 13, 2, 150),
            (14, 8,  1, 550), (14, 10, 2, 180),
            (15, 6,  1, 380), (15, 9,  1, 480),
        ]
    )

connection.commit()
connection.close()
print("Database initialized successfully!")
