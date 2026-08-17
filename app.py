import os
import secrets
import re
from datetime import date
from functools import wraps
from io import BytesIO

from flask import (
    Flask, render_template, request, redirect, url_for, session,
    flash, send_file, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

import psycopg
from psycopg.rows import dict_row

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave-no-vercel")
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

DATABASE_URL = os.environ.get("DATABASE_URL")
ALLOWED_MIMES = {"image/png", "image/jpeg", "image/webp", "image/gif"}

def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL não encontrada. Conecte o Neon ao projeto na Vercel.")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user','admin')),
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    approved BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS approved BOOLEAN NOT NULL DEFAULT FALSE
            """)
            cur.execute("UPDATE users SET approved=TRUE WHERE role='admin'")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS cycles (
                    id BIGSERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    active BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id BIGSERIAL PRIMARY KEY,
                    cycle_id BIGINT NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'GERAL',
                    target NUMERIC(14,2) NOT NULL,
                    unit TEXT NOT NULL DEFAULT 'un',
                    icon TEXT DEFAULT '📦',
                    sort_order INTEGER NOT NULL DEFAULT 0
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS submissions (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    goal_id BIGINT NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
                    amount NUMERIC(14,2) NOT NULL,
                    note TEXT,
                    image_data BYTEA,
                    image_mime TEXT,
                    image_name TEXT,
                    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
                    admin_note TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    reviewed_at TIMESTAMPTZ,
                    reviewed_by BIGINT REFERENCES users(id)
                )
            """)
            cur.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS image2_data BYTEA")
            cur.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS image2_mime TEXT")
            cur.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS image2_name TEXT")
            cur.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS image3_data BYTEA")
            cur.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS image3_mime TEXT")
            cur.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS image3_name TEXT")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS delivery_batches (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    cycle_id BIGINT NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
                    note TEXT,
                    image_data BYTEA,
                    image_mime TEXT,
                    image_name TEXT,
                    image2_data BYTEA,
                    image2_mime TEXT,
                    image2_name TEXT,
                    image3_data BYTEA,
                    image3_mime TEXT,
                    image3_name TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS batch_id BIGINT REFERENCES delivery_batches(id) ON DELETE SET NULL")
            admin_email = os.environ.get("ADMIN_EMAIL")
            admin_password = os.environ.get("ADMIN_PASSWORD")

            # Se ADMIN_EMAIL e ADMIN_PASSWORD estiverem configurados na Vercel,
            # garante que essas credenciais sejam sempre o administrador válido.
            if admin_email and admin_password:
                cur.execute("""
                    INSERT INTO users (name,email,password_hash,role,active,approved)
                    VALUES (%s,%s,%s,'admin',TRUE,TRUE)
                    ON CONFLICT (email) DO UPDATE SET
                        password_hash=EXCLUDED.password_hash,
                        role='admin',
                        active=TRUE,
                        approved=TRUE
                """, (
                    "Administrador",
                    admin_email.strip().lower(),
                    generate_password_hash(admin_password)
                ))
            else:
                # Fallback apenas para ambiente de teste/local.
                cur.execute("SELECT 1 FROM users WHERE role='admin' LIMIT 1")
                if cur.fetchone() is None:
                    cur.execute("""
                        INSERT INTO users (name,email,password_hash,role,active,approved)
                        VALUES (%s,%s,%s,'admin',TRUE,TRUE)
                        ON CONFLICT (email) DO NOTHING
                    """, (
                        "Administrador",
                        "admin@iron.local",
                        generate_password_hash("admin123")
                    ))
        conn.commit()

init_db()

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
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id=%s", (uid,))
            return cur.fetchone()

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
            return redirect(url_for("admin_login"))
        if user["role"] != "admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

def money(value):
    try:
        v = float(value or 0)
    except Exception:
        v = 0
    formatted = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"

@app.context_processor
def inject_globals():
    return {
        "current_user": get_current_user(),
        "csrf_token": csrf_token,
        "money": money,
        "today": date.today(),
    }

