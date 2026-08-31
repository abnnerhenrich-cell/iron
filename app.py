import os
import secrets
import re
from datetime import date, timedelta
from functools import wraps
from io import BytesIO

from flask import (
    Flask, render_template, request, redirect, url_for, session,
    flash, send_file, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException

import psycopg
from psycopg.rows import dict_row

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave-no-vercel")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("VERCEL")),
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
    SESSION_REFRESH_EACH_REQUEST=True,
)

DATABASE_URL = os.environ.get("DATABASE_URL")
ALLOWED_MIMES = {"image/png", "image/jpeg", "image/webp", "image/gif"}

TRADE_PRODUCTS = {
    "Colete": {
        "CPF": 45000,
        "CNPJ": 30000,
        "Parceria": 25000,
        "Aliança": 20000,
    },
    "Celular Hacker": {
        "CNPJ": 95000,
        "Aliança": 80000,
    },
    "Circuito Eletrônico": {
        "CNPJ": 57000,
        "Aliança": 38000,
    },
}

PERSONAL_GOAL_CATALOG = [
    {"key": "plastico", "title": "Plástico", "icon": "🧴", "image": "materials/plastico.webp", "unit": "un"},
    {"key": "borracha", "title": "Borracha", "icon": "🛞", "image": "materials/borracha.webp", "unit": "un"},
    {"key": "vidro", "title": "Vidro", "icon": "🪟", "image": "materials/vidro.webp", "unit": "un"},
    {"key": "cobre", "title": "Cobre", "icon": "🔶", "image": "materials/cobre.webp", "unit": "un"},
    {"key": "aluminio", "title": "Alumínio", "icon": "🥫", "image": "materials/aluminio.webp", "unit": "un"},
    {"key": "chapa_metal", "title": "Chapa de Metal", "icon": "🔩", "image": "materials/chapa_metal.webp", "unit": "un"},
    {"key": "placa_transito", "title": "Placa de Trânsito", "icon": "🚸", "image": "materials/placa_transito.webp", "unit": "un"},
    {"key": "lona", "title": "Lona", "icon": "🧵", "image": "materials/lona.webp", "unit": "un"},
    {"key": "dinheiro", "title": "Dinheiro Sujo ou Limpo", "icon": "💵", "image": "materials/dinheiro.webp", "unit": "un"},
]

