from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'gurman_secret_2026'
DB_PATH = "restaurant.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash('Недостаточно прав доступа', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ─── AUTH ────────────────────────────────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm  = request.form.get('confirm', '').strip()
        full_name = request.form.get('full_name', '').strip()
        role     = request.form.get('role', 'официант')

        if not username or not password or not full_name:
            flash('Заполните все обязательные поля', 'error')
            return render_template('register.html')
        if password != confirm:
            flash('Пароли не совпадают', 'error')
            return render_template('register.html')
        if len(password) < 6:
            flash('Пароль должен быть не менее 6 символов', 'error')
            return render_template('register.html')

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            db.close()
            flash('Пользователь с таким логином уже существует', 'error')
            return render_template('register.html')

        hashed = generate_password_hash(password)
        db.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?,?,?,?)",
            (username, hashed, full_name, role)
        )
        db.commit()
        db.close()
        flash('Регистрация успешна! Войдите в систему.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        db.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id']   = user['id']
            session['username']  = user['username']
            session['full_name'] = user['full_name']
            session['role']      = user['role']
            flash(f'Добро пожаловать, {user["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Неверный логин или пароль', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ─── MAIN PAGES ──────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def dashboard():
    db = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    stats = {
        'tables_free':  db.execute("SELECT COUNT(*) FROM tables WHERE status='свободен'").fetchone()[0],
        'tables_busy':  db.execute("SELECT COUNT(*) FROM tables WHERE status='занят'").fetchone()[0],
        'orders_open':  db.execute("SELECT COUNT(*) FROM orders WHERE status IN ('открыт','готовится','готов')").fetchone()[0],
        'revenue_today':db.execute(
            "SELECT COALESCE(SUM(total),0) FROM orders WHERE status='закрыт' AND created_at LIKE ?",
            (f'{today}%',)
        ).fetchone()[0],
        'reservations_today': db.execute(
            "SELECT COUNT(*) FROM reservations WHERE reserved_at LIKE ?", (f'{today}%',)
        ).fetchone()[0],
    }
    active_orders = db.execute("""
        SELECT o.id, t.number as table_num, o.status, o.total, o.created_at,
               u.full_name as waiter
        FROM orders o
        JOIN tables t ON o.table_id = t.id
        LEFT JOIN users u ON o.user_id = u.id
        WHERE o.status IN ('открыт','готовится','готов')
        ORDER BY o.created_at DESC LIMIT 10
    """).fetchall()
    db.close()
    return render_template('dashboard.html', stats=stats, active_orders=active_orders)


# ─── MENU ────────────────────────────────────────────────────────────────────

@app.route('/menu')
@login_required
def menu():
    db = get_db()
    category = request.args.get('category', '')
    if category:
        items = db.execute("SELECT * FROM menu WHERE category=? ORDER BY name", (category,)).fetchall()
    else:
        items = db.execute("SELECT * FROM menu ORDER BY category, name").fetchall()
    categories = [r['category'] for r in db.execute("SELECT DISTINCT category FROM menu ORDER BY category").fetchall()]
    db.close()
    return render_template('menu.html', items=items, categories=categories, active_category=category)


@app.route('/menu/add', methods=['POST'])
@login_required
@role_required('администратор', 'менеджер')
def menu_add():
    data = request.json
    db = get_db()
    db.execute("INSERT INTO menu (name, category, price, weight) VALUES (?,?,?,?)",
               (data['name'], data['category'], data['price'], data.get('weight', '')))
    db.commit()
    db.close()
    return jsonify({'ok': True})


@app.route('/menu/delete/<int:item_id>', methods=['DELETE'])
@login_required
@role_required('администратор', 'менеджер')
def menu_delete(item_id):
    db = get_db()
    db.execute("DELETE FROM menu WHERE id=?", (item_id,))
    db.commit()
    db.close()
    return jsonify({'ok': True})


# ─── ORDERS ──────────────────────────────────────────────────────────────────

@app.route('/orders')
@login_required
def orders():
    db = get_db()
    status_filter = request.args.get('status', '')
    if status_filter:
        rows = db.execute("""
            SELECT o.*, t.number as table_num, u.full_name as waiter
            FROM orders o JOIN tables t ON o.table_id=t.id
            LEFT JOIN users u ON o.user_id=u.id
            WHERE o.status=? ORDER BY o.created_at DESC
        """, (status_filter,)).fetchall()
    else:
        rows = db.execute("""
            SELECT o.*, t.number as table_num, u.full_name as waiter
            FROM orders o JOIN tables t ON o.table_id=t.id
            LEFT JOIN users u ON o.user_id=u.id
            ORDER BY o.created_at DESC LIMIT 50
        """).fetchall()
    tables = db.execute("SELECT * FROM tables WHERE status != 'занят' OR id IN (SELECT table_id FROM orders WHERE status NOT IN ('закрыт','отменен'))").fetchall()
    menu_items = db.execute("SELECT * FROM menu ORDER BY category, name").fetchall()
    db.close()
    return render_template('orders.html', orders=rows, tables=tables, menu_items=menu_items, status_filter=status_filter)


@app.route('/api/orders/create', methods=['POST'])
@login_required
def api_order_create():
    data = request.json
    table_id = data.get('table_id')
    items    = data.get('items', [])
    comment  = data.get('comment', '')

    if not table_id or not items:
        return jsonify({'ok': False, 'error': 'Укажите столик и позиции'}), 400

    db = get_db()
    total = 0
    for it in items:
        menu_item = db.execute("SELECT price FROM menu WHERE id=?", (it['menu_id'],)).fetchone()
        if menu_item:
            total += menu_item['price'] * it['quantity']

    cur = db.execute(
        "INSERT INTO orders (table_id, user_id, status, total, comment, created_at) VALUES (?,?,?,?,?,?)",
        (table_id, session['user_id'], 'открыт', total, comment, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    order_id = cur.lastrowid

    for it in items:
        menu_item = db.execute("SELECT price FROM menu WHERE id=?", (it['menu_id'],)).fetchone()
        if menu_item:
            db.execute("INSERT INTO order_items (order_id, menu_id, quantity, price) VALUES (?,?,?,?)",
                       (order_id, it['menu_id'], it['quantity'], menu_item['price']))

    db.execute("UPDATE tables SET status='занят' WHERE id=?", (table_id,))
    db.commit()
    db.close()
    return jsonify({'ok': True, 'order_id': order_id})


@app.route('/api/orders/<int:order_id>/status', methods=['POST'])
@login_required
def api_order_status(order_id):
    new_status = request.json.get('status')
    valid = ('открыт', 'готовится', 'готов', 'закрыт', 'отменен')
    if new_status not in valid:
        return jsonify({'ok': False, 'error': 'Неверный статус'}), 400
    db = get_db()
    order = db.execute("SELECT table_id FROM orders WHERE id=?", (order_id,)).fetchone()
    db.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order_id))
    if new_status in ('закрыт', 'отменен') and order:
        # free the table if no other active orders
        other = db.execute(
            "SELECT id FROM orders WHERE table_id=? AND status NOT IN ('закрыт','отменен') AND id!=?",
            (order['table_id'], order_id)
        ).fetchone()
        if not other:
            db.execute("UPDATE tables SET status='свободен' WHERE id=?", (order['table_id'],))
    db.commit()
    db.close()
    return jsonify({'ok': True})


@app.route('/api/orders/<int:order_id>')
@login_required
def api_order_detail(order_id):
    db = get_db()
    order = db.execute("""
        SELECT o.*, t.number as table_num, u.full_name as waiter
        FROM orders o JOIN tables t ON o.table_id=t.id
        LEFT JOIN users u ON o.user_id=u.id
        WHERE o.id=?
    """, (order_id,)).fetchone()
    if not order:
        return jsonify({'ok': False}), 404
    items = db.execute("""
        SELECT oi.*, m.name, m.category
        FROM order_items oi JOIN menu m ON oi.menu_id=m.id
        WHERE oi.order_id=?
    """, (order_id,)).fetchall()
    db.close()
    return jsonify({'ok': True, 'order': dict(order), 'items': [dict(i) for i in items]})


# ─── RESERVATIONS ────────────────────────────────────────────────────────────

@app.route('/reserve')
@login_required
def reserve():
    db = get_db()
    tables = db.execute("SELECT * FROM tables ORDER BY number").fetchall()
    reservations = db.execute("""
        SELECT r.*, t.number as table_num
        FROM reservations r JOIN tables t ON r.table_id=t.id
        ORDER BY r.reserved_at DESC LIMIT 30
    """).fetchall()
    db.close()
    return render_template('reserve.html', tables=tables, reservations=reservations)


@app.route('/api/tables')
@login_required
def api_tables():
    db = get_db()
    date_str = request.args.get('date', '')
    guests   = request.args.get('guests', 1, type=int)
    tables   = db.execute("SELECT * FROM tables ORDER BY number").fetchall()
    result = []
    for t in tables:
        booked = False
        if date_str:
            res = db.execute(
                "SELECT id FROM reservations WHERE table_id=? AND reserved_at LIKE ?",
                (t['id'], f"{date_str[:10]}%")
            ).fetchone()
            booked = res is not None
        result.append({
            'id': t['id'], 'number': t['number'], 'capacity': t['capacity'],
            'status': t['status'], 'booked_on_date': booked, 'suitable': t['capacity'] >= guests
        })
    db.close()
    return jsonify(result)


@app.route('/api/reserve', methods=['POST'])
@login_required
def api_reserve():
    data = request.json
    table_id    = data.get('table_id')
    guest_name  = data.get('guest_name', '').strip()
    guest_phone = data.get('guest_phone', '').strip()
    reserved_at = data.get('reserved_at', '').strip()
    guests_count= data.get('guests_count', 1)
    comment     = data.get('comment', '').strip()

    if not table_id or not guest_name or not reserved_at:
        return jsonify({'ok': False, 'error': 'Заполните обязательные поля'}), 400

    db = get_db()
    existing = db.execute(
        "SELECT id FROM reservations WHERE table_id=? AND reserved_at LIKE ?",
        (table_id, f"{reserved_at[:10]}%")
    ).fetchone()
    if existing:
        db.close()
        return jsonify({'ok': False, 'error': 'Столик уже забронирован на эту дату'}), 409

    db.execute(
        "INSERT INTO reservations (table_id, guest_name, guest_phone, reserved_at, guests_count, comment) VALUES (?,?,?,?,?,?)",
        (table_id, guest_name, guest_phone, reserved_at, guests_count, comment)
    )
    db.execute("UPDATE tables SET status='забронирован' WHERE id=?", (table_id,))
    db.commit()
    table = db.execute("SELECT number FROM tables WHERE id=?", (table_id,)).fetchone()
    db.close()
    return jsonify({'ok': True, 'message': f'Столик №{table["number"]} успешно забронирован!'})


@app.route('/api/reserve/<int:res_id>/cancel', methods=['DELETE'])
@login_required
def api_reserve_cancel(res_id):
    db = get_db()
    res = db.execute("SELECT table_id FROM reservations WHERE id=?", (res_id,)).fetchone()
    if res:
        db.execute("DELETE FROM reservations WHERE id=?", (res_id,))
        db.execute("UPDATE tables SET status='свободен' WHERE id=?", (res['table_id'],))
        db.commit()
    db.close()
    return jsonify({'ok': True})


# ─── WAREHOUSE ───────────────────────────────────────────────────────────────

@app.route('/warehouse')
@login_required
def warehouse():
    db = get_db()
    search = request.args.get('q', '')
    if search:
        items = db.execute(
            "SELECT * FROM warehouse WHERE name LIKE ? ORDER BY name",
            (f'%{search}%',)
        ).fetchall()
    else:
        items = db.execute("SELECT * FROM warehouse ORDER BY name").fetchall()
    db.close()
    return render_template('warehouse.html', items=items, search=search)


@app.route('/api/warehouse/add', methods=['POST'])
@login_required
@role_required('администратор', 'менеджер', 'кладовщик')
def api_warehouse_add():
    data = request.json
    db = get_db()
    db.execute(
        "INSERT INTO warehouse (name, unit, quantity, min_quantity, price_per_unit, expiry_date) VALUES (?,?,?,?,?,?)",
        (data['name'], data['unit'], data['quantity'], data.get('min_quantity', 0),
         data.get('price_per_unit', 0), data.get('expiry_date', ''))
    )
    db.commit()
    db.close()
    return jsonify({'ok': True})


@app.route('/api/warehouse/<int:item_id>/update', methods=['POST'])
@login_required
@role_required('администратор', 'менеджер', 'кладовщик')
def api_warehouse_update(item_id):
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE warehouse SET quantity=?, expiry_date=? WHERE id=?",
        (data['quantity'], data.get('expiry_date', ''), item_id)
    )
    db.commit()
    db.close()
    return jsonify({'ok': True})


