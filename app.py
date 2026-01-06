from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "expense_secret_key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "expenses.db")

# ---------- DB CONNECTION ----------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- CREATE TABLES ----------
def init_db():
    conn = get_db_connection()

    # USERS TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # EXPENSES TABLE (LINKED TO USER)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            error = "Username already exists"

    return render_template("register.html", error=error)

# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            # 🔐 store user info in session
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("home"))
        else:
            error = "Invalid username or password"

    return render_template("login.html", error=error)

# ---------- HOME / DASHBOARD ----------
@app.route("/", methods=["GET", "POST"])
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    # ADD EXPENSE (for logged-in user only)
    if request.method == "POST":
        conn.execute(
            """
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                request.form["amount"],
                request.form["category"],
                request.form["date"],
                request.form["description"]
            )
        )
        conn.commit()

    # FETCH ONLY LOGGED-IN USER EXPENSES
    expenses = conn.execute(
        "SELECT * FROM expenses WHERE user_id=?",
        (user_id,)
    ).fetchall()

    total = sum(exp["amount"] for exp in expenses)

    # CHART DATA (USER-SPECIFIC)
    chart_rows = conn.execute(
        """
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE user_id=?
        GROUP BY category
        """,
        (user_id,)
    ).fetchall()

    conn.close()

    categories = [row["category"] for row in chart_rows]
    amounts = [row["total"] for row in chart_rows]

    return render_template(
        "index.html",
        expenses=expenses,
        total=total,
        categories=categories,
        amounts=amounts
    )

# ---------- EDIT EXPENSE ----------
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    # Fetch expense ONLY if it belongs to logged-in user
    expense = conn.execute(
        "SELECT * FROM expenses WHERE id=? AND user_id=?",
        (id, user_id)
    ).fetchone()

    if expense is None:
        conn.close()
        return redirect(url_for("home"))

    if request.method == "POST":
        conn.execute(
            """
            UPDATE expenses
            SET amount=?, category=?, date=?, description=?
            WHERE id=? AND user_id=?
            """,
            (
                request.form["amount"],
                request.form["category"],
                request.form["date"],
                request.form["description"],
                id,
                user_id
            )
        )
        conn.commit()
        conn.close()
        return redirect(url_for("home"))

    conn.close()
    return render_template("edit.html", expense=expense)

# ---------- DELETE EXPENSE ----------
@app.route("/delete/<int:id>")
def delete(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    # Delete ONLY if expense belongs to logged-in user
    conn.execute(
        "DELETE FROM expenses WHERE id=? AND user_id=?",
        (id, user_id)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("home"))


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