def active_cycle_with_goals(user_id=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM cycles WHERE active=TRUE ORDER BY id DESC LIMIT 1")
            cycle = cur.fetchone()
            goals = []
            if cycle:
                cur.execute("""
                    SELECT g.*,
                           COALESCE(SUM(CASE WHEN s.status='approved' AND s.user_id=%s THEN s.amount ELSE 0 END),0) AS approved,
                           COALESCE(SUM(CASE WHEN s.status='pending' AND s.user_id=%s THEN s.amount ELSE 0 END),0) AS pending
                    FROM goals g
                    LEFT JOIN submissions s ON s.goal_id=g.id
                    WHERE g.cycle_id=%s
                    GROUP BY g.id
                    ORDER BY g.sort_order, g.id
                """, (user_id or -1, user_id or -1, cycle["id"]))
                goals = cur.fetchall()
    return cycle, goals

@app.route("/")
def index():
    user = get_current_user()
    if user:
        return redirect(url_for("admin_dashboard" if user["role"] == "admin" else "dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        validate_csrf()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE LOWER(email)=%s", (email,))
                user = cur.fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("E-mail ou senha inválidos.", "danger")
            return render_template("login.html")

        if user["role"] == "admin":
            flash("Administradores devem entrar pelo Painel Admin.", "danger")
            return redirect(url_for("admin_login"))

        if not user["active"]:
            flash("Seu acesso está bloqueado. Procure um administrador.", "danger")
            return render_template("login.html")

        if not user["approved"]:
            flash("Cadastro aguardando aprovação de um administrador.", "danger")
            return render_template("login.html")

        session.clear()
        session["uid"] = user["id"]
        session["_csrf"] = secrets.token_urlsafe(24)
        return redirect(url_for("dashboard"))

    return render_template("login.html")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        validate_csrf()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE LOWER(email)=%s", (email,))
                user = cur.fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("E-mail ou senha inválidos.", "danger")
            return render_template("admin_login.html")

        if user["role"] != "admin":
            flash("Esta conta não possui permissão administrativa.", "danger")
            return render_template("admin_login.html")

        if not user["active"]:
            flash("Esta conta administrativa está bloqueada.", "danger")
            return render_template("admin_login.html")

        session.clear()
        session["uid"] = user["id"]
        session["_csrf"] = secrets.token_urlsafe(24)
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    form_data = {"name": "", "email": ""}

    if request.method == "POST":
        validate_csrf()

        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        form_data = {"name": name, "email": email}

        # Mensagens separadas para ficar claro qual campo está errado.
        if len(name) < 2:
            flash("Informe seu nome com pelo menos 2 caracteres.", "danger")
            return render_template("register.html", form_data=form_data)

        if not re.match(r"^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", email):
            flash("Informe um e-mail válido, por exemplo nome@email.com.", "danger")
            return render_template("register.html", form_data=form_data)

        if len(password) < 6:
            flash("A senha precisa ter pelo menos 6 caracteres.", "danger")
            return render_template("register.html", form_data=form_data)

        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO users (name,email,password_hash,role,approved,active)
                        VALUES (%s,%s,%s,'user',FALSE,TRUE)
                        """,
                        (name, email, generate_password_hash(password))
                    )
                conn.commit()

            flash("Cadastro enviado. Aguarde a aprovação de um administrador antes de entrar.", "success")
            return redirect(url_for("login"))

        except psycopg.errors.UniqueViolation:
            flash("Este e-mail já está cadastrado. Use outro e-mail ou entre na sua conta.", "danger")
            return render_template("register.html", form_data=form_data)

    return render_template("register.html", form_data=form_data)

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

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.*, g.title AS goal_title, g.unit, c.title AS cycle_title
                FROM submissions s
                JOIN goals g ON g.id=s.goal_id
                JOIN cycles c ON c.id=g.cycle_id
                WHERE s.user_id=%s
                ORDER BY s.id DESC LIMIT 8
            """, (user["id"],))
            history = cur.fetchall()
            cur.execute("""
                SELECT
                  COUNT(*) FILTER (WHERE status='pending') AS pending,
                  COUNT(*) FILTER (WHERE status='approved') AS approved,
                  COUNT(*) FILTER (WHERE status='rejected') AS rejected
                FROM submissions WHERE user_id=%s
            """, (user["id"],))
            counts = cur.fetchone()

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
        note = (request.form.get("note") or "").strip()

        selected = []
        valid_ids = {int(g["id"]): g for g in goals}

        for key, raw_value in request.form.items():
            if not key.startswith("amount_"):
                continue
            try:
                goal_id = int(key.split("_", 1)[1])
                amount = float(raw_value or 0)
            except (ValueError, TypeError):
                continue

            if goal_id in valid_ids and amount > 0:
                selected.append((goal_id, amount))

        if not selected:
            flash("Informe pelo menos uma quantidade antes de enviar.", "danger")
            return render_template("submit.html", cycle=cycle, goals=goals)

        uploaded = [img for img in request.files.getlist("images") if img and img.filename]

        if not uploaded:
            flash("Adicione pelo menos uma foto/comprovante da entrega.", "danger")
            return render_template("submit.html", cycle=cycle, goals=goals)

        if len(uploaded) > 3:
            flash("Envie no máximo 3 imagens por atualização.", "danger")
            return render_template("submit.html", cycle=cycle, goals=goals)

        images = []
        total_bytes = 0

        for image in uploaded:
            if image.mimetype not in ALLOWED_MIMES:
                flash("Uma das imagens está em formato não permitido.", "danger")
                return render_template("submit.html", cycle=cycle, goals=goals)

            data = image.read()
            total_bytes += len(data)

            if len(data) > 1_250_000:
                flash("Uma das imagens ficou grande demais. Tente novamente.", "danger")
                return render_template("submit.html", cycle=cycle, goals=goals)

            images.append((data, image.mimetype, image.filename[:180]))

        if total_bytes > 3_600_000:
            flash("As fotos juntas ficaram grandes demais. Tente novamente com menos fotos.", "danger")
            return render_template("submit.html", cycle=cycle, goals=goals)

        while len(images) < 3:
            images.append((None, None, None))

        (img1, mime1, name1), (img2, mime2, name2), (img3, mime3, name3) = images

        # As imagens são gravadas UMA única vez no lote da entrega.
        # Cada item da meta apenas referencia esse lote.
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO delivery_batches (
                        user_id, cycle_id, note,
                        image_data, image_mime, image_name,
                        image2_data, image2_mime, image2_name,
                        image3_data, image3_mime, image3_name
                    )
                    VALUES (
                        %s,%s,%s,
                        %s,%s,%s,
                        %s,%s,%s,
                        %s,%s,%s
                    )
                    RETURNING id
                """, (
                    user["id"], cycle["id"], note,
                    img1, mime1, name1,
                    img2, mime2, name2,
                    img3, mime3, name3
                ))
                batch_id = cur.fetchone()["id"]

                for goal_id, amount in selected:
                    cur.execute("""
                        INSERT INTO submissions (
                            user_id, goal_id, amount, note, batch_id, status
                        )
                        VALUES (%s,%s,%s,%s,%s,'pending')
                    """, (
                        user["id"], goal_id, amount, note, batch_id
                    ))
            conn.commit()

        flash(f"{len(selected)} item(ns) enviado(s) para análise.", "success")
        return redirect(url_for("dashboard"))

    return render_template("submit.html", cycle=cycle, goals=goals)


@app.route("/history")
@login_required
def history():
    user = get_current_user()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.id, s.user_id, s.goal_id, s.amount, s.note, s.status,
                       s.admin_note, s.created_at, s.reviewed_at,
                       (s.image_data IS NOT NULL) AS has_image,
                       g.title AS goal_title, g.unit,
                       c.title AS cycle_title, c.start_date, c.end_date
                FROM submissions s
                JOIN goals g ON g.id=s.goal_id
                JOIN cycles c ON c.id=g.cycle_id
                WHERE s.user_id=%s
                ORDER BY s.id DESC
            """, (user["id"],))
            rows = cur.fetchall()
    return render_template("history.html", rows=rows)

