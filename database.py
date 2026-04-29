import sqlite3
import csv
import os
import sys
from datetime import datetime


def get_db_path():
    if getattr(sys, "frozen", False):
        base = os.path.join(os.environ.get("APPDATA", os.path.dirname(sys.executable)),
                            "InstrumentTracker")
        os.makedirs(base, exist_ok=True)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "band_tracker.db")


def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                student_id TEXT UNIQUE NOT NULL,
                grade TEXT
            );

            CREATE TABLE IF NOT EXISTS instruments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                model TEXT,
                serial_number TEXT,
                qr_code_text TEXT,
                status TEXT DEFAULT 'Available',
                current_student_id INTEGER REFERENCES students(id) ON DELETE SET NULL,
                last_checked_out TEXT,
                last_checked_in TEXT
            );

            CREATE TABLE IF NOT EXISTS checkout_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument_id INTEGER NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
                student_id INTEGER REFERENCES students(id) ON DELETE SET NULL,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                notes TEXT,
                condition_photo_path TEXT,
                contract_photo_path TEXT,
                repair_invoice_path TEXT
            );

            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                instrument_id INTEGER REFERENCES instruments(id) ON DELETE SET NULL,
                scan_file_path TEXT,
                notes TEXT,
                date TEXT NOT NULL,
                active INTEGER DEFAULT 1
            );
        """)
        # Migrate existing DBs that predate the photo columns
        cols = [r[1] for r in conn.execute("PRAGMA table_info(checkout_history)")]
        if "condition_photo_path" not in cols:
            conn.execute("ALTER TABLE checkout_history ADD COLUMN condition_photo_path TEXT")
        if "contract_photo_path" not in cols:
            conn.execute("ALTER TABLE checkout_history ADD COLUMN contract_photo_path TEXT")
        if "repair_invoice_path" not in cols:
            conn.execute("ALTER TABLE checkout_history ADD COLUMN repair_invoice_path TEXT")


# ── Students ──────────────────────────────────────────────────────────────────

def add_student(name, student_id, grade):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO students (name, student_id, grade) VALUES (?, ?, ?)",
            (name, student_id, grade),
        )


def get_all_students():
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM students ORDER BY name COLLATE NOCASE"
        ).fetchall()


def get_student_roster():
    with get_connection() as conn:
        return conn.execute("""
            SELECT s.*,
                MIN(i.id)   AS instrument_id,
                MIN(i.name) AS instrument_name,
                MIN(i.model) AS model,
                MIN(i.serial_number) AS serial_number,
                COUNT(i.id) AS instrument_count
            FROM students s
            LEFT JOIN instruments i ON i.current_student_id = s.id
            GROUP BY s.id
            ORDER BY s.name COLLATE NOCASE
        """).fetchall()


def get_student_by_id(student_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM students WHERE id = ?", (student_id,)
        ).fetchone()


def update_student(student_db_id, name, student_id, grade):
    with get_connection() as conn:
        conn.execute(
            "UPDATE students SET name=?, student_id=?, grade=? WHERE id=?",
            (name, student_id, grade, student_db_id),
        )


def delete_student(student_db_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM students WHERE id=?", (student_db_id,))


def import_students_from_csv(filepath):
    added, skipped = 0, 0
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        with get_connection() as conn:
            for row in reader:
                try:
                    name = row.get("Name", "").strip()
                    sid = row.get("Student ID", "").strip()
                    grade = row.get("Grade", "").strip()
                    if not name or not sid:
                        skipped += 1
                        continue
                    conn.execute(
                        "INSERT OR IGNORE INTO students (name, student_id, grade) VALUES (?, ?, ?)",
                        (name, sid, grade),
                    )
                    added += 1
                except Exception:
                    skipped += 1
    return added, skipped


def export_students_to_csv(filepath):
    students = get_all_students()
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Student ID", "Grade"])
        for s in students:
            writer.writerow([s["name"], s["student_id"], s["grade"]])
    return len(students)


# ── Instruments ───────────────────────────────────────────────────────────────

def add_instrument(name, model, serial_number):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO instruments (name, model, serial_number, qr_code_text) VALUES (?, ?, ?, ?)",
            (name, model, serial_number, serial_number),
        )


def get_all_instruments():
    with get_connection() as conn:
        return conn.execute("""
            SELECT i.*, s.name AS student_name
            FROM instruments i
            LEFT JOIN students s ON i.current_student_id = s.id
            ORDER BY i.name COLLATE NOCASE, i.model COLLATE NOCASE
        """).fetchall()


def get_current_checkouts():
    with get_connection() as conn:
        return conn.execute("""
            SELECT i.*, s.name AS student_name, s.student_id AS student_number, s.grade
            FROM instruments i
            JOIN students s ON i.current_student_id = s.id
            WHERE i.status = 'Checked Out'
            ORDER BY s.name COLLATE NOCASE
        """).fetchall()


def get_needs_repair():
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM instruments
            WHERE status IN ('Needs Repair', 'Out for Repair')
            ORDER BY name COLLATE NOCASE
        """).fetchall()


