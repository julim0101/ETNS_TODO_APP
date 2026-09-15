"""ETNS 할일관리 앱 (Flask + SQLite/Supabase Postgres)."""

import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import (
    Flask, flash, g, redirect, render_template, request, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# DATABASE_URL 이 설정돼 있으면 Supabase(Postgres) 를 쓰고,
# 없으면 로컬 개발 편의를 위해 SQLite 로 동작한다.
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg
    from psycopg.rows import dict_row
else:
    # Vercel 등 서버리스 환경은 파일시스템이 읽기 전용이라 /tmp 만 쓸 수 있다.
    ON_SERVERLESS = bool(os.environ.get("VERCEL"))
    DB_PATH = os.environ.get("TODO_DB_PATH") or os.path.join(
        tempfile.gettempdir() if ON_SERVERLESS else BASE_DIR, "todo.db"
    )

# 배포 환경(Vercel)은 UTC 로 동작하므로 표시/비교는 항상 KST 기준으로 한다.
KST = timezone(timedelta(hours=9))

PRIORITIES = ("high", "normal", "low")
FILTERS = ("all", "active", "done")
MIN_PASSWORD_LEN = 6

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "etns-todo-dev-key")


# --- DB ---------------------------------------------------------------------

def q(sql):
    """SQLite 는 '?', Postgres 는 '%s' 를 파라미터 자리표시자로 쓴다."""
    return sql.replace("?", "%s") if USE_POSTGRES else sql


def get_db():
    if "db" not in g:
        if USE_POSTGRES:
            # pgbouncer(transaction pooling) 환경에서 서버측 prepared statement 를
            # 재사용하면 오류가 나므로 비활성화한다.
            g.db = psycopg.connect(
                DATABASE_URL, row_factory=dict_row, prepare_threshold=None
            )
        else:
            g.db = sqlite3.connect(DB_PATH)
            g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    if USE_POSTGRES:
        conn = psycopg.connect(DATABASE_URL)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            SERIAL  PRIMARY KEY,
                username      TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id         SERIAL  PRIMARY KEY,
                title      TEXT    NOT NULL,
                memo       TEXT    NOT NULL DEFAULT '',
                priority   TEXT    NOT NULL DEFAULT 'normal',
                due_date   TEXT,
                done       INTEGER NOT NULL DEFAULT 0,
                created_at TEXT    NOT NULL,
                updated_at TEXT    NOT NULL,
                user_id    INTEGER REFERENCES users(id)
            );
            """
        )
        # 로그인 기능 추가 이전에 만들어진 배포본에도 user_id 컬럼을 보강한다.
        conn.execute(
            "ALTER TABLE todos ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);"
        )
        conn.commit()
        conn.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS todos (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT    NOT NULL,
                memo       TEXT    NOT NULL DEFAULT '',
                priority   TEXT    NOT NULL DEFAULT 'normal',
                due_date   TEXT,
                done       INTEGER NOT NULL DEFAULT 0,
                created_at TEXT    NOT NULL,
                updated_at TEXT    NOT NULL
            );
            """
        )
        # SQLite 는 ADD COLUMN IF NOT EXISTS 를 지원하지 않으므로 직접 확인한다.
        cols = [r[1] for r in conn.execute("PRAGMA table_info(todos)").fetchall()]
        if "user_id" not in cols:
            conn.execute("ALTER TABLE todos ADD COLUMN user_id INTEGER REFERENCES users(id);")
        conn.commit()
        conn.close()


def now():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")


def today():
    return datetime.now(KST).strftime("%Y-%m-%d")