def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL não encontrada. Conecte o Neon ao projeto na Vercel.")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def goal_credit_key(title):
    """Chave estável para transportar crédito entre metas com o mesmo nome."""
    return re.sub(r"\s+", " ", (title or "").strip().lower())

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user','manager','admin')),
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    approved BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS approved BOOLEAN NOT NULL DEFAULT FALSE
            """)
            # Bancos antigos possuem CHECK apenas para user/admin.
            cur.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check")
            cur.execute("""
                ALTER TABLE users
                ADD CONSTRAINT users_role_check
                CHECK(role IN ('user','manager','admin'))
            """)
            cur.execute("UPDATE users SET approved=TRUE WHERE role IN ('admin','manager')")

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
            cur.execute("ALTER TABLE goals ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES users(id) ON DELETE CASCADE")
            cur.execute("ALTER TABLE goals ADD COLUMN IF NOT EXISTS credit_applied NUMERIC(14,2) NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE goals ADD COLUMN IF NOT EXISTS closed BOOLEAN NOT NULL DEFAULT FALSE")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS member_goal_credits (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    goal_key TEXT NOT NULL,
                    goal_title TEXT NOT NULL,
                    unit TEXT NOT NULL DEFAULT 'un',
                    balance NUMERIC(14,2) NOT NULL DEFAULT 0,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(user_id, goal_key, unit)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS goal_closures (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    cycle_id BIGINT NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
                    goal_id BIGINT NOT NULL UNIQUE REFERENCES goals(id) ON DELETE CASCADE,
                    goal_title TEXT NOT NULL,
                    unit TEXT NOT NULL DEFAULT 'un',
                    target NUMERIC(14,2) NOT NULL DEFAULT 0,
                    credit_applied NUMERIC(14,2) NOT NULL DEFAULT 0,
                    required_target NUMERIC(14,2) NOT NULL DEFAULT 0,
                    approved NUMERIC(14,2) NOT NULL DEFAULT 0,
                    surplus NUMERIC(14,2) NOT NULL DEFAULT 0,
                    shortfall NUMERIC(14,2) NOT NULL DEFAULT 0,
                    carried_balance NUMERIC(14,2) NOT NULL DEFAULT 0,
                    applied_to_goal_id BIGINT REFERENCES goals(id) ON DELETE SET NULL,
                    consumed_at TIMESTAMPTZ,
                    closed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    closed_by BIGINT REFERENCES users(id)
                )
            """)
            # Migrações idempotentes: garantem as colunas mesmo se a tabela
            # tiver sido criada parcialmente por uma implantação anterior.
            cur.execute("ALTER TABLE member_goal_credits ADD COLUMN IF NOT EXISTS goal_key TEXT")
            cur.execute("ALTER TABLE member_goal_credits ADD COLUMN IF NOT EXISTS goal_title TEXT")
            cur.execute("ALTER TABLE member_goal_credits ADD COLUMN IF NOT EXISTS unit TEXT NOT NULL DEFAULT 'un'")
            cur.execute("ALTER TABLE member_goal_credits ADD COLUMN IF NOT EXISTS balance NUMERIC(14,2) NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE member_goal_credits ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
            cur.execute("ALTER TABLE goal_closures ADD COLUMN IF NOT EXISTS credit_applied NUMERIC(14,2) NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE goal_closures ADD COLUMN IF NOT EXISTS required_target NUMERIC(14,2) NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE goal_closures ADD COLUMN IF NOT EXISTS approved NUMERIC(14,2) NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE goal_closures ADD COLUMN IF NOT EXISTS surplus NUMERIC(14,2) NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE goal_closures ADD COLUMN IF NOT EXISTS shortfall NUMERIC(14,2) NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE goal_closures ADD COLUMN IF NOT EXISTS carried_balance NUMERIC(14,2) NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE goal_closures ADD COLUMN IF NOT EXISTS applied_to_goal_id BIGINT REFERENCES goals(id) ON DELETE SET NULL")
            cur.execute("ALTER TABLE goal_closures ADD COLUMN IF NOT EXISTS consumed_at TIMESTAMPTZ")
            cur.execute("ALTER TABLE goal_closures ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
            cur.execute("ALTER TABLE goal_closures ADD COLUMN IF NOT EXISTS closed_by BIGINT REFERENCES users(id)")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_image BYTEA")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_image_mime TEXT")
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

            # Compras & Vendas — módulo administrativo nativo.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS trade_records (
                    id BIGSERIAL PRIMARY KEY,
                    record_type TEXT NOT NULL CHECK(record_type IN ('sale','purchase')),
                    seller TEXT,
                    supplier TEXT,
                    responsible TEXT NOT NULL,
                    buyer TEXT NOT NULL,
                    contact TEXT,
                    document_type TEXT,
                    document TEXT,
                    product TEXT NOT NULL,
                    price_type TEXT,
                    unit_price NUMERIC(14,2),
                    markup_percent NUMERIC(5,2) NOT NULL DEFAULT 0,
                    quantity NUMERIC(14,2) NOT NULL CHECK(quantity > 0),
                    total NUMERIC(14,2) NOT NULL CHECK(total >= 0),
                    record_date DATE NOT NULL,
                    delivery_status TEXT CHECK(delivery_status IN ('delivered','scheduled')),
                    delivery_date DATE,
                    notes TEXT,
                    created_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("ALTER TABLE trade_records ADD COLUMN IF NOT EXISTS price_type TEXT")
            cur.execute("ALTER TABLE trade_records ADD COLUMN IF NOT EXISTS unit_price NUMERIC(14,2)")
            cur.execute("ALTER TABLE trade_records ADD COLUMN IF NOT EXISTS markup_percent NUMERIC(5,2) NOT NULL DEFAULT 0")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_trade_records_date ON trade_records(record_date DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_trade_records_type ON trade_records(record_type)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_trade_records_delivery ON trade_records(delivery_status, delivery_date)")
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

@app.errorhandler(413)
def request_too_large(_error):
    flash(
        "As fotos chegaram grandes demais ao servidor. Volte em Nova entrega, escolha as fotos novamente e aguarde a otimização terminar antes de enviar.",
        "danger"
    )
    return redirect(request.referrer or url_for("submit"))

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
            cur.execute("""
                SELECT id, name, email, role, active, approved, created_at,
                       (profile_image IS NOT NULL) AS has_profile_image
                FROM users WHERE id=%s
            """, (uid,))
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

def staff_required(fn):
    """Acesso operacional: Gerente ou Hierarquia."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect(url_for("admin_login"))
        if user["role"] not in {"admin", "manager"}:
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

@app.before_request
def restrict_manager_access():
    """Gerente enxerga somente o núcleo operacional autorizado."""
    if request.endpoint in {None, "static"}:
        return None

    user = get_current_user()
    if not user or user["role"] != "manager":
        return None

    allowed = {
        # Navegação geral
        "index",
        "logout",

        # Painel normal de membro
        "member_home",
        "dashboard",
        "submit",
        "history",
        "profile_photo",
        "profile_photo_upload",
        "profile_photo_remove",
        "submission_image",
        "calculator",
        "calculator_app",

        # Painel operacional do Gerente
        "admin_dashboard",
        "admin_registrations",
        "admin_user_approve",
        "admin_user_reject",
        "admin_calculator",
        "admin_calculator_app",
        "admin_trades",
        "admin_trade_save",
        "admin_trade_delete",
        "admin_trade_mark_delivered",
    }

    if request.endpoint not in allowed:
        abort(403)

    return None


def material_image(title):
    """Retorna a imagem do material padrão pelo título da meta."""
    wanted = (title or "").strip().casefold()
    for material in PERSONAL_GOAL_CATALOG:
        if material["title"].strip().casefold() == wanted:
            return material["image"]
    return None


def money(value):
    try:
        v = float(value or 0)
    except Exception:
        v = 0
    formatted = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


@app.template_filter("dt")
def format_datetime(value):
    if not value:
        return "—"
    try:
        return value.strftime("%d/%m/%Y %H:%M")
    except AttributeError:
        text = str(value)
        return text.replace("T", " ")[:16]

@app.context_processor
def inject_globals():
    return {
        "current_user": get_current_user(),
        "csrf_token": csrf_token,
        "money": money,
        "material_image": material_image,
        "today": date.today(),
    }

def active_cycle_with_goals(user_id=None, open_only=False):
    """Retorna a meta ativa e o progresso do membro, incluindo créditos aplicados."""
    member_id = user_id or -1
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM cycles WHERE active=TRUE ORDER BY id DESC LIMIT 1")
            cycle = cur.fetchone()
            goals = []
            if cycle:
                sql = """
                    SELECT g.*,
                           COALESCE(SUM(s.amount) FILTER (WHERE s.status='approved'), 0) AS approved,
                           COALESCE(SUM(s.amount) FILTER (WHERE s.status='pending'), 0) AS pending
                    FROM goals g
                    LEFT JOIN submissions s
                      ON s.goal_id=g.id
                     AND s.user_id=%s
                     AND s.status IN ('approved','pending')
                    WHERE g.cycle_id=%s
                      AND g.user_id=%s
                """
                params = [member_id, cycle["id"], member_id]
                if open_only:
                    sql += " AND g.closed=FALSE"
                sql += " GROUP BY g.id ORDER BY g.sort_order, g.id"
                cur.execute(sql, params)
                rows = cur.fetchall()
                for row in rows:
                    item = dict(row)

                    # psycopg devolve campos NUMERIC como Decimal. Para o painel
                    # e os templates, normalizamos todos os valores usados em
                    # contas para float, evitando operações Decimal x float.
                    target = float(item.get("target") or 0)
                    approved = float(item.get("approved") or 0)
                    pending = float(item.get("pending") or 0)
                    credit = float(item.get("credit_applied") or 0)

                    item["target"] = target
                    item["approved"] = approved
                    item["pending"] = pending
                    item["original_target"] = target
                    item["credit_applied"] = credit
                    item["effective_target"] = max(target - credit, 0)
                    goals.append(item)
    return cycle, goals

@app.route("/")
def index():
    user = get_current_user()
    if user:
        return redirect(url_for("admin_dashboard" if user["role"] in {"admin","manager"} else "dashboard"))
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

        if not user["active"]:
            flash("Seu acesso está bloqueado. Procure um administrador.", "danger")
            return render_template("login.html")

        if not user["approved"]:
            flash("Cadastro aguardando aprovação de um administrador.", "danger")
            return render_template("login.html")

        remember_device = request.form.get("remember_device") == "1"
        session.clear()
        session.permanent = remember_device
        session["uid"] = user["id"]
        session["_csrf"] = secrets.token_urlsafe(24)
        return redirect(url_for("admin_dashboard" if user["role"] in {"admin","manager"} else "dashboard"))

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

        if user["role"] not in {"admin", "manager"}:
            flash("Esta conta não possui permissão para o painel.", "danger")
            return render_template("admin_login.html")

        if not user["active"]:
            flash("Esta conta de acesso ao painel está bloqueada.", "danger")
            return render_template("admin_login.html")

        remember_device = request.form.get("remember_device") == "1"
        session.clear()
        session.permanent = remember_device
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

        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
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

@app.route("/member")
@login_required
def member_home():
    return redirect(url_for("dashboard"))

@app.route("/admin-home")
@staff_required
def admin_home():
    return redirect(url_for("admin_dashboard"))


@app.post("/profile/photo")
@login_required
def profile_photo_upload():
    validate_csrf()
    user = get_current_user()
    image = request.files.get("profile_image")

    if not image or not image.filename:
        flash("Escolha uma foto para o perfil.", "danger")
        return redirect(request.referrer or url_for("dashboard"))

    data = image.read()
    mime = (image.mimetype or "").lower()
    allowed = {"image/jpeg", "image/png", "image/webp"}

    if mime not in allowed:
        flash("Use uma imagem JPG, PNG ou WEBP.", "danger")
        return redirect(request.referrer or url_for("dashboard"))

    if len(data) > 3 * 1024 * 1024:
        flash("A foto deve ter no máximo 3 MB.", "danger")
        return redirect(request.referrer or url_for("dashboard"))

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE users
                    SET profile_image=%s, profile_image_mime=%s
                    WHERE id=%s
                """, (data, mime, user["id"]))
            conn.commit()
    except Exception:
        app.logger.exception("Erro ao salvar foto de perfil")
        flash("Não foi possível salvar a foto de perfil. Tente novamente.", "danger")
        return redirect(request.referrer or url_for("dashboard"))

    flash("Foto de perfil atualizada.", "success")
    return redirect(request.referrer or url_for("dashboard"))


@app.post("/profile/photo/remove")
@login_required
def profile_photo_remove():
    validate_csrf()
    user = get_current_user()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET profile_image=NULL, profile_image_mime=NULL
                WHERE id=%s
            """, (user["id"],))
        conn.commit()

    flash("Foto de perfil removida.", "success")
    return redirect(request.referrer or url_for("dashboard"))


@app.get("/profile/photo/<int:user_id>")
@login_required
def profile_photo(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT profile_image, profile_image_mime
                FROM users
                WHERE id=%s
            """, (user_id,))
            row = cur.fetchone()

    if not row or not row["profile_image"]:
        abort(404)

    viewer = get_current_user()
    if viewer["role"] != "admin" and int(viewer["id"]) != int(user_id):
        abort(403)

    return send_file(
        BytesIO(bytes(row["profile_image"])),
        mimetype=row["profile_image_mime"] or "image/jpeg",
        as_attachment=False,
        download_name=f"perfil-{user_id}"
    )


@app.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    cycle, goals = active_cycle_with_goals(user["id"])

    # Mesma regra usada no Admin:
    # cada material tem o mesmo peso no percentual geral, independentemente
    # de a meta ser 10, 100 ou 10.000 unidades.
    total_target = 0.0
    total_approved = 0.0
    total_pending = 0.0
    goal_progress_sum = 0.0
    goal_pending_sum = 0.0
    goal_count = len(goals)

    for g in goals:
        required = float(g.get("effective_target", g["target"]) or 0)
        approved = float(g["approved"] or 0)
        pending = float(g["pending"] or 0)

        total_target += required
        total_approved += approved
        total_pending += pending

        if required <= 0:
            approved_ratio = 1.0
            pending_ratio = 0.0
        else:
            approved_ratio = min(approved / required, 1.0)
            pending_ratio = min(pending / required, max(1.0 - approved_ratio, 0.0))

        goal_progress_sum += approved_ratio
        goal_pending_sum += pending_ratio

    overall = round((goal_progress_sum / goal_count) * 100) if goal_count else 0
    overall_pending = round((goal_pending_sum / goal_count) * 100) if goal_count else 0
    overall_activity = min(100, overall + overall_pending)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.*, g.title AS goal_title, g.unit, c.title AS cycle_title
                FROM submissions s
                JOIN goals g ON g.id=s.goal_id
                JOIN cycles c ON c.id=g.cycle_id
                LEFT JOIN delivery_batches b ON b.id=s.batch_id
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

    return render_template(
        "dashboard.html",
        cycle=cycle,
        goals=goals,
        overall=overall,
        overall_pending=overall_pending,
        overall_activity=overall_activity,
        history=history,
        counts=counts
    )