@app.route("/submission-image/<int:submission_id>")
@login_required
def submission_image(submission_id):
    user = get_current_user()
    index = request.args.get("index", "1")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    s.user_id,
                    s.image_data, s.image_mime, s.image_name,
                    s.image2_data, s.image2_mime, s.image2_name,
                    s.image3_data, s.image3_mime, s.image3_name,
                    b.image_data AS batch_image_data,
                    b.image_mime AS batch_image_mime,
                    b.image_name AS batch_image_name,
                    b.image2_data AS batch_image2_data,
                    b.image2_mime AS batch_image2_mime,
                    b.image2_name AS batch_image2_name,
                    b.image3_data AS batch_image3_data,
                    b.image3_mime AS batch_image3_mime,
                    b.image3_name AS batch_image3_name
                FROM submissions s
                LEFT JOIN delivery_batches b ON b.id=s.batch_id
                WHERE s.id=%s
            """, (submission_id,))
            item = cur.fetchone()

    if not item:
        abort(404)

    if user["role"] != "admin" and int(item["user_id"]) != int(user["id"]):
        abort(403)

    if index == "2":
        data = item["batch_image2_data"] or item["image2_data"]
        mime = item["batch_image2_mime"] or item["image2_mime"]
        name = item["batch_image2_name"] or item["image2_name"]
    elif index == "3":
        data = item["batch_image3_data"] or item["image3_data"]
        mime = item["batch_image3_mime"] or item["image3_mime"]
        name = item["batch_image3_name"] or item["image3_name"]
    else:
        data = item["batch_image_data"] or item["image_data"]
        mime = item["batch_image_mime"] or item["image_mime"]
        name = item["batch_image_name"] or item["image_name"]

    if not data:
        abort(404)

    return send_file(
        BytesIO(bytes(data)),
        mimetype=mime or "application/octet-stream",
        download_name=name or f"comprovante-{submission_id}-{index}",
        as_attachment=False
    )


@app.route("/admin")
@admin_required
def admin_dashboard():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM users WHERE role='user'")
            users = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM submissions WHERE status='pending'")
            pending = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM submissions WHERE status='approved'")
            approved = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM cycles")
            cycles = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM users WHERE role='user' AND approved=FALSE")
            pending_users = cur.fetchone()["c"]
            cur.execute("""
                SELECT s.id, s.amount, s.status, s.created_at,
                       (s.image_data IS NOT NULL) AS has_image,
                       u.name AS user_name, g.title AS goal_title, g.unit
                FROM submissions s
                JOIN users u ON u.id=s.user_id
                JOIN goals g ON g.id=s.goal_id
                ORDER BY s.id DESC LIMIT 10
            """)
            recent = cur.fetchall()
            cur.execute("SELECT * FROM cycles WHERE active=TRUE ORDER BY id DESC LIMIT 1")
            cycle = cur.fetchone()
    stats = {"users": users, "pending": pending, "approved": approved, "cycles": cycles, "pending_users": pending_users}
    return render_template("admin_dashboard.html", stats=stats, recent=recent, cycle=cycle)

@app.route("/admin/cycles", methods=["GET", "POST"])
@admin_required
def admin_cycles():
    if request.method == "POST":
        validate_csrf()
        title = request.form.get("title", "").strip()
        start_date = request.form.get("start_date", "")
        end_date = request.form.get("end_date", "")
        active = request.form.get("active") == "1"
        if not title or not start_date or not end_date:
            flash("Preencha todos os campos do ciclo.", "danger")
        else:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    if active:
                        cur.execute("UPDATE cycles SET active=FALSE")
                    cur.execute("""
                        INSERT INTO cycles(title,start_date,end_date,active)
                        VALUES(%s,%s,%s,%s) RETURNING id
                    """, (title, start_date, end_date, active))
                    cycle_id = cur.fetchone()["id"]
                conn.commit()
            flash("Ciclo criado.", "success")
            return redirect(url_for("admin_cycle_detail", cycle_id=cycle_id))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.*, COUNT(g.id) AS goals_count
                FROM cycles c LEFT JOIN goals g ON g.cycle_id=c.id
                GROUP BY c.id ORDER BY c.id DESC
            """)
            cycles = cur.fetchall()
    return render_template("admin_cycles.html", cycles=cycles)

