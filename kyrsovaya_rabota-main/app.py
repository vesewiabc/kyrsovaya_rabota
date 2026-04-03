from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB_PATH = "rest.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@app.route('/')
def index():
    db = get_db()
    categories = db.execute("SELECT DISTINCT category FROM menu ORDER BY category").fetchall()
    categories = [r['category'] for r in categories]
    db.close()
    return render_template('index.html', categories=categories)

@app.route('/menu')
def menu():
    db = get_db()
    category = request.args.get('category', '')
    if category:
        items = db.execute("SELECT * FROM menu WHERE category = ? ORDER BY name", (category,)).fetchall()
    else:
        items = db.execute("SELECT * FROM menu ORDER BY category, name").fetchall()
    categories = db.execute("SELECT DISTINCT category FROM menu ORDER BY category").fetchall()
    categories = [r['category'] for r in categories]
    db.close()
    return render_template('menu.html', items=items, categories=categories, active_category=category)

@app.route('/reserve')
def reserve():
    db = get_db()
    tables = db.execute("SELECT * FROM tables ORDER BY number").fetchall()
    db.close()
    return render_template('reserve.html', tables=tables)

@app.route('/api/tables')
def api_tables():
    db = get_db()
    date_str = request.args.get('date', '')
    guests = request.args.get('guests', 1, type=int)
    
    tables = db.execute("SELECT * FROM tables ORDER BY number").fetchall()
    result = []
    for t in tables:
        # Check reservations for this date
        booked = False
        if date_str:
            date_prefix = date_str[:10]  # YYYY-MM-DD
            res = db.execute(
                "SELECT id FROM reservations WHERE table_id = ? AND reserved_at LIKE ?",
                (t['id'], f"{date_prefix}%")
            ).fetchone()
            booked = res is not None

        result.append({
            'id': t['id'],
            'number': t['number'],
            'capacity': t['capacity'],
            'status': t['status'],
            'booked_on_date': booked,
            'suitable': t['capacity'] >= guests
        })
    db.close()
    return jsonify(result)

@app.route('/api/reserve', methods=['POST'])
def api_reserve():
    data = request.json
    table_id = data.get('table_id')
    guest_name = data.get('guest_name', '').strip()
    guest_phone = data.get('guest_phone', '').strip()
    reserved_at = data.get('reserved_at', '').strip()
    guests_count = data.get('guests_count', 1)
    comment = data.get('comment', '').strip()

    if not table_id or not guest_name or not reserved_at:
        return jsonify({'ok': False, 'error': 'Заполните обязательные поля'}), 400

    db = get_db()
    table = db.execute("SELECT * FROM tables WHERE id = ?", (table_id,)).fetchone()
    if not table:
        db.close()
        return jsonify({'ok': False, 'error': 'Столик не найден'}), 404

    # Check for existing reservation on same date/time
    date_prefix = reserved_at[:10]
    existing = db.execute(
        "SELECT id FROM reservations WHERE table_id = ? AND reserved_at LIKE ?",
        (table_id, f"{date_prefix}%")
    ).fetchone()
    if existing:
        db.close()
        return jsonify({'ok': False, 'error': 'Этот столик уже забронирован на выбранную дату'}), 409

    db.execute(
        "INSERT INTO reservations (table_id, guest_name, guest_phone, reserved_at, guests_count, comment) VALUES (?,?,?,?,?,?)",
        (table_id, guest_name, guest_phone, reserved_at, guests_count, comment)
    )
    # Update table status to 'забронирован'
    db.execute("UPDATE tables SET status = 'забронирован' WHERE id = ?", (table_id,))
    db.commit()
    db.close()
    return jsonify({'ok': True, 'message': f'Столик №{table["number"]} успешно забронирован!'})

@app.route('/api/menu')
def api_menu():
    db = get_db()
    category = request.args.get('category', '')
    if category:
        items = db.execute("SELECT * FROM menu WHERE category = ? ORDER BY name", (category,)).fetchall()
    else:
        items = db.execute("SELECT * FROM menu ORDER BY category, name").fetchall()
    db.close()
    return jsonify([dict(r) for r in items])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