@app.route("/submit", methods=["GET", "POST"])
@login_required
def submit():
    user = get_current_user()
    cycle, goals = active_cycle_with_goals(user["id"], open_only=True)
    if not cycle:
        flash("Não há meta ativa.", "danger")
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
                goal = valid_ids[goal_id]
                # Excedentes são permitidos. O que ultrapassar a necessidade da meta
                # só vira crédito após o fechamento feito pela Hierarquia.
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

            if len(data) > 950_000:
                flash("Uma das imagens não conseguiu ser otimizada o suficiente. Escolha a foto novamente e tente enviar.", "danger")
                return render_template("submit.html", cycle=cycle, goals=goals)

            images.append((data, image.mimetype, image.filename[:180]))

        if total_bytes > 2_800_000:
            flash("As fotos juntas ficaram grandes demais. Tente novamente; o IRON vai compactá-las antes do próximo envio.", "danger")
            return render_template("submit.html", cycle=cycle, goals=goals)

        while len(images) < 3:
            images.append((None, None, None))

        (img1, mime1, name1), (img2, mime2, name2), (img3, mime3, name3) = images

        # As imagens são gravadas UMA única vez no lote da entrega.
        # Cada item da meta apenas referencia esse lote.
        try:
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
        except Exception as exc:
            app.logger.exception(
                "Falha ao salvar entrega com imagens: user_id=%s cycle_id=%s",
                user["id"], cycle["id"]
            )
            flash(
                "Não foi possível concluir o envio. Sua conexão pode ter oscilado. Nenhuma entrega parcial foi salva; tente novamente.",
                "danger"
            )
            return render_template("submit.html", cycle=cycle, goals=goals), 503

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
                       ((b.image_data IS NOT NULL) OR (s.image_data IS NOT NULL)) AS has_image,
                       ((b.image2_data IS NOT NULL) OR (s.image2_data IS NOT NULL)) AS has_image2,
                       ((b.image3_data IS NOT NULL) OR (s.image3_data IS NOT NULL)) AS has_image3,
                       g.title AS goal_title, g.unit,
                       c.title AS cycle_title, c.start_date, c.end_date
                FROM submissions s
                JOIN goals g ON g.id=s.goal_id
                JOIN cycles c ON c.id=g.cycle_id
                LEFT JOIN delivery_batches b ON b.id=s.batch_id
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
@staff_required
def admin_dashboard():
    current = get_current_user()

    if current["role"] == "manager":
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM users WHERE role='user' AND approved=FALSE")
                pending_users = int(cur.fetchone()["c"] or 0)
                cur.execute("""
                    SELECT COUNT(*) AS c
                    FROM trade_records
                    WHERE record_type='sale'
                      AND delivery_status='scheduled'
                """)
                scheduled_deliveries = int(cur.fetchone()["c"] or 0)
                cur.execute("SELECT COUNT(*) AS c FROM trade_records WHERE record_date=CURRENT_DATE")
                today_records = int(cur.fetchone()["c"] or 0)
        return render_template(
            "manager_dashboard.html",
            pending_users=pending_users,
            scheduled_deliveries=scheduled_deliveries,
            today_records=today_records
        )

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM users WHERE role='user' AND approved=TRUE")
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
        # Toda nova meta passa a ser a meta ativa automaticamente.
        # Como o sistema trabalha com uma meta ativa por vez, desativamos a anterior.
        active = True
        if not title or not start_date or not end_date:
            flash("Preencha todos os campos da meta.", "danger")
        else:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE cycles SET active=FALSE")
                    cur.execute("""
                        INSERT INTO cycles(title,start_date,end_date,active)
                        VALUES(%s,%s,%s,%s) RETURNING id
                    """, (title, start_date, end_date, active))
                    cycle_id = cur.fetchone()["id"]
                conn.commit()
            flash("Meta criada e ativada automaticamente.", "success")
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
    flash("Meta ativada.", "success")
    return redirect(url_for("admin_cycles"))

@app.post("/admin/cycles/<int:cycle_id>/delete")
@admin_required
def admin_cycle_delete(cycle_id):
    validate_csrf()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title FROM cycles WHERE id=%s", (cycle_id,))
            cycle = cur.fetchone()
            if not cycle:
                abort(404)

            # Apaga o ciclo. As metas, entregas e lotes/histórico vinculados
            # são removidos automaticamente pelas chaves ON DELETE CASCADE.
            cur.execute("DELETE FROM cycles WHERE id=%s", (cycle_id,))
        conn.commit()

    flash(f"Meta '{cycle['title']}' excluída com todo o histórico relacionado.", "success")
    return redirect(url_for("admin_cycles"))


