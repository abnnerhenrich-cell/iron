import os
import sqlite3
import secrets
from datetime import datetime, date
from functools import wraps
from pathlib import Path

from flask import (
    Flask, render_template, request, redirect, url_for, session,
    flash, send_from_directory, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
UPLOAD_DIR = INSTANCE_DIR / "uploads"
DB_PATH = INSTANCE_DIR / "rpt.db"

INSTANCE_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__, instance_path=str(INSTANCE_DIR))
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.executescript("""
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user','admin')),
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS cycles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cycle_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'GERAL',
        target REAL NOT NULL,
        unit TEXT NOT NULL DEFAULT 'un',
        icon TEXT DEFAULT '📦',
        sort_order INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (cycle_id) REFERENCES cycles(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        goal_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        note TEXT,
        image_filename TEXT,
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK(status IN ('pending','approved','rejected')),
        admin_note TEXT,
        created_at TEXT NOT NULL,
        reviewed_at TEXT,
        reviewed_by INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE,
        FOREIGN KEY (reviewed_by) REFERENCES users(id)
    );
    """)
    conn.commit()

    admin_exists = conn.execute("SELECT 1 FROM users WHERE role='admin' LIMIT 1").fetchone()
    if not admin_exists:
        email = os.environ.get("ADMIN_EMAIL", "admin@rpt.local")
        password = os.environ.get("ADMIN_PASSWORD", "admin123")
        conn.execute(
            "INSERT INTO users (name,email,password_hash,role,created_at) VALUES (?,?,?,?,?)",
            ("Administrador", email, generate_password_hash(password), "admin", datetime.utcnow().isoformat())
        )
        conn.commit()
    conn.close()

init_db()

@app.context_processor
def inject_globals():
    return {
        "current_user": get_current_user(),
        "csrf_token": csrf_token,
        "money": money,
        "today": date.today(),
    }

def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(24)
    return session["_csrf"]

def validate_csrf():
    if request.form.get("_csrf") != session.get("_csrf"):
        abort(400, "Token CSRF inválido.")

def get_current_user():
    uid = session.get("uid")
    if not uid:
        return None
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return user

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not get_current_user():
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect(url_for("login"))
        if user["role"] != "admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def money(value):
    try:
        v = float(value)
    except Exception:
        v = 0
    formatted = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"