@app.route('/api/warehouse/<int:item_id>', methods=['DELETE'])
@login_required
@role_required('администратор', 'менеджер')
def api_warehouse_delete(item_id):
    db = get_db()
    db.execute("DELETE FROM warehouse WHERE id=?", (item_id,))
    db.commit()
    db.close()
    return jsonify({'ok': True})


# ─── STAFF ───────────────────────────────────────────────────────────────────

@app.route('/staff')
@login_required
@role_required('администратор', 'менеджер')
def staff():
    db = get_db()
    employees = db.execute("SELECT * FROM employees ORDER BY last_name").fetchall()
    users     = db.execute("SELECT id, username, full_name, role, created_at FROM users ORDER BY full_name").fetchall()
    db.close()
    return render_template('staff.html', employees=employees, users=users)


# ─── ANALYTICS ───────────────────────────────────────────────────────────────

@app.route('/analytics')
@login_required
@role_required('администратор', 'менеджер')
def analytics():
    db = get_db()
    # Revenue by day (last 7 days)
    revenue_days = db.execute("""
        SELECT substr(created_at,1,10) as day, SUM(total) as revenue, COUNT(*) as cnt
        FROM orders WHERE status='закрыт' AND created_at >= date('now','-7 days')
        GROUP BY day ORDER BY day
    """).fetchall()
    # Top dishes
    top_dishes = db.execute("""
        SELECT m.name, SUM(oi.quantity) as sold, SUM(oi.quantity * oi.price) as revenue
        FROM order_items oi JOIN menu m ON oi.menu_id=m.id
        JOIN orders o ON oi.order_id=o.id
        WHERE o.status='закрыт'
        GROUP BY m.id ORDER BY sold DESC LIMIT 10
    """).fetchall()
    # Revenue by category
    by_category = db.execute("""
        SELECT m.category, SUM(oi.quantity * oi.price) as revenue
        FROM order_items oi JOIN menu m ON oi.menu_id=m.id
        JOIN orders o ON oi.order_id=o.id
        WHERE o.status='закрыт'
        GROUP BY m.category ORDER BY revenue DESC
    """).fetchall()
    # General stats
    total_revenue = db.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status='закрыт'").fetchone()[0]
    total_orders  = db.execute("SELECT COUNT(*) FROM orders WHERE status='закрыт'").fetchone()[0]
    avg_check     = (total_revenue / total_orders) if total_orders else 0
    db.close()
    return render_template('analytics.html',
        revenue_days=[dict(r) for r in revenue_days],
        top_dishes=[dict(r) for r in top_dishes],
        by_category=[dict(r) for r in by_category],
        total_revenue=total_revenue,
        total_orders=total_orders, avg_check=avg_check)