@app.route("/admin/cycles/<int:cycle_id>", methods=["GET"])
@admin_required
def admin_cycle_detail(cycle_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM cycles WHERE id=%s", (cycle_id,))
            cycle = cur.fetchone()
            if not cycle:
                abort(404)

            cur.execute("""
                SELECT g.*, u.name AS member_name
                FROM goals g
                LEFT JOIN users u ON u.id=g.user_id
                WHERE g.cycle_id=%s
                ORDER BY g.sort_order,g.id
            """, (cycle_id,))
            goals = cur.fetchall()

    return render_template("admin_cycle_detail.html", cycle=cycle, goals=goals)

@app.post("/admin/goals/<int:goal_id>/delete")
@admin_required
def admin_goal_delete(goal_id):
    validate_csrf()

    with get_conn() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM goals WHERE id=%s FOR UPDATE", (goal_id,))
                goal = cur.fetchone()
                if not goal:
                    abort(404)

                cycle_id = goal["cycle_id"]
                member_id = goal.get("user_id")

                # Se uma meta ainda aberta consumiu crédito anterior e for excluída,
                # devolve esse crédito ao saldo do membro.
                restored_credit = 0
                if member_id and not goal.get("closed") and abs(float(goal.get("credit_applied") or 0)) > 1e-9:
                    restored_credit = float(goal.get("credit_applied") or 0)
                    cur.execute("""
                        INSERT INTO member_goal_credits(user_id, goal_key, goal_title, unit, balance)
                        VALUES (%s,%s,%s,%s,%s)
                        ON CONFLICT (user_id, goal_key, unit)
                        DO UPDATE SET balance=member_goal_credits.balance+EXCLUDED.balance,
                                      goal_title=EXCLUDED.goal_title,
                                      updated_at=NOW()
                    """, (member_id, goal_credit_key(goal["title"]), goal["title"], goal["unit"], restored_credit))

                # Guarda os lotes das entregas desta meta antes de removê-la.
                # As fotos ficam em delivery_batches e podem ser compartilhadas quando
                # o membro envia várias metas no mesmo envio.
                cur.execute("""
                    SELECT DISTINCT batch_id
                    FROM submissions
                    WHERE goal_id=%s AND batch_id IS NOT NULL
                """, (goal_id,))
                batch_ids = [row["batch_id"] for row in cur.fetchall()]

                # Exclui todo o histórico desta meta personalizada. Isso também remove
                # imagens antigas que eventualmente estejam salvas diretamente em submissions.
                cur.execute("DELETE FROM submissions WHERE goal_id=%s", (goal_id,))

                # Agora a própria meta pode ser excluída, mesmo que já tivesse entregas.
                cur.execute("DELETE FROM goals WHERE id=%s", (goal_id,))

                # Remove apenas lotes/fotos que ficaram órfãos. Se o mesmo envio também
                # pertence a outra meta, o lote é preservado para não apagar o comprovante dela.
                if batch_ids:
                    cur.execute("""
                        DELETE FROM delivery_batches b
                        WHERE b.id = ANY(%s)
                          AND NOT EXISTS (
                              SELECT 1 FROM submissions s WHERE s.batch_id=b.id
                          )
                    """, (batch_ids,))

            conn.commit()
        except Exception:
            conn.rollback()
            app.logger.exception("Erro ao excluir meta personalizada: goal_id=%s", goal_id)
            flash("Não foi possível excluir a meta. Tente novamente.", "danger")
            if 'member_id' in locals() and member_id:
                return redirect(url_for("admin_member_goals", user_id=member_id))
            if 'cycle_id' in locals():
                return redirect(url_for("admin_cycle_detail", cycle_id=cycle_id))
            return redirect(url_for("admin_cycles"))

    flash("Meta e histórico relacionado excluídos.", "success")
    if member_id:
        return redirect(url_for("admin_member_goals", user_id=member_id))
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
            # Bloqueia a linha durante a revisão para impedir duas decisões
            # concorrentes sobre a mesma entrega.
            cur.execute("""
                SELECT id, status, batch_id, user_id
                FROM submissions
                WHERE id=%s
                FOR UPDATE
            """, (submission_id,))
            submission = cur.fetchone()

            if not submission:
                abort(404)

            if submission["status"] != "pending":
                conn.rollback()
                flash("Essa atualização já foi analisada e não foi alterada novamente.", "danger")
                return redirect(request.referrer or url_for("admin_submissions"))

            # Cada atualização pode conter vários produtos/metas. Quando existe
            # batch_id, a decisão deve ser aplicada ao lote inteiro, e não
            # somente ao produto cujo botão foi clicado.
            if submission["batch_id"] is not None:
                cur.execute("""
                    SELECT id
                    FROM submissions
                    WHERE batch_id=%s
                      AND user_id=%s
                      AND status='pending'
                    FOR UPDATE
                """, (submission["batch_id"], submission["user_id"]))
                batch_rows = cur.fetchall()
                batch_ids = [row["id"] for row in batch_rows]

                if batch_ids:
                    cur.execute("""
                        UPDATE submissions
                        SET status=%s,
                            admin_note=%s,
                            reviewed_at=NOW(),
                            reviewed_by=%s
                        WHERE id = ANY(%s)
                          AND status='pending'
                    """, (decision, admin_note, admin["id"], batch_ids))
                    reviewed_count = cur.rowcount
                else:
                    reviewed_count = 0
            else:
                # Compatibilidade com entregas antigas que não possuem lote.
                cur.execute("""
                    UPDATE submissions
                    SET status=%s,
                        admin_note=%s,
                        reviewed_at=NOW(),
                        reviewed_by=%s
                    WHERE id=%s
                      AND status='pending'
                """, (decision, admin_note, admin["id"], submission_id))
                reviewed_count = cur.rowcount
        conn.commit()

    if decision == "rejected":
        flash(
            f"Atualização recusada. {reviewed_count} produto(s) saíram de Em análise e não contam mais na porcentagem do membro.",
            "success"
        )
    else:
        flash(
            f"Atualização aprovada. {reviewed_count} produto(s) passaram de Em análise para Aprovado.",
            "success"
        )
    return redirect(request.referrer or url_for("admin_submissions"))

@app.route("/admin/registrations")
@staff_required
def admin_registrations():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, email, role, active, approved, created_at,
                       (profile_image IS NOT NULL) AS has_profile_image
                FROM users
                WHERE role='user' AND approved=FALSE
                ORDER BY created_at ASC
            """)
            users = cur.fetchall()
    return render_template("admin_registrations.html", users=users)

@app.route("/admin/members")
@admin_required
def admin_members():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM cycles WHERE active=TRUE ORDER BY id DESC LIMIT 1")
            cycle = cur.fetchone()

            cur.execute("""
                SELECT id, name, email, role, active, approved, created_at,
                       (profile_image IS NOT NULL) AS has_profile_image
                FROM users
                WHERE approved=TRUE
                ORDER BY LOWER(name) ASC, name ASC
            """)
            members = cur.fetchall()

            rows = []
            for member in members:
                total_target = 0.0
                total_approved = 0.0
                total_pending = 0.0
                goal_progress_sum = 0.0
                goal_pending_sum = 0.0
                goal_count = 0

                if cycle:
                    # O progresso geral precisa dar o mesmo peso a cada material.
                    # Somar quantidades brutas distorcia o percentual quando uma meta
                    # tinha muito mais unidades do que outra.
                    cur.execute("""
                        SELECT g.id, g.target, g.credit_applied,
                               COALESCE(SUM(CASE WHEN s.status='approved' THEN s.amount ELSE 0 END),0) AS approved,
                               COALESCE(SUM(CASE WHEN s.status='pending' THEN s.amount ELSE 0 END),0) AS pending
                        FROM goals g
                        LEFT JOIN submissions s
                          ON s.goal_id=g.id
                         AND s.user_id=%s
                        WHERE g.cycle_id=%s
                          AND g.user_id=%s
                        GROUP BY g.id
                        ORDER BY g.sort_order, g.id
                    """, (member["id"], cycle["id"], member["id"]))
                    goal_rows = cur.fetchall()

                    for g in goal_rows:
                        original_target = float(g["target"] or 0)
                        credit_applied = float(g.get("credit_applied") or 0)
                        required = max(original_target - credit_applied, 0)
                        approved = float(g["approved"] or 0)
                        pending = float(g["pending"] or 0)

                        total_target += required
                        total_approved += approved
                        total_pending += pending
                        goal_count += 1

                        if required <= 0:
                            approved_ratio = 1.0
                            pending_ratio = 0.0
                        else:
                            approved_ratio = min(approved / required, 1.0)
                            pending_ratio = min(pending / required, max(1.0 - approved_ratio, 0.0))

                        goal_progress_sum += approved_ratio
                        goal_pending_sum += pending_ratio

                percent = round((goal_progress_sum / goal_count) * 100) if goal_count else 0
                pending_percent = round((goal_pending_sum / goal_count) * 100) if goal_count else 0
                rows.append({
                    "id": member["id"],
                    "name": member["name"],
                    "email": member["email"],
                    "role": member["role"],
                    "has_profile_image": member.get("has_profile_image", False),
                    "active": member["active"],
                    "approved": member["approved"],
                    "created_at": member["created_at"],
                    "target": total_target,
                    "approved_total": total_approved,
                    "pending_total": total_pending,
                    "percent": percent,
                    "pending_percent": pending_percent,
                    "remaining": max(total_target - total_approved, 0),
                })

    return render_template("admin_members.html", members=rows, cycle=cycle)


@app.route("/admin/members/<int:user_id>")
@admin_required
def admin_member_detail(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, email, active, approved, created_at,
                       (profile_image IS NOT NULL) AS has_profile_image
                FROM users
                WHERE id=%s
            """, (user_id,))
            member = cur.fetchone()
            if not member:
                abort(404)

            cur.execute("SELECT * FROM cycles WHERE active=TRUE ORDER BY id DESC LIMIT 1")
            cycle = cur.fetchone()

            total_target = total_approved = total_pending = 0.0
            goals_completed = goals_total = 0
            goal_progress_sum = 0.0
            goal_pending_sum = 0.0

            if cycle:
                cur.execute("""
                    SELECT g.id, g.target, g.credit_applied,
                           COALESCE(SUM(CASE WHEN s.status='approved' THEN s.amount ELSE 0 END),0) AS approved,
                           COALESCE(SUM(CASE WHEN s.status='pending' THEN s.amount ELSE 0 END),0) AS pending
                    FROM goals g
                    LEFT JOIN submissions s ON s.goal_id=g.id AND s.user_id=%s
                    WHERE g.cycle_id=%s
                      AND g.user_id=%s
                    GROUP BY g.id
                    ORDER BY g.sort_order, g.id
                """, (user_id, cycle["id"], user_id))
                goal_rows = cur.fetchall()
                goals_total = len(goal_rows)
                for g in goal_rows:
                    original_target = float(g["target"] or 0)
                    credit_applied = float(g.get("credit_applied") or 0)
                    target = max(original_target - credit_applied, 0)
                    approved = float(g["approved"] or 0)
                    pending = float(g["pending"] or 0)
                    total_target += target
                    total_approved += approved
                    total_pending += pending

                    if target <= 0:
                        approved_ratio = 1.0
                        pending_ratio = 0.0
                        goals_completed += 1
                    else:
                        approved_ratio = min(approved / target, 1.0)
                        pending_ratio = min(pending / target, max(1.0 - approved_ratio, 0.0))
                        if approved >= target:
                            goals_completed += 1

                    goal_progress_sum += approved_ratio
                    goal_pending_sum += pending_ratio

            # Percentual geral = média do progresso de cada material, e não
            # soma de unidades de materiais diferentes.
            overall = round((goal_progress_sum / goals_total) * 100) if goals_total else 0
            overall_pending = round((goal_pending_sum / goals_total) * 100) if goals_total else 0

            cur.execute("""
                SELECT COUNT(*) FILTER (WHERE status='pending') AS pending_count,
                       COUNT(*) FILTER (WHERE status='approved') AS approved_count,
                       COUNT(*) FILTER (WHERE status='rejected') AS rejected_count,
                       COUNT(*) AS total_count
                FROM submissions
                WHERE user_id=%s
            """, (user_id,))
            submission_counts = cur.fetchone()

    return render_template(
        "admin_member_detail.html",
        member=member,
        cycle=cycle,
        overall=overall,
        overall_pending=overall_pending,
        total_target=total_target,
        total_approved=total_approved,
        total_pending=total_pending,
        remaining=max(total_target-total_approved, 0),
        goals_completed=goals_completed,
        goals_total=goals_total,
        submission_counts=submission_counts
    )