@app.post("/admin/cycles/<int:cycle_id>/activate")
@admin_required
def admin_cycle_activate(cycle_id):
    validate_csrf()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE cycles SET active=FALSE")
            cur.execute("UPDATE cycles SET active=TRUE WHERE id=%s", (cycle_id,))
        conn.commit()
    flash("Ciclo ativado.", "success")
    return redirect(url_for("admin_cycles"))

@app.route("/admin/cycles/<int:cycle_id>", methods=["GET", "POST"])
@admin_required
def admin_cycle_detail(cycle_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM cycles WHERE id=%s", (cycle_id,))
            cycle = cur.fetchone()
            if not cycle:
                abort(404)

            if request.method == "POST":
                validate_csrf()
                title = request.form.get("title", "").strip()
                category = request.form.get("category", "GERAL").strip() or "GERAL"
                target = request.form.get("target", type=float)
                unit = request.form.get("unit", "un")
                icon = request.form.get("icon", "📦").strip() or "📦"
                if title and target and target > 0:
                    cur.execute("SELECT COALESCE(MAX(sort_order),0)+1 AS n FROM goals WHERE cycle_id=%s", (cycle_id,))
                    max_order = cur.fetchone()["n"]
                    cur.execute("""
                        INSERT INTO goals(cycle_id,title,category,target,unit,icon,sort_order)
                        VALUES(%s,%s,%s,%s,%s,%s,%s)
                    """, (cycle_id, title, category, target, unit, icon, max_order))
                    conn.commit()
                    flash("Meta adicionada.", "success")
                else:
                    flash("Informe título e alvo válido.", "danger")

            cur.execute("SELECT * FROM goals WHERE cycle_id=%s ORDER BY sort_order,id", (cycle_id,))
            goals = cur.fetchall()
    return render_template("admin_cycle_detail.html", cycle=cycle, goals=goals)

@app.post("/admin/goals/<int:goal_id>/delete")
@admin_required
def admin_goal_delete(goal_id):
    validate_csrf()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM goals WHERE id=%s", (goal_id,))
            goal = cur.fetchone()
            if not goal:
                abort(404)
            cur.execute("SELECT 1 FROM submissions WHERE goal_id=%s LIMIT 1", (goal_id,))
            if cur.fetchone():
                flash("Essa meta já possui entregas e não pode ser excluída.", "danger")
                return redirect(url_for("admin_cycle_detail", cycle_id=goal["cycle_id"]))
            cur.execute("DELETE FROM goals WHERE id=%s", (goal_id,))
            conn.commit()
            cycle_id = goal["cycle_id"]
    flash("Meta excluída.", "success")
    return redirect(url_for("admin_cycle_detail", cycle_id=cycle_id))

@app.route("/admin/submissions")
@admin_required
def admin_submissions():
    status = request.args.get("status", "pending")
    if status not in {"pending", "approved", "rejected", "all"}:
        status = "pending"
    sql = """
        SELECT s.id, s.user_id, s.amount, s.note, s.status, s.admin_note,
               s.created_at, s.reviewed_at,
               ((b.image_data IS NOT NULL) OR (s.image_data IS NOT NULL)) AS has_image,
               ((b.image2_data IS NOT NULL) OR (s.image2_data IS NOT NULL)) AS has_image2,
               ((b.image3_data IS NOT NULL) OR (s.image3_data IS NOT NULL)) AS has_image3,
               u.name AS user_name, u.email,
               g.title AS goal_title, g.unit,
               c.title AS cycle_title
        FROM submissions s
        JOIN users u ON u.id=s.user_id
        JOIN goals g ON g.id=s.goal_id
        JOIN cycles c ON c.id=g.cycle_id
        LEFT JOIN delivery_batches b ON b.id=s.batch_id
    """
    params = []
    if status != "all":
        sql += " WHERE s.status=%s"
        params.append(status)
    sql += " ORDER BY s.id DESC"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
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
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE submissions
                SET status=%s, admin_note=%s, reviewed_at=NOW(), reviewed_by=%s
                WHERE id=%s
            """, (decision, admin_note, admin["id"], submission_id))
        conn.commit()
    flash("Entrega atualizada.", "success")
    return redirect(request.referrer or url_for("admin_submissions"))

@app.route("/admin/registrations")
@admin_required
def admin_registrations():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, email, role, active, approved, created_at
                FROM users
                WHERE role='user' AND approved=FALSE
                ORDER BY created_at ASC
            """)
            users = cur.fetchall()
    return render_template("admin_registrations.html", users=users)