# --- 로그인 -------------------------------------------------------------------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_user():
    return {"current_username": session.get("username")}


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not username or not password:
            flash("아이디와 비밀번호를 모두 입력해 주세요.", "error")
        elif len(password) < MIN_PASSWORD_LEN:
            flash(f"비밀번호는 {MIN_PASSWORD_LEN}자 이상이어야 합니다.", "error")
        elif password != confirm:
            flash("비밀번호 확인이 일치하지 않습니다.", "error")
        else:
            db = get_db()
            exists = db.execute(
                q("SELECT id FROM users WHERE username = ?"), (username,)
            ).fetchone()
            if exists:
                flash("이미 사용 중인 아이디입니다.", "error")
            else:
                db.execute(
                    q("INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)"),
                    (username, generate_password_hash(password), now()),
                )
                db.commit()
                flash("회원가입이 완료됐습니다. 로그인해 주세요.", "success")
                return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            q("SELECT id, username, password_hash FROM users WHERE username = ?"),
            (username,),
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("아이디 또는 비밀번호가 올바르지 않습니다.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(request.args.get("next") or url_for("index"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("로그아웃했습니다.", "success")
    return redirect(url_for("login"))


# --- 화면 -------------------------------------------------------------------

@app.route("/")
@login_required
def index():
    view = request.args.get("view", "all")
    if view not in FILTERS:
        view = "all"
    keyword = request.args.get("q", "").strip()

    sql = "SELECT * FROM todos WHERE user_id = ?"
    params = [session["user_id"]]
    if view == "active":
        sql += " AND done = 0"
    elif view == "done":
        sql += " AND done = 1"
    if keyword:
        sql += " AND (title LIKE ? OR memo LIKE ?)"
        params += [f"%{keyword}%", f"%{keyword}%"]
    sql += """
        ORDER BY done ASC,
                 CASE priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END,
                 (due_date IS NULL), due_date,
                 id DESC
    """

    db = get_db()
    todos = db.execute(q(sql), params).fetchall()
    counts = db.execute(
        q(
            "SELECT COUNT(*) AS total,"
            " SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END) AS done"
            " FROM todos WHERE user_id = ?"
        ),
        (session["user_id"],),
    ).fetchone()
    total = counts["total"] or 0
    done = counts["done"] or 0

    return render_template(
        "index.html",
        todos=todos,
        view=view,
        keyword=keyword,
        total=total,
        done=done,
        active=total - done,
        today=today(),
    )


@app.route("/add", methods=["POST"])
@login_required
def add():
    title = request.form.get("title", "").strip()
    if not title:
        flash("할 일 제목을 입력해 주세요.", "error")
        return redirect(url_for("index"))

    memo = request.form.get("memo", "").strip()
    priority = request.form.get("priority", "normal")
    if priority not in PRIORITIES:
        priority = "normal"
    due_date = request.form.get("due_date", "").strip() or None

    db = get_db()
    db.execute(
        q(
            "INSERT INTO todos (title, memo, priority, due_date, done, created_at, updated_at, user_id)"
            " VALUES (?, ?, ?, ?, 0, ?, ?, ?)"
        ),
        (title, memo, priority, due_date, now(), now(), session["user_id"]),
    )
    db.commit()
    flash("할 일을 추가했습니다.", "success")
    return redirect(url_for("index", view=request.form.get("view", "all")))


@app.route("/toggle/<int:todo_id>", methods=["POST"])
@login_required
def toggle(todo_id):
    db = get_db()
    row = db.execute(
        q("SELECT done FROM todos WHERE id = ? AND user_id = ?"),
        (todo_id, session["user_id"]),
    ).fetchone()
    if row is None:
        flash("해당 할 일을 찾을 수 없습니다.", "error")
        return redirect(url_for("index"))
    db.execute(
        q("UPDATE todos SET done = ?, updated_at = ? WHERE id = ? AND user_id = ?"),
        (0 if row["done"] else 1, now(), todo_id, session["user_id"]),
    )
    db.commit()
    return redirect(url_for("index", view=request.form.get("view", "all"),
                            q=request.form.get("q", "")))


@app.route("/edit/<int:todo_id>", methods=["GET", "POST"])
@login_required
def edit(todo_id):
    db = get_db()
    todo = db.execute(
        q("SELECT * FROM todos WHERE id = ? AND user_id = ?"),
        (todo_id, session["user_id"]),
    ).fetchone()
    if todo is None:
        flash("해당 할 일을 찾을 수 없습니다.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("할 일 제목을 입력해 주세요.", "error")
            return redirect(url_for("edit", todo_id=todo_id))

        priority = request.form.get("priority", "normal")
        if priority not in PRIORITIES:
            priority = "normal"

        db.execute(
            q(
                "UPDATE todos SET title = ?, memo = ?, priority = ?, due_date = ?,"
                " done = ?, updated_at = ? WHERE id = ? AND user_id = ?"
            ),
            (
                title,
                request.form.get("memo", "").strip(),
                priority,
                request.form.get("due_date", "").strip() or None,
                1 if request.form.get("done") else 0,
                now(),
                todo_id,
                session["user_id"],
            ),
        )
        db.commit()
        flash("할 일을 수정했습니다.", "success")
        return redirect(url_for("index"))

    return render_template("edit.html", todo=todo)


@app.route("/delete/<int:todo_id>", methods=["POST"])
@login_required
def delete(todo_id):
    db = get_db()
    db.execute(
        q("DELETE FROM todos WHERE id = ? AND user_id = ?"),
        (todo_id, session["user_id"]),
    )
    db.commit()
    flash("할 일을 삭제했습니다.", "success")
    return redirect(url_for("index", view=request.form.get("view", "all")))


@app.route("/clear-done", methods=["POST"])
@login_required
def clear_done():
    db = get_db()
    cur = db.execute(
        q("DELETE FROM todos WHERE done = 1 AND user_id = ?"), (session["user_id"],)
    )
    db.commit()
    flash(f"완료된 할 일 {cur.rowcount}건을 정리했습니다.", "success")
    return redirect(url_for("index"))


# 서버리스에서는 __main__ 이 실행되지 않으므로 import 시점에 스키마를 보장한다.
init_db()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