@app.route("/admin/members/<int:user_id>/goals", methods=["GET", "POST"])
@admin_required
def admin_member_goals(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Garante que bancos criados em versões antigas tenham a coluna necessária.
            cur.execute("""
                ALTER TABLE goals
                ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES users(id) ON DELETE CASCADE
            """)

            cur.execute("""
                SELECT id, name, email, active, approved,
                       (profile_image IS NOT NULL) AS has_profile_image
                FROM users
                WHERE id=%s
            """, (user_id,))
            member = cur.fetchone()
            if not member:
                abort(404)

            cur.execute("""
                SELECT *
                FROM cycles
                WHERE active=TRUE
                ORDER BY id DESC
                LIMIT 1
            """)
            cycle = cur.fetchone()

            if request.method == "POST":
                validate_csrf()

                if not cycle:
                    flash("Não existe meta ativa. Crie e ative uma meta primeiro.", "danger")
                    return redirect(url_for("admin_member_goals", user_id=user_id))

                selected_materials = []
                for material in PERSONAL_GOAL_CATALOG:
                    raw = (request.form.get(f"qty_{material['key']}") or "").strip().replace(",", ".")
                    if not raw:
                        continue
                    try:
                        qty = float(raw)
                    except (TypeError, ValueError):
                        qty = 0
                    if qty > 0:
                        selected_materials.append((material, qty))

                if not selected_materials:
                    flash("Informe a quantidade de pelo menos um material.", "danger")
                    return redirect(url_for("admin_member_goals", user_id=user_id))

                created = []
                try:
                    for material, target in selected_materials:
                        cur.execute("""
                            SELECT COALESCE(MAX(sort_order),0)+1 AS next_order
                            FROM goals
                            WHERE cycle_id=%s AND user_id=%s
                        """, (cycle["id"], user_id))
                        sort_order = int(cur.fetchone()["next_order"] or 1)

                        goal_key = goal_credit_key(material["title"])
                        cur.execute("""
                            SELECT id, balance
                            FROM member_goal_credits
                            WHERE user_id=%s AND goal_key=%s AND unit=%s
                            FOR UPDATE
                        """, (user_id, goal_key, material["unit"]))
                        credit_row = cur.fetchone()
                        credit_applied = float(credit_row["balance"] or 0) if credit_row else 0

                        if credit_row and abs(credit_applied) > 1e-9:
                            cur.execute("""
                                UPDATE member_goal_credits
                                SET balance=0, updated_at=NOW()
                                WHERE id=%s
                            """, (credit_row["id"],))

                        cur.execute("""
                            INSERT INTO goals (
                                cycle_id, title, category, target, unit, icon,
                                sort_order, user_id, credit_applied, closed
                            )
                            VALUES (%s,%s,'MATERIAL',%s,%s,%s,%s,%s,%s,FALSE)
                            RETURNING id
                        """, (
                            cycle["id"], material["title"], target, material["unit"],
                            material["icon"], sort_order, user_id, credit_applied
                        ))
                        new_goal_id = cur.fetchone()["id"]

                        if abs(credit_applied) > 1e-9:
                            cur.execute("""
                                UPDATE goal_closures
                                SET applied_to_goal_id=%s, consumed_at=NOW()
                                WHERE user_id=%s
                                  AND unit=%s
                                  AND LOWER(REGEXP_REPLACE(TRIM(goal_title), '\\s+', ' ', 'g'))=%s
                                  AND consumed_at IS NULL
                                  AND carried_balance <> 0
                            """, (new_goal_id, user_id, material["unit"], goal_key))

                        created.append(material["title"])

                    conn.commit()
                except Exception:
                    conn.rollback()
                    app.logger.exception("Erro ao criar metas padronizadas: user_id=%s cycle_id=%s", user_id, cycle["id"])
                    flash("Não foi possível criar as metas. Tente novamente.", "danger")
                    return redirect(url_for("admin_member_goals", user_id=user_id))

                flash(f"{len(created)} meta(s) criada(s): " + ", ".join(created) + ".", "success")
                return redirect(url_for("admin_member_goals", user_id=user_id))

            goals = []
            if cycle:
                cur.execute("""
                    SELECT g.*,
                           COALESCE(SUM(CASE WHEN s.status='approved' THEN s.amount ELSE 0 END),0) AS approved,
                           COALESCE(SUM(CASE WHEN s.status='pending' THEN s.amount ELSE 0 END),0) AS pending,
                           COALESCE(SUM(CASE WHEN s.status='rejected' THEN s.amount ELSE 0 END),0) AS rejected
                    FROM goals g
                    LEFT JOIN submissions s
                      ON s.goal_id=g.id
                     AND s.user_id=%s
                    WHERE g.cycle_id=%s
                      AND g.user_id=%s
                    GROUP BY g.id
                    ORDER BY g.sort_order, g.id
                """, (user_id, cycle["id"], user_id))
                rows = cur.fetchall()

                for g in rows:
                    target = float(g["target"] or 0)
                    credit_applied = float(g.get("credit_applied") or 0)
                    required = max(target - credit_applied, 0)
                    approved = float(g["approved"] or 0)
                    pending = float(g["pending"] or 0)
                    remaining = max(required - approved, 0)
                    surplus = max(approved - required, 0)
                    percent = min(100, round((approved / required) * 100)) if required else 100

                    goals.append({
                        **dict(g),
                        "target_f": target,
                        "credit_applied_f": credit_applied,
                        "required_f": required,
                        "approved_f": approved,
                        "pending_f": pending,
                        "remaining": remaining,
                        "surplus": surplus,
                        "difference": surplus if surplus > 0 else (-remaining if remaining > 0 else 0),
                        "percent": percent,
                        "complete": required <= 0 or approved >= required,
                    })

            cur.execute("""
                SELECT id, goal_title, unit, balance
                FROM member_goal_credits
                WHERE user_id=%s AND ABS(balance)>0
                ORDER BY goal_title ASC
            """, (user_id,))
            credits = cur.fetchall()

    return render_template(
        "admin_member_goals.html",
        member=member,
        cycle=cycle,
        goals=goals,
        credits=credits,
        personal_goal_catalog=PERSONAL_GOAL_CATALOG
    )




@app.post("/admin/members/<int:user_id>/goals/close")
@admin_required
def admin_member_goals_close(user_id):
    validate_csrf()
    admin = get_current_user()

    with get_conn() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, name, role, approved, active FROM users WHERE id=%s", (user_id,))
                member = cur.fetchone()
                if not member:
                    conn.rollback()
                    flash("Membro não encontrado. Atualize a lista de membros e tente novamente.", "danger")
                    return redirect(url_for("admin_members"))

                cur.execute("SELECT * FROM cycles WHERE active=TRUE ORDER BY id DESC LIMIT 1")
                cycle = cur.fetchone()
                if not cycle:
                    flash("Não existe meta ativa para fechar.", "danger")
                    return redirect(url_for("admin_member_goals", user_id=user_id))

                cur.execute("""
                    SELECT COUNT(*) AS c
                    FROM submissions s
                    JOIN goals g ON g.id=s.goal_id
                    WHERE s.user_id=%s
                      AND g.cycle_id=%s
                      AND g.user_id=%s
                      AND g.closed=FALSE
                      AND s.status='pending'
                """, (user_id, cycle["id"], user_id))
                if int(cur.fetchone()["c"] or 0) > 0:
                    flash("Ainda existem entregas Em análise. Aprove ou recuse tudo antes de fechar a meta.", "danger")
                    return redirect(url_for("admin_member_goals", user_id=user_id))

                # Primeiro trava somente as linhas de metas. O PostgreSQL pode
                # rejeitar FOR UPDATE em consultas que misturam agregação/subquery.
                cur.execute("""
                    SELECT g.*
                    FROM goals g
                    WHERE g.cycle_id=%s
                      AND g.user_id=%s
                      AND g.closed=FALSE
                    ORDER BY g.sort_order,g.id
                    FOR UPDATE
                """, (cycle["id"], user_id))
                rows = cur.fetchall()

                # Soma os aprovados separadamente para manter o fechamento simples
                # e compatível com o PostgreSQL/Neon.
                for row in rows:
                    cur.execute("""
                        SELECT COALESCE(SUM(amount),0) AS approved
                        FROM submissions
                        WHERE goal_id=%s
                          AND user_id=%s
                          AND status='approved'
                    """, (row["id"], user_id))
                    row["approved"] = cur.fetchone()["approved"]

                if not rows:
                    flash("Não há metas abertas deste membro para fechar.", "danger")
                    return redirect(url_for("admin_member_goals", user_id=user_id))

                positive_generated = 0
                negative_generated = 0
                closed_count = 0

                for g in rows:
                    target = float(g["target"] or 0)
                    credit_applied = float(g.get("credit_applied") or 0)
                    required_target = max(target - credit_applied, 0)
                    approved = float(g["approved"] or 0)
                    surplus = max(approved - required_target, 0)
                    shortfall = max(required_target - approved, 0)

                    # V25: decisão simples por produto.
                    # "carry" leva a diferença real para a próxima meta;
                    # "zero" encerra o produto sem gerar saldo.
                    close_action = (request.form.get(f"carry_{g['id']}") or "carry").strip().lower()
                    signed_balance = 0
                    if close_action == "carry":
                        if surplus > 0:
                            signed_balance = surplus
                        elif shortfall > 0:
                            signed_balance = -shortfall

                    cur.execute("""
                        INSERT INTO goal_closures(
                            user_id, cycle_id, goal_id, goal_title, unit,
                            target, credit_applied, required_target, approved,
                            surplus, shortfall, carried_balance, closed_by
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (goal_id) DO NOTHING
                    """, (
                        user_id, cycle["id"], g["id"], g["title"], g["unit"],
                        target, credit_applied, required_target, approved,
                        surplus, shortfall, signed_balance, admin["id"]
                    ))

                    if cur.rowcount:
                        closed_count += 1

                        if signed_balance > 0:
                            positive_generated += signed_balance
                        elif signed_balance < 0:
                            negative_generated += abs(signed_balance)

                        if abs(signed_balance) > 1e-9:
                            cur.execute("""
                                INSERT INTO member_goal_credits(
                                    user_id, goal_key, goal_title, unit, balance
                                )
                                VALUES (%s,%s,%s,%s,%s)
                                ON CONFLICT (user_id, goal_key, unit)
                                DO UPDATE SET
                                    balance=member_goal_credits.balance+EXCLUDED.balance,
                                    goal_title=EXCLUDED.goal_title,
                                    updated_at=NOW()
                            """, (
                                user_id, goal_credit_key(g["title"]), g["title"],
                                g["unit"], signed_balance
                            ))

                    cur.execute("UPDATE goals SET closed=TRUE WHERE id=%s", (g["id"],))

            conn.commit()
        except HTTPException:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            app.logger.exception("Erro ao fechar metas do membro: user_id=%s", user_id)
            flash(f"Não foi possível fechar a meta ({type(exc).__name__}). Tente novamente.", "danger")
            return redirect(url_for("admin_member_goals", user_id=user_id))

    flash(
        f"Fechamento concluído: {closed_count} meta(s). "
        f"Saldo positivo: +{positive_generated:g}. "
        f"Saldo negativo: -{negative_generated:g}.",
        "success"
    )
    return redirect(url_for("admin_member_history", user_id=user_id))


@app.post("/admin/members/<int:user_id>/credits/<int:credit_id>/adjust")
@admin_required
def admin_member_credit_adjust(user_id, credit_id):
    validate_csrf()

    raw = (request.form.get("balance") or "").strip().replace(",", ".")
    try:
        new_balance = float(raw)
    except (TypeError, ValueError):
        flash("Informe um saldo válido.", "danger")
        return redirect(request.referrer or url_for("admin_member_goals", user_id=user_id))

    with get_conn() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, goal_title, unit
                    FROM member_goal_credits
                    WHERE id=%s AND user_id=%s
                    FOR UPDATE
                """, (credit_id, user_id))
                credit = cur.fetchone()
                if not credit:
                    flash("Saldo não encontrado.", "danger")
                    return redirect(request.referrer or url_for("admin_member_goals", user_id=user_id))

                if abs(new_balance) <= 1e-9:
                    cur.execute("DELETE FROM member_goal_credits WHERE id=%s", (credit_id,))
                else:
                    cur.execute("""
                        UPDATE member_goal_credits
                        SET balance=%s, updated_at=NOW()
                        WHERE id=%s
                    """, (new_balance, credit_id))
            conn.commit()
        except Exception as exc:
            conn.rollback()
            app.logger.exception("Erro ao ajustar saldo: user_id=%s credit_id=%s", user_id, credit_id)
            flash(f"Não foi possível ajustar o saldo ({type(exc).__name__}).", "danger")
            return redirect(request.referrer or url_for("admin_member_goals", user_id=user_id))

    flash(
        f"Saldo de {credit['goal_title']} atualizado para {new_balance:+g} {credit['unit']}."
        if abs(new_balance) > 1e-9 else
        f"Saldo de {credit['goal_title']} zerado.",
        "success"
    )
    return redirect(request.referrer or url_for("admin_member_goals", user_id=user_id))


@app.post("/admin/members/<int:user_id>/credits/<int:credit_id>/delete")
@admin_required
def admin_member_credit_delete(user_id, credit_id):
    validate_csrf()

    with get_conn() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, user_id, goal_title, unit, balance
                    FROM member_goal_credits
                    WHERE id=%s AND user_id=%s
                    FOR UPDATE
                """, (credit_id, user_id))
                credit = cur.fetchone()

                if not credit:
                    flash("Saldo não encontrado ou já removido.", "danger")
                    return redirect(request.referrer or url_for("admin_member_goals", user_id=user_id))

                cur.execute(
                    "DELETE FROM member_goal_credits WHERE id=%s AND user_id=%s",
                    (credit_id, user_id)
                )

            conn.commit()
        except HTTPException:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            app.logger.exception(
                "Erro ao excluir saldo manual: user_id=%s credit_id=%s",
                user_id, credit_id
            )
            flash(f"Não foi possível excluir o saldo ({type(exc).__name__}).", "danger")
            return redirect(request.referrer or url_for("admin_member_goals", user_id=user_id))

    flash(
        f"Saldo de {credit['goal_title']} removido. Ele não será aplicado na próxima meta.",
        "success"
    )
    return redirect(request.referrer or url_for("admin_member_goals", user_id=user_id))