@app.route("/admin/users")
@admin_required
def admin_users():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.*,
                       COUNT(s.id) AS submissions_count,
                       COUNT(s.id) FILTER (WHERE s.status='approved') AS approved_count
                FROM users u
                LEFT JOIN submissions s ON s.user_id=u.id
                GROUP BY u.id
                ORDER BY u.id DESC
            """)
            users = cur.fetchall()
    return render_template("admin_users.html", users=users)

@app.post("/admin/users/<int:user_id>/toggle")
@admin_required
def admin_user_toggle(user_id):
    validate_csrf()
    if int(user_id) == int(get_current_user()["id"]):
        flash("Você não pode desativar sua própria conta.", "danger")
        return redirect(url_for("admin_users"))
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET active=NOT active WHERE id=%s", (user_id,))
        conn.commit()
    flash("Status do usuário alterado.", "success")
    return redirect(url_for("admin_users"))

@app.post("/admin/users/<int:user_id>/approve")
@admin_required
def admin_user_approve(user_id):
    validate_csrf()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET approved=TRUE, active=TRUE
                WHERE id=%s AND role='user'
            """, (user_id,))
        conn.commit()
    flash("Membro aprovado e liberado para acessar o painel.", "success")
    return redirect(request.referrer or url_for("admin_registrations"))