@app.route('/api/analytics/summary')
@login_required
def api_analytics_summary():
    db = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    data = {
        'revenue_today': db.execute(
            "SELECT COALESCE(SUM(total),0) FROM orders WHERE status='закрыт' AND created_at LIKE ?",
            (f'{today}%',)
        ).fetchone()[0],
        'orders_today': db.execute(
            "SELECT COUNT(*) FROM orders WHERE created_at LIKE ?", (f'{today}%',)
        ).fetchone()[0],
        'revenue_month': db.execute(
            "SELECT COALESCE(SUM(total),0) FROM orders WHERE status='закрыт' AND created_at LIKE ?",
            (f"{today[:7]}%",)
        ).fetchone()[0],
    }
    db.close()
    return jsonify(data)


# ─── LOYALTY ─────────────────────────────────────────────────────────────────

@app.route('/loyalty')
@login_required
def loyalty():
    db = get_db()
    search = request.args.get('q', '')
    if search:
        guests = db.execute(
            "SELECT * FROM loyalty_guests WHERE name LIKE ? OR phone LIKE ? ORDER BY name",
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        guests = db.execute("SELECT * FROM loyalty_guests ORDER BY bonus_points DESC").fetchall()
    db.close()
    return render_template('loyalty.html', guests=guests, search=search)


@app.route('/api/loyalty/add', methods=['POST'])
@login_required
def api_loyalty_add():
    data = request.json
    db = get_db()
    existing = db.execute("SELECT id FROM loyalty_guests WHERE phone=?", (data['phone'],)).fetchone()
    if existing:
        db.close()
        return jsonify({'ok': False, 'error': 'Гость с таким телефоном уже зарегистрирован'}), 409
    db.execute(
        "INSERT INTO loyalty_guests (name, phone, email, bonus_points, registered_at) VALUES (?,?,?,?,?)",
        (data['name'], data['phone'], data.get('email', ''), 0, datetime.now().strftime('%Y-%m-%d'))
    )
    db.commit()
    db.close()
    return jsonify({'ok': True})


@app.route('/api/loyalty/<int:guest_id>/points', methods=['POST'])
@login_required
def api_loyalty_points(guest_id):
    delta = request.json.get('delta', 0)
    db = get_db()
    db.execute("UPDATE loyalty_guests SET bonus_points = bonus_points + ? WHERE id=?", (delta, guest_id))
    db.commit()
    new_pts = db.execute("SELECT bonus_points FROM loyalty_guests WHERE id=?", (guest_id,)).fetchone()[0]
    db.close()
    return jsonify({'ok': True, 'bonus_points': new_pts})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