@app.post("/admin/members/<int:user_id>/closures/<int:closure_id>/delete")
@admin_required
def admin_member_closure_delete(user_id, closure_id):
    validate_csrf()

    with get_conn() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT gc.*, g.id AS source_goal_id, g.title AS source_goal_title,
                           g.unit AS source_goal_unit
                    FROM goal_closures gc
                    JOIN goals g ON g.id=gc.goal_id
                    WHERE gc.id=%s
                      AND gc.user_id=%s
                      AND gc.consumed_at IS NULL
                    FOR UPDATE OF gc, g
                """, (closure_id, user_id))
                closure = cur.fetchone()

                if not closure:
                    flash("Fechamento não encontrado.", "danger")
                    return redirect(url_for("admin_member_history", user_id=user_id))

                carried = float(closure.get("carried_balance") or 0)

                # Compatibilidade com fechamentos antigos (V16–V20), que ainda
                # não gravavam exatamente o saldo transportado.
                if abs(carried) <= 1e-9:
                    surplus = float(closure.get("surplus") or 0)
                    shortfall = float(closure.get("shortfall") or 0)
                    if surplus > 0:
                        carried = surplus
                    elif shortfall > 0:
                        carried = -shortfall

                remaining = carried
                goal_key = goal_credit_key(closure["goal_title"])
                unit = closure["unit"]

                # Primeiro desfaz a parte que ainda está parada no saldo.
                cur.execute("""
                    SELECT id, balance
                    FROM member_goal_credits
                    WHERE user_id=%s AND goal_key=%s AND unit=%s
                    FOR UPDATE
                """, (user_id, goal_key, unit))
                credit_row = cur.fetchone()

                if credit_row and abs(remaining) > 1e-9:
                    balance = float(credit_row["balance"] or 0)

                    if remaining > 0 and balance > 0:
                        take = min(balance, remaining)
                        balance -= take
                        remaining -= take
                    elif remaining < 0 and balance < 0:
                        take = min(abs(balance), abs(remaining))
                        balance += take
                        remaining += take

                    cur.execute("""
                        UPDATE member_goal_credits
                        SET balance=%s, updated_at=NOW()
                        WHERE id=%s
                    """, (balance, credit_row["id"]))

                # Se o saldo já foi consumido por uma meta posterior, desfaz a
                # aplicação naquela meta. Assim a quantidade necessária se ajusta.
                if abs(remaining) > 1e-9:
                    cur.execute("""
                        SELECT id, credit_applied
                        FROM goals
                        WHERE user_id=%s
                          AND LOWER(REGEXP_REPLACE(TRIM(title), '\\s+', ' ', 'g'))=%s
                          AND unit=%s
                          AND id>%s
                          AND (
                              (%s > 0 AND credit_applied > 0)
                              OR
                              (%s < 0 AND credit_applied < 0)
                          )
                        ORDER BY id ASC
                        FOR UPDATE
                    """, (
                        user_id, goal_key, unit, closure["goal_id"],
                        remaining, remaining
                    ))
                    later_goals = cur.fetchall()

                    for later in later_goals:
                        if abs(remaining) <= 1e-9:
                            break

                        applied = float(later["credit_applied"] or 0)

                        if remaining > 0 and applied > 0:
                            take = min(applied, remaining)
                            applied -= take
                            remaining -= take
                        elif remaining < 0 and applied < 0:
                            take = min(abs(applied), abs(remaining))
                            applied += take
                            remaining += take
                        else:
                            continue

                        cur.execute(
                            "UPDATE goals SET credit_applied=%s WHERE id=%s",
                            (applied, later["id"])
                        )

                # Se ainda restar valor sem conseguir desfazer, não apagamos.
                # Isso evita corromper o extrato em cenários antigos/atípicos.
                if abs(remaining) > 1e-6:
                    conn.rollback()
                    flash(
                        "Não foi possível excluir este fechamento porque parte do saldo já foi usada "
                        "de uma forma que não pôde ser revertida automaticamente.",
                        "danger"
                    )
                    return redirect(url_for("admin_member_history", user_id=user_id))

                # Reabre a meta original para permitir correção e novo fechamento.
                cur.execute("UPDATE goals SET closed=FALSE WHERE id=%s", (closure["goal_id"],))
                cur.execute("DELETE FROM goal_closures WHERE id=%s", (closure_id,))

            conn.commit()
        except HTTPException:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            app.logger.exception(
                "Erro ao excluir fechamento: user_id=%s closure_id=%s",
                user_id, closure_id
            )
            flash(f"Não foi possível excluir o fechamento ({type(exc).__name__}).", "danger")
            return redirect(url_for("admin_member_history", user_id=user_id))

    flash("Fechamento excluído manualmente e saldo relacionado desfeito.", "success")
    return redirect(url_for("admin_member_history", user_id=user_id))


@app.route("/admin/members/<int:user_id>/history")
@admin_required
def admin_member_history(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, email, active, approved,
                       (profile_image IS NOT NULL) AS has_profile_image
                FROM users
                WHERE id=%s
            """, (user_id,))
            member = cur.fetchone()
            if not member:
                abort(404)

            cur.execute("""
                SELECT s.id, s.amount, s.note, s.status, s.admin_note,
                       s.created_at, s.reviewed_at,
                       ((b.image_data IS NOT NULL) OR (s.image_data IS NOT NULL)) AS has_image,
                       ((b.image2_data IS NOT NULL) OR (s.image2_data IS NOT NULL)) AS has_image2,
                       ((b.image3_data IS NOT NULL) OR (s.image3_data IS NOT NULL)) AS has_image3,
                       g.title AS goal_title, g.unit,
                       c.title AS cycle_title
                FROM submissions s
                JOIN goals g ON g.id=s.goal_id
                JOIN cycles c ON c.id=g.cycle_id
                LEFT JOIN delivery_batches b ON b.id=s.batch_id
                WHERE s.user_id=%s
                ORDER BY s.created_at DESC, s.id DESC
            """, (user_id,))
            history = cur.fetchall()

            cur.execute("""
                SELECT gc.*, c.title AS cycle_title, c.start_date, c.end_date
                FROM goal_closures gc
                JOIN cycles c ON c.id=gc.cycle_id
                WHERE gc.user_id=%s
                ORDER BY gc.closed_at DESC, gc.id DESC
            """, (user_id,))
            closures = cur.fetchall()

            cur.execute("""
                SELECT id, goal_title, unit, balance, updated_at
                FROM member_goal_credits
                WHERE user_id=%s AND ABS(balance)>0
                ORDER BY goal_title ASC
            """, (user_id,))
            credits = cur.fetchall()

    return render_template(
        "admin_member_history.html",
        member=member,
        history=history,
        closures=closures,
        credits=credits
    )