@app.post("/admin/users/<int:user_id>/reject")
@admin_required
def admin_user_reject(user_id):
    validate_csrf()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET approved=FALSE, active=FALSE
                WHERE id=%s AND role='user'
            """, (user_id,))
        conn.commit()
    flash("Cadastro recusado/bloqueado.", "success")
    return redirect(request.referrer or url_for("admin_registrations"))

@app.post("/admin/users/<int:user_id>/make-admin")
@admin_required
def admin_user_make_admin(user_id):
    validate_csrf()
    if int(user_id) == int(get_current_user()["id"]):
        return redirect(url_for("admin_users"))
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET role='admin', approved=TRUE, active=TRUE
                WHERE id=%s
            """, (user_id,))
        conn.commit()
    flash("Permissão de administrador concedida.", "success")
    return redirect(url_for("admin_users"))

@app.post("/admin/users/<int:user_id>/remove-admin")
@admin_required
def admin_user_remove_admin(user_id):
    validate_csrf()
    if int(user_id) == int(get_current_user()["id"]):
        flash("Você não pode remover sua própria permissão administrativa.", "danger")
        return redirect(url_for("admin_users"))
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET role='user', approved=TRUE, active=TRUE
                WHERE id=%s
            """, (user_id,))
        conn.commit()
    flash("Permissão administrativa removida. A conta voltou a ser membro.", "success")
    return redirect(url_for("admin_users"))

@app.errorhandler(413)
def too_large(_):
    flash("Arquivo muito grande. Use uma imagem menor que 3,5 MB.", "danger")
    return redirect(request.referrer or url_for("dashboard"))