def active_cycle_with_goals(user_id=None):
    conn = db()
    cycle = conn.execute(
        "SELECT * FROM cycles WHERE active=1 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    goals = []
    if cycle:
        rows = conn.execute("""
            SELECT g.*,
                   COALESCE(SUM(CASE WHEN s.status='approved' AND s.user_id=? THEN s.amount ELSE 0 END),0) approved,
                   COALESCE(SUM(CASE WHEN s.status='pending' AND s.user_id=? THEN s.amount ELSE 0 END),0) pending
            FROM goals g
            LEFT JOIN submissions s ON s.goal_id=g.id
            WHERE g.cycle_id=?
            GROUP BY g.id
            ORDER BY g.sort_order, g.id
        """, (user_id or -1, user_id or -1, cycle["id"])).fetchall()
        goals = rows
    conn.close()
    return cycle, goals

@app.route("/")
def index():
    if get_current_user():
        return redirect(url_for("admin_dashboard" if get_current_user()["role"] == "admin" else "dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        validate_csrf()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        conn = db()
        user = conn.execute("SELECT * FROM users WHERE email=? AND active=1", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["uid"] = user["id"]
            session["_csrf"] = secrets.token_urlsafe(24)
            return redirect(url_for("admin_dashboard" if user["role"] == "admin" else "dashboard"))
        flash("E-mail ou senha inválidos.", "danger")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        validate_csrf()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if len(name) < 2 or "@" not in email or len(password) < 6:
            flash("Preencha os dados corretamente. A senha deve ter ao menos 6 caracteres.", "danger")
            return render_template("register.html")
        try:
            conn = db()
            conn.execute(
                "INSERT INTO users (name,email,password_hash,role,created_at) VALUES (?,?,?,?,?)",
                (name, email, generate_password_hash(password), "user", datetime.utcnow().isoformat())
            )
            conn.commit()
            conn.close()
            flash("Conta criada. Agora faça login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Este e-mail já está cadastrado.", "danger")
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    cycle, goals = active_cycle_with_goals(user["id"])
    total_target = sum(float(g["target"]) for g in goals)
    total_approved = sum(float(g["approved"]) for g in goals)
    overall = round((total_approved / total_target) * 100) if total_target else 0

    conn = db()
    history = conn.execute("""
        SELECT s.*, g.title goal_title, g.unit, c.title cycle_title
        FROM submissions s
        JOIN goals g ON g.id=s.goal_id
        JOIN cycles c ON c.id=g.cycle_id
        WHERE s.user_id=?
        ORDER BY s.id DESC LIMIT 8
    """, (user["id"],)).fetchall()
    counts = conn.execute("""
        SELECT
          SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) pending,
          SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) approved,
          SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) rejected
        FROM submissions WHERE user_id=?
    """, (user["id"],)).fetchone()
    conn.close()
    return render_template("dashboard.html", cycle=cycle, goals=goals, overall=overall, history=history, counts=counts)

@app.route("/submit", methods=["GET", "POST"])
@login_required
def submit():
    user = get_current_user()
    cycle, goals = active_cycle_with_goals(user["id"])
    if not cycle:
        flash("Não há ciclo ativo.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        validate_csrf()
        goal_id = request.form.get("goal_id", type=int)
        amount = request.form.get("amount", type=float)
        note = request.form.get("note", "").strip()
        image = request.files.get("image")
        valid_goal = next((g for g in goals if g["id"] == goal_id), None)

        if not valid_goal or amount is None or amount <= 0:
            flash("Selecione uma meta e informe um valor válido.", "danger")
            return render_template("submit.html", cycle=cycle, goals=goals)

        filename = None
        if image and image.filename:
            if not allowed_file(image.filename):
                flash("Formato de imagem não permitido.", "danger")
                return render_template("submit.html", cycle=cycle, goals=goals)
            ext = image.filename.rsplit(".", 1)[1].lower()
            safe = secure_filename(image.filename.rsplit(".", 1)[0])[:50] or "comprovante"
            filename = f"{user['id']}_{int(datetime.utcnow().timestamp())}_{secrets.token_hex(4)}_{safe}.{ext}"
            image.save(UPLOAD_DIR / filename)

        conn = db()
        conn.execute("""
            INSERT INTO submissions (user_id, goal_id, amount, note, image_filename, status, created_at)
            VALUES (?,?,?,?,?,'pending',?)
        """, (user["id"], goal_id, amount, note, filename, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        flash("Entrega enviada para análise.", "success")
        return redirect(url_for("dashboard"))

    return render_template("submit.html", cycle=cycle, goals=goals)

@app.route("/history")
@login_required
def history():
    user = get_current_user()
    conn = db()
    rows = conn.execute("""
        SELECT s.*, g.title goal_title, g.unit, c.title cycle_title, c.start_date, c.end_date
        FROM submissions s
        JOIN goals g ON g.id=s.goal_id
        JOIN cycles c ON c.id=g.cycle_id
        WHERE s.user_id=?
        ORDER BY s.id DESC
    """, (user["id"],)).fetchall()
    conn.close()
    return render_template("history.html", rows=rows)

@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    # Usuário logado pode consultar anexos; em produção, pode-se restringir ainda mais por proprietário/admin.
    return send_from_directory(UPLOAD_DIR, filename)

# ---------------- ADMIN ----------------

@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = db()
    stats = {
        "users": conn.execute("SELECT COUNT(*) c FROM users WHERE role='user'").fetchone()["c"],
        "pending": conn.execute("SELECT COUNT(*) c FROM submissions WHERE status='pending'").fetchone()["c"],
        "approved": conn.execute("SELECT COUNT(*) c FROM submissions WHERE status='approved'").fetchone()["c"],
        "cycles": conn.execute("SELECT COUNT(*) c FROM cycles").fetchone()["c"],
    }
    recent = conn.execute("""
        SELECT s.*, u.name user_name, g.title goal_title, g.unit
        FROM submissions s
        JOIN users u ON u.id=s.user_id
        JOIN goals g ON g.id=s.goal_id
        ORDER BY s.id DESC LIMIT 10
    """).fetchall()
    cycle = conn.execute("SELECT * FROM cycles WHERE active=1 ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return render_template("admin_dashboard.html", stats=stats, recent=recent, cycle=cycle)

@app.route("/admin/cycles", methods=["GET", "POST"])
@admin_required
def admin_cycles():
    if request.method == "POST":
        validate_csrf()
        title = request.form.get("title", "").strip()
        start_date = request.form.get("start_date", "")
        end_date = request.form.get("end_date", "")
        active = 1 if request.form.get("active") == "1" else 0
        if not title or not start_date or not end_date:
            flash("Preencha todos os campos do ciclo.", "danger")
        else:
            conn = db()
            if active:
                conn.execute("UPDATE cycles SET active=0")
            cur = conn.execute(
                "INSERT INTO cycles(title,start_date,end_date,active,created_at) VALUES(?,?,?,?,?)",
                (title, start_date, end_date, active, datetime.utcnow().isoformat())
            )
            conn.commit()
            cycle_id = cur.lastrowid
            conn.close()
            flash("Ciclo criado.", "success")
            return redirect(url_for("admin_cycle_detail", cycle_id=cycle_id))

    conn = db()
    cycles = conn.execute("""
        SELECT c.*, COUNT(g.id) goals_count
        FROM cycles c LEFT JOIN goals g ON g.cycle_id=c.id
        GROUP BY c.id ORDER BY c.id DESC
    """).fetchall()
    conn.close()
    return render_template("admin_cycles.html", cycles=cycles)

@app.post("/admin/cycles/<int:cycle_id>/activate")
@admin_required
def admin_cycle_activate(cycle_id):
    validate_csrf()
    conn = db()
    conn.execute("UPDATE cycles SET active=0")
    conn.execute("UPDATE cycles SET active=1 WHERE id=?", (cycle_id,))
    conn.commit()
    conn.close()
    flash("Ciclo ativado.", "success")
    return redirect(url_for("admin_cycles"))

@app.route("/admin/cycles/<int:cycle_id>", methods=["GET", "POST"])
@admin_required
def admin_cycle_detail(cycle_id):
    conn = db()
    cycle = conn.execute("SELECT * FROM cycles WHERE id=?", (cycle_id,)).fetchone()
    if not cycle:
        conn.close()
        abort(404)

    if request.method == "POST":
        validate_csrf()
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "GERAL").strip() or "GERAL"
        target = request.form.get("target", type=float)
        unit = request.form.get("unit", "un")
        icon = request.form.get("icon", "📦").strip() or "📦"
        if title and target and target > 0:
            max_order = conn.execute("SELECT COALESCE(MAX(sort_order),0)+1 n FROM goals WHERE cycle_id=?", (cycle_id,)).fetchone()["n"]
            conn.execute("""
                INSERT INTO goals(cycle_id,title,category,target,unit,icon,sort_order)
                VALUES(?,?,?,?,?,?,?)
            """, (cycle_id, title, category, target, unit, icon, max_order))
            conn.commit()
            flash("Meta adicionada.", "success")
        else:
            flash("Informe título e alvo válido.", "danger")

    goals = conn.execute("SELECT * FROM goals WHERE cycle_id=? ORDER BY sort_order,id", (cycle_id,)).fetchall()
    conn.close()
    return render_template("admin_cycle_detail.html", cycle=cycle, goals=goals)

@app.post("/admin/goals/<int:goal_id>/delete")
@admin_required
def admin_goal_delete(goal_id):
    validate_csrf()
    conn = db()
    goal = conn.execute("SELECT * FROM goals WHERE id=?", (goal_id,)).fetchone()
    if not goal:
        conn.close()
        abort(404)
    if conn.execute("SELECT 1 FROM submissions WHERE goal_id=? LIMIT 1", (goal_id,)).fetchone():
        conn.close()
        flash("Essa meta já possui entregas e não pode ser excluída.", "danger")
        return redirect(url_for("admin_cycle_detail", cycle_id=goal["cycle_id"]))
    conn.execute("DELETE FROM goals WHERE id=?", (goal_id,))
    conn.commit()
    cycle_id = goal["cycle_id"]
    conn.close()
    flash("Meta excluída.", "success")
    return redirect(url_for("admin_cycle_detail", cycle_id=cycle_id))

@app.route("/admin/submissions")
@admin_required
def admin_submissions():
    status = request.args.get("status", "pending")
    if status not in {"pending", "approved", "rejected", "all"}:
        status = "pending"
    conn = db()
    sql = """
        SELECT s.*, u.name user_name, u.email, g.title goal_title, g.unit, c.title cycle_title
        FROM submissions s
        JOIN users u ON u.id=s.user_id
        JOIN goals g ON g.id=s.goal_id
        JOIN cycles c ON c.id=g.cycle_id
    """
    params = ()
    if status != "all":
        sql += " WHERE s.status=?"
        params = (status,)
    sql += " ORDER BY s.id DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template("admin_submissions.html", rows=rows, status=status)

@app.post("/admin/submissions/<int:submission_id>/review")
@admin_required
def admin_review(submission_id):
    validate_csrf()
    decision = request.form.get("decision")
    admin_note = request.form.get("admin_note", "").strip()
    if decision not in {"approved", "rejected"}:
        abort(400)
    admin = get_current_user()
    conn = db()
    conn.execute("""
        UPDATE submissions
        SET status=?, admin_note=?, reviewed_at=?, reviewed_by=?
        WHERE id=?
    """, (decision, admin_note, datetime.utcnow().isoformat(), admin["id"], submission_id))
    conn.commit()
    conn.close()
    flash("Entrega atualizada.", "success")
    return redirect(request.referrer or url_for("admin_submissions"))

@app.route("/admin/users")
@admin_required
def admin_users():
    conn = db()
    users = conn.execute("""
        SELECT u.*,
               COUNT(s.id) submissions_count,
               SUM(CASE WHEN s.status='approved' THEN 1 ELSE 0 END) approved_count
        FROM users u
        LEFT JOIN submissions s ON s.user_id=u.id
        GROUP BY u.id
        ORDER BY u.id DESC
    """).fetchall()
    conn.close()
    return render_template("admin_users.html", users=users)

@app.post("/admin/users/<int:user_id>/toggle")
@admin_required
def admin_user_toggle(user_id):
    validate_csrf()
    if user_id == get_current_user()["id"]:
        flash("Você não pode desativar sua própria conta.", "danger")
        return redirect(url_for("admin_users"))
    conn = db()
    conn.execute("UPDATE users SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    flash("Status do usuário alterado.", "success")
    return redirect(url_for("admin_users"))

@app.errorhandler(413)
def too_large(_):
    flash("Arquivo muito grande. O limite é 8 MB.", "danger")
    return redirect(request.referrer or url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