@app.route("/admin/permissions")
@admin_required
def admin_permissions():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, email, role, active, approved, created_at,
                       (profile_image IS NOT NULL) AS has_profile_image
                FROM users
                WHERE approved=TRUE
                ORDER BY CASE WHEN role='admin' THEN 0 WHEN role='manager' THEN 1 ELSE 2 END, name ASC
            """)
            users = cur.fetchall()
    return render_template("admin_permissions.html", users=users)


@app.route("/admin/users")
@admin_required
def admin_users():
    return redirect(url_for("admin_members"))


@app.post("/admin/members/<int:user_id>/delete")
@admin_required
def admin_member_delete(user_id):
    validate_csrf()
    current = get_current_user()

    if int(user_id) == int(current["id"]):
        flash("Você não pode excluir sua própria conta por esta tela.", "danger")
        return redirect(url_for("admin_members"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, email, role
                FROM users
                WHERE id=%s
            """, (user_id,))
            member = cur.fetchone()

            if not member:
                abort(404)

            if member["role"] == "admin":
                flash("Para excluir um administrador, remova primeiro a permissão Admin.", "danger")
                return redirect(url_for("admin_permissions"))

            # A exclusão do usuário remove entregas e lotes vinculados por CASCADE.
            cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
        conn.commit()

    flash(f"Membro '{member['name']}' excluído totalmente do sistema.", "success")
    return redirect(url_for("admin_members"))


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
@staff_required
def admin_user_approve(user_id):
    validate_csrf()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET approved=TRUE, active=TRUE
                WHERE id=%s
            """, (user_id,))
        conn.commit()
    flash("Membro aprovado e liberado para acessar o painel.", "success")
    return redirect(request.referrer or url_for("admin_registrations"))

@app.post("/admin/users/<int:user_id>/reject")
@staff_required
def admin_user_reject(user_id):
    validate_csrf()
    # Uma solicitação recusada não deve continuar aparecendo como pendente.
    # Como o usuário ainda não foi aprovado, removemos o cadastro pendente;
    # isso também permite que ele faça uma nova solicitação no futuro.
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM users
                WHERE id=%s AND role='user' AND approved=FALSE
                RETURNING name
            """, (user_id,))
            rejected = cur.fetchone()
        conn.commit()

    if rejected:
        flash("Cadastro recusado e removido das solicitações pendentes.", "success")
    else:
        flash("Esse cadastro não está mais pendente ou não pode ser recusado.", "danger")
    return redirect(url_for("admin_registrations"))

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
    return redirect(url_for("admin_permissions"))