def get_available_instruments():
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM instruments
            WHERE status = 'Available'
            ORDER BY name COLLATE NOCASE
        """).fetchall()


def get_summer_hold_instruments():
    with get_connection() as conn:
        return conn.execute("""
            SELECT i.*, s.name AS student_name
            FROM instruments i
            LEFT JOIN students s ON i.current_student_id = s.id
            WHERE i.status = 'Summer Hold'
            ORDER BY i.name COLLATE NOCASE
        """).fetchall()


def get_instrument_by_id(instrument_db_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM instruments WHERE id=?", (instrument_db_id,)
        ).fetchone()


def get_instrument_by_qr(qr_text):
    with get_connection() as conn:
        return conn.execute(
            "SELECT i.*, s.name AS student_name FROM instruments i "
            "LEFT JOIN students s ON i.current_student_id = s.id "
            "WHERE i.qr_code_text = ?",
            (qr_text,),
        ).fetchone()


def update_instrument(instrument_db_id, name, model, serial_number):
    with get_connection() as conn:
        conn.execute(
            "UPDATE instruments SET name=?, model=?, serial_number=?, qr_code_text=? WHERE id=?",
            (name, model, serial_number, serial_number, instrument_db_id),
        )


def update_instrument_status(instrument_db_id, status):
    with get_connection() as conn:
        if status == "Available":
            # Clearing to available also removes the assigned student
            conn.execute(
                "UPDATE instruments SET status=?, current_student_id=NULL WHERE id=?",
                (status, instrument_db_id),
            )
        else:
            conn.execute(
                "UPDATE instruments SET status=? WHERE id=?",
                (status, instrument_db_id),
            )


def delete_instrument(instrument_db_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM instruments WHERE id=?", (instrument_db_id,))


def resume_checkout(instrument_db_id):
    """Flip a Summer Hold instrument back to Checked Out for the same student."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with get_connection() as conn:
        row = conn.execute(
            "SELECT current_student_id FROM instruments WHERE id=?", (instrument_db_id,)
        ).fetchone()
        if not row or not row["current_student_id"]:
            return
        conn.execute(
            "UPDATE instruments SET status='Checked Out', last_checked_out=? WHERE id=?",
            (now, instrument_db_id),
        )
        conn.execute(
            "INSERT INTO checkout_history "
            "(instrument_id, student_id, action, timestamp, notes) "
            "VALUES (?, ?, 'check_out', ?, 'Resumed from Summer Hold')",
            (instrument_db_id, row["current_student_id"], now),
        )


def checkout_instrument(instrument_db_id, student_db_id, notes="",
                        condition_photo_path="", contract_photo_path=""):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with get_connection() as conn:
        conn.execute(
            "UPDATE instruments SET status='Checked Out', current_student_id=?, last_checked_out=? WHERE id=?",
            (student_db_id, now, instrument_db_id),
        )
        conn.execute(
            "INSERT INTO checkout_history "
            "(instrument_id, student_id, action, timestamp, notes, condition_photo_path, contract_photo_path) "
            "VALUES (?, ?, 'check_out', ?, ?, ?, ?)",
            (instrument_db_id, student_db_id, now, notes,
             condition_photo_path or None, contract_photo_path or None),
        )


def checkin_instrument(instrument_db_id, notes="", condition_photo_path=""):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with get_connection() as conn:
        instr = conn.execute(
            "SELECT current_student_id FROM instruments WHERE id=?", (instrument_db_id,)
        ).fetchone()
        student_db_id = instr["current_student_id"] if instr else None
        conn.execute(
            "UPDATE instruments SET status='Available', current_student_id=NULL, last_checked_in=? WHERE id=?",
            (now, instrument_db_id),
        )
        conn.execute(
            "INSERT INTO checkout_history (instrument_id, student_id, action, timestamp, notes, condition_photo_path) "
            "VALUES (?, ?, 'check_in', ?, ?, ?)",
            (instrument_db_id, student_db_id, now, notes, condition_photo_path or None),
        )
        conn.execute(
            "UPDATE contracts SET active = 0 WHERE instrument_id = ? AND active = 1",
            (instrument_db_id,),
        )


