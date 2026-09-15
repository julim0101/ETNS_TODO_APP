"""ETNS 할일관리 앱 (Flask + SQLite)."""

import os
import sqlite3
import tempfile
from datetime import datetime

from flask import Flask, flash, g, redirect, render_template, request, url_for

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Vercel 등 서버리스 환경은 파일시스템이 읽기 전용이라 /tmp 만 쓸 수 있다.
# (서버리스에서는 인스턴스가 재활용될 때 데이터가 사라진다. README 참고)
ON_SERVERLESS = bool(os.environ.get("VERCEL"))
DB_PATH = os.environ.get("TODO_DB_PATH") or os.path.join(
    tempfile.gettempdir() if ON_SERVERLESS else BASE_DIR, "todo.db"
)

PRIORITIES = ("high", "normal", "low")
FILTERS = ("all", "active", "done")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "etns-todo-dev-key")


# --- DB ---------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
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
    db.commit()
    db.close()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# --- 화면 -------------------------------------------------------------------

@app.route("/")
def index():
    view = request.args.get("view", "all")
    if view not in FILTERS:
        view = "all"
    keyword = request.args.get("q", "").strip()

    sql = "SELECT * FROM todos WHERE 1=1"
    params = []
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
    todos = db.execute(sql, params).fetchall()
    counts = db.execute(
        "SELECT COUNT(*) AS total,"
        " SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END) AS done"
        " FROM todos"
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
        today=datetime.now().strftime("%Y-%m-%d"),
    )


@app.route("/add", methods=["POST"])
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
        "INSERT INTO todos (title, memo, priority, due_date, done, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, 0, ?, ?)",
        (title, memo, priority, due_date, now(), now()),
    )
    db.commit()
    flash("할 일을 추가했습니다.", "success")
    return redirect(url_for("index", view=request.form.get("view", "all")))


@app.route("/toggle/<int:todo_id>", methods=["POST"])
def toggle(todo_id):
    db = get_db()
    row = db.execute("SELECT done FROM todos WHERE id = ?", (todo_id,)).fetchone()
    if row is None:
        flash("해당 할 일을 찾을 수 없습니다.", "error")
        return redirect(url_for("index"))
    db.execute(
        "UPDATE todos SET done = ?, updated_at = ? WHERE id = ?",
        (0 if row["done"] else 1, now(), todo_id),
    )
    db.commit()
    return redirect(url_for("index", view=request.form.get("view", "all"),
                            q=request.form.get("q", "")))


@app.route("/edit/<int:todo_id>", methods=["GET", "POST"])
def edit(todo_id):
    db = get_db()
    todo = db.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
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
            "UPDATE todos SET title = ?, memo = ?, priority = ?, due_date = ?,"
            " done = ?, updated_at = ? WHERE id = ?",
            (
                title,
                request.form.get("memo", "").strip(),
                priority,
                request.form.get("due_date", "").strip() or None,
                1 if request.form.get("done") else 0,
                now(),
                todo_id,
            ),
        )
        db.commit()
        flash("할 일을 수정했습니다.", "success")
        return redirect(url_for("index"))

    return render_template("edit.html", todo=todo)


@app.route("/delete/<int:todo_id>", methods=["POST"])
def delete(todo_id):
    db = get_db()
    db.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    db.commit()
    flash("할 일을 삭제했습니다.", "success")
    return redirect(url_for("index", view=request.form.get("view", "all")))


@app.route("/clear-done", methods=["POST"])
def clear_done():
    db = get_db()
    cur = db.execute("DELETE FROM todos WHERE done = 1")
    db.commit()
    flash(f"완료된 할 일 {cur.rowcount}건을 정리했습니다.", "success")
    return redirect(url_for("index"))


# 서버리스에서는 __main__ 이 실행되지 않으므로 import 시점에 스키마를 보장한다.
init_db()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