@app.post("/admin/users/<int:user_id>/make-manager")
@admin_required
def admin_user_make_manager(user_id):
    validate_csrf()
    if int(user_id) == int(get_current_user()["id"]):
        flash("Você não pode alterar seu próprio cargo por esta tela.", "danger")
        return redirect(url_for("admin_permissions"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET role='manager', approved=TRUE, active=TRUE
                WHERE id=%s AND role<>'admin'
            """, (user_id,))
        conn.commit()

    flash("Cargo Gerente concedido. A conta terá acesso apenas a Cadastros, Calculadora e Compras & Vendas.", "success")
    return redirect(url_for("admin_permissions"))


@app.post("/admin/users/<int:user_id>/remove-manager")
@admin_required
def admin_user_remove_manager(user_id):
    validate_csrf()
    if int(user_id) == int(get_current_user()["id"]):
        flash("Você não pode alterar seu próprio cargo por esta tela.", "danger")
        return redirect(url_for("admin_permissions"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET role='user', approved=TRUE, active=TRUE
                WHERE id=%s AND role='manager'
            """, (user_id,))
        conn.commit()

    flash("Cargo Gerente removido. A conta voltou a ser Membro.", "success")
    return redirect(url_for("admin_permissions"))


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
    return redirect(url_for("admin_permissions"))




@app.route("/calculadora")
@login_required
def calculator():
    return render_template("admin_calculator.html", calculator_member=True)


@app.route("/calculadora/app")
@login_required
def calculator_app():
    return render_template("admin_calculator_app.html")



def parse_trade_number(raw):
    value = (raw or "").strip()
    if not value:
        return 0.0
    # Aceita "1.234,56", "1234,56", "1234.56" e valores com R$.
    value = re.sub(r"[^\d,.\-]", "", value)
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@app.route("/admin/compras-vendas")
@staff_required
def admin_trades():
    view = (request.args.get("view") or "overview").lower()
    if view not in {"overview", "sale", "purchase", "history"}:
        view = "overview"

    q = (request.args.get("q") or "").strip()
    kind = (request.args.get("type") or "all").lower()
    if kind not in {"all", "sale", "purchase"}:
        kind = "all"
    date_from = (request.args.get("from") or "").strip()
    date_to = (request.args.get("to") or "").strip()
    edit_id = request.args.get("edit", type=int)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COALESCE(SUM(total) FILTER (
                        WHERE record_type='sale'
                          AND DATE_TRUNC('month', record_date)=DATE_TRUNC('month', CURRENT_DATE)
                    ),0) AS month_sales,
                    COALESCE(SUM(total) FILTER (
                        WHERE record_type='purchase'
                          AND DATE_TRUNC('month', record_date)=DATE_TRUNC('month', CURRENT_DATE)
                    ),0) AS month_purchases,
                    COUNT(*) FILTER (
                        WHERE record_type='sale'
                          AND delivery_status='scheduled'
                    ) AS scheduled_deliveries,
                    COUNT(*) FILTER (
                        WHERE record_date=CURRENT_DATE
                    ) AS today_records
                FROM trade_records
            """)
            stats = dict(cur.fetchone())
            stats["month_sales"] = float(stats["month_sales"] or 0)
            stats["month_purchases"] = float(stats["month_purchases"] or 0)
            stats["month_balance"] = stats["month_sales"] - stats["month_purchases"]

            cur.execute("""
                SELECT *
                FROM trade_records
                WHERE record_type='sale'
                  AND delivery_status='scheduled'
                ORDER BY delivery_date NULLS LAST, id DESC
                LIMIT 6
            """)
            scheduled = cur.fetchall()

            params = []
            where = []
            if kind != "all":
                where.append("record_type=%s")
                params.append(kind)
            if q:
                where.append("""
                    (
                        COALESCE(seller,'') ILIKE %s OR
                        COALESCE(supplier,'') ILIKE %s OR
                        COALESCE(responsible,'') ILIKE %s OR
                        COALESCE(buyer,'') ILIKE %s OR
                        COALESCE(contact,'') ILIKE %s OR
                        COALESCE(document,'') ILIKE %s OR
                        COALESCE(product,'') ILIKE %s
                    )
                """)
                like = f"%{q}%"
                params.extend([like] * 7)
            if date_from:
                where.append("record_date >= %s")
                params.append(date_from)
            if date_to:
                where.append("record_date <= %s")
                params.append(date_to)

            sql = "SELECT * FROM trade_records"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY record_date DESC, updated_at DESC, id DESC LIMIT 250"
            cur.execute(sql, params)
            records = cur.fetchall()

            edit_record = None
            if edit_id:
                cur.execute("SELECT * FROM trade_records WHERE id=%s", (edit_id,))
                edit_record = cur.fetchone()

    return render_template(
        "admin_trades.html",
        view=view,
        stats=stats,
        scheduled=scheduled,
        records=records,
        edit_record=edit_record,
        q=q,
        kind=kind,
        date_from=date_from,
        date_to=date_to,
        trade_products=TRADE_PRODUCTS,
    )


@app.post("/admin/compras-vendas/save")
@staff_required
def admin_trade_save():
    validate_csrf()
    admin = get_current_user()

    record_id = request.form.get("record_id", type=int)
    record_type = (request.form.get("record_type") or "").strip().lower()
    if record_type not in {"sale", "purchase"}:
        abort(400)

    responsible = (request.form.get("responsible") or "").strip()
    buyer = (request.form.get("buyer") or "").strip()
    product = (request.form.get("product") or "").strip()
    record_date = (request.form.get("record_date") or "").strip()
    quantity = parse_trade_number(request.form.get("quantity"))
    notes = (request.form.get("notes") or "").strip() or None

    if record_type == "sale":
        # Venda continua padronizada e protegida pela tabela oficial.
        document_type = (request.form.get("document_type") or "").strip()
        price_type = document_type
        product_prices = TRADE_PRODUCTS.get(product)
        if not product_prices or price_type not in product_prices:
            flash("Selecione um produto e um documento válidos.", "danger")
            return redirect(url_for("admin_trades", view=record_type, edit=record_id) if record_id else url_for("admin_trades", view=record_type))

        unit_price = float(product_prices[price_type])
        markup_percent = parse_trade_number(request.form.get("markup_percent"))
        if markup_percent not in {0, 15, 20, 30}:
            flash("Selecione um acréscimo válido: 0%, 15%, 20% ou 30%.", "danger")
            return redirect(url_for("admin_trades", view=record_type, edit=record_id) if record_id else url_for("admin_trades", view=record_type))
        total = unit_price * quantity * (1 + markup_percent / 100.0)
    else:
        # Compra é totalmente livre: produto, documento/tipo, valor unitário,
        # acréscimo e total podem ser informados manualmente.
        document_type = (request.form.get("document_type") or "").strip() or None
        price_type = document_type
        unit_price = parse_trade_number(request.form.get("unit_price"))
        markup_percent = parse_trade_number(request.form.get("markup_percent"))
        total = parse_trade_number(request.form.get("total"))
        if total <= 0 and unit_price > 0 and quantity > 0:
            total = unit_price * quantity * (1 + markup_percent / 100.0)

    seller = (request.form.get("seller") or "").strip() or None
    supplier = (request.form.get("supplier") or "").strip() or None
    contact = (request.form.get("contact") or "").strip() or None
    document_type = document_type or None
    document = (request.form.get("document") or "").strip() or None

    delivery_status = None
    delivery_date = None
    if record_type == "sale":
        delivery_status = (request.form.get("delivery_status") or "delivered").strip().lower()
        if delivery_status not in {"delivered", "scheduled"}:
            delivery_status = "delivered"
        delivery_date = (request.form.get("delivery_date") or "").strip() or None
        if delivery_status == "scheduled" and not delivery_date:
            flash("Informe a data prevista de entrega.", "danger")
            return redirect(url_for("admin_trades", view="sale", edit=record_id) if record_id else url_for("admin_trades", view="sale"))

    if not responsible or not buyer or not product or not record_date or quantity <= 0 or total < 0:
        flash("Preencha os campos obrigatórios corretamente.", "danger")
        return redirect(url_for("admin_trades", view=record_type, edit=record_id) if record_id else url_for("admin_trades", view=record_type))

    if record_type == "sale" and not seller:
        flash("Informe o vendedor.", "danger")
        return redirect(url_for("admin_trades", view="sale", edit=record_id) if record_id else url_for("admin_trades", view="sale"))
    if record_type == "purchase" and not supplier:
        flash("Informe o fornecedor.", "danger")
        return redirect(url_for("admin_trades", view="purchase", edit=record_id) if record_id else url_for("admin_trades", view="purchase"))

    with get_conn() as conn:
        try:
            with conn.cursor() as cur:
                if record_id:
                    cur.execute("""
                        UPDATE trade_records
                        SET record_type=%s, seller=%s, supplier=%s, responsible=%s,
                            buyer=%s, contact=%s, document_type=%s, document=%s,
                            product=%s, price_type=%s, unit_price=%s, markup_percent=%s,
                            quantity=%s, total=%s, record_date=%s,
                            delivery_status=%s, delivery_date=%s, notes=%s,
                            updated_at=NOW()
                        WHERE id=%s
                    """, (
                        record_type, seller, supplier, responsible, buyer,
                        contact, document_type, document, product, price_type, unit_price, markup_percent,
                        quantity, total, record_date, delivery_status, delivery_date,
                        notes, record_id
                    ))
                    if cur.rowcount == 0:
                        conn.rollback()
                        flash("Registro não encontrado.", "danger")
                        return redirect(url_for("admin_trades", view="history"))
                else:
                    cur.execute("""
                        INSERT INTO trade_records(
                            record_type, seller, supplier, responsible, buyer,
                            contact, document_type, document, product, price_type,
                            unit_price, markup_percent, quantity, total, record_date, delivery_status,
                            delivery_date, notes, created_by
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (
                        record_type, seller, supplier, responsible, buyer,
                        contact, document_type, document, product, price_type,
                        unit_price, markup_percent, quantity, total, record_date, delivery_status,
                        delivery_date, notes, admin["id"]
                    ))
            conn.commit()
        except Exception as exc:
            conn.rollback()
            app.logger.exception("Erro ao salvar compra/venda")
            flash(f"Não foi possível salvar o registro ({type(exc).__name__}).", "danger")
            return redirect(url_for("admin_trades", view=record_type))

    flash("Venda salva com sucesso." if record_type == "sale" else "Compra salva com sucesso.", "success")
    return redirect(url_for("admin_trades", view="history"))


@app.post("/admin/compras-vendas/<int:record_id>/delete")
@staff_required
def admin_trade_delete(record_id):
    validate_csrf()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM trade_records WHERE id=%s RETURNING record_type", (record_id,))
            deleted = cur.fetchone()
        conn.commit()
    flash("Registro excluído." if deleted else "Registro já não existia.", "success")
    return redirect(request.referrer or url_for("admin_trades", view="history"))


@app.post("/admin/compras-vendas/<int:record_id>/delivered")
@staff_required
def admin_trade_mark_delivered(record_id):
    validate_csrf()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE trade_records
                SET delivery_status='delivered', delivery_date=NULL, updated_at=NOW()
                WHERE id=%s AND record_type='sale'
            """, (record_id,))
        conn.commit()
    flash("Venda marcada como entregue.", "success")
    return redirect(request.referrer or url_for("admin_trades", view="overview"))


@app.route("/admin/calculadora")
@staff_required
def admin_calculator():
    return render_template("admin_calculator.html")


@app.route("/admin/calculadora/app")
@staff_required
def admin_calculator_app():
    return render_template("admin_calculator_app.html")

@app.after_request
def disable_dynamic_page_cache(response):
    """Evita que dashboards dinâmicos voltem do cache do navegador.

    Isso é especialmente importante depois que uma entrega é aprovada ou
    recusada, pois o percentual precisa refletir o banco imediatamente.
    Arquivos estáticos continuam livres para o cache otimizado do PWA.
    """
    if request.endpoint != "static" and request.path not in {"/service-worker.js", "/manifest.webmanifest"}:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.get("/manifest.webmanifest")
def web_manifest():
    return send_file(
        os.path.join(app.static_folder, "manifest.webmanifest"),
        mimetype="application/manifest+json",
        max_age=0,
    )


@app.get("/service-worker.js")
def service_worker():
    response = send_file(
        os.path.join(app.static_folder, "service-worker.js"),
        mimetype="application/javascript",
        max_age=0,
    )
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


@app.errorhandler(413)
def too_large(_):
    flash("Arquivo muito grande. Use uma imagem menor que 3,5 MB.", "danger")
    return redirect(request.referrer or url_for("dashboard"))