def log_repair_note(instrument_db_id, status, notes):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    action = "needs_repair" if status == "Needs Repair" else "out_for_repair"
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO checkout_history (instrument_id, student_id, action, timestamp, notes) "
            "VALUES (?, NULL, ?, ?, ?)",
            (instrument_db_id, action, now, notes),
        )


def log_repair_return(instrument_db_id, notes="", invoice_path=""):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with get_connection() as conn:
        conn.execute(
            "UPDATE instruments SET status='Available', current_student_id=NULL WHERE id=?",
            (instrument_db_id,),
        )
        conn.execute(
            "INSERT INTO checkout_history "
            "(instrument_id, student_id, action, timestamp, notes, repair_invoice_path) "
            "VALUES (?, NULL, 'repair_returned', ?, ?, ?)",
            (instrument_db_id, now, notes or None, invoice_path or None),
        )


def get_instrument_ids_with_repair_invoices():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT instrument_id FROM checkout_history "
            "WHERE repair_invoice_path IS NOT NULL AND repair_invoice_path != ''"
        ).fetchall()
        return {r["instrument_id"] for r in rows}


def import_instruments_from_csv(filepath):
    added, skipped = 0, 0
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        with get_connection() as conn:
            for row in reader:
                try:
                    name = row.get("Name", "").strip()
                    model = row.get("Model", "").strip()
                    serial = row.get("Serial Number", "").strip()
                    qr = row.get("QR Code Text", "").strip()
                    if not name:
                        skipped += 1
                        continue
                    conn.execute(
                        "INSERT INTO instruments (name, model, serial_number, qr_code_text) VALUES (?, ?, ?, ?)",
                        (name, model, serial, qr),
                    )
                    added += 1
                except Exception:
                    skipped += 1
    return added, skipped


def export_instruments_to_csv(filepath):
    instruments = get_all_instruments()
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Model", "Serial Number", "QR Code Text", "Status", "Current Student"])
        for i in instruments:
            writer.writerow([
                i["name"], i["model"], i["serial_number"], i["qr_code_text"],
                i["status"], i["student_name"] or "",
            ])
    return len(instruments)


# ── History ───────────────────────────────────────────────────────────────────

def get_student_history(student_db_id):
    with get_connection() as conn:
        return conn.execute("""
            SELECT h.*, i.name AS instrument_name, i.model, i.serial_number
            FROM checkout_history h
            LEFT JOIN instruments i ON h.instrument_id = i.id
            WHERE h.student_id = ?
            ORDER BY h.timestamp DESC
        """, (student_db_id,)).fetchall()


def get_instrument_history(instrument_db_id):
    with get_connection() as conn:
        return conn.execute("""
            SELECT h.*, s.name AS student_name
            FROM checkout_history h
            LEFT JOIN students s ON h.student_id = s.id
            WHERE h.instrument_id = ?
            ORDER BY h.timestamp DESC
        """, (instrument_db_id,)).fetchall()


# ── Contracts ─────────────────────────────────────────────────────────────────

def add_contract(student_db_id, instrument_db_id, scan_file_path, notes):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO contracts (student_id, instrument_id, scan_file_path, notes, date, active) VALUES (?, ?, ?, ?, ?, 1)",
            (student_db_id, instrument_db_id or None, scan_file_path, notes, now),
        )


def get_all_contracts():
    with get_connection() as conn:
        return conn.execute("""
            SELECT c.*, s.name AS student_name,
                   i.name AS instrument_name, i.serial_number AS instrument_serial
            FROM contracts c
            JOIN students s ON c.student_id = s.id
            LEFT JOIN instruments i ON c.instrument_id = i.id
            ORDER BY c.date DESC
        """).fetchall()


def get_contracts_for_instrument(instrument_db_id):
    with get_connection() as conn:
        return conn.execute("""
            SELECT c.*, s.name AS student_name
            FROM contracts c
            JOIN students s ON c.student_id = s.id
            WHERE c.instrument_id = ?
            ORDER BY c.date DESC
        """, (instrument_db_id,)).fetchall()


def toggle_contract_active(contract_id):
    with get_connection() as conn:
        conn.execute(
            "UPDATE contracts SET active = CASE WHEN active=1 THEN 0 ELSE 1 END WHERE id=?",
            (contract_id,),
        )


def delete_contract(contract_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM contracts WHERE id=?", (contract_id,))
