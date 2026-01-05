from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "expense_secret_key"

# ---------------- DB CONNECTION ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "expenses.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- CREATE TABLE ----------------
def init_db():
    conn = get_db_connection()

    # Expenses table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount INTEGER NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT
        )
    """)

    # Users table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # ✅ Ensure default user ALWAYS exists
    user = conn.execute(
        "SELECT * FROM users WHERE username='admin'"
    ).fetchone()

    if not user:
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("admin", "admin123")
        )

    conn.commit()
    conn.close()

init_db()

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not username or not password:
            error = "All fields are required"
        elif password != confirm_password:
            error = "Passwords do not match"
        else:
            try:
                conn = get_db_connection()
                conn.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username.strip(), password)
                )
                conn.commit()
                conn.close()
                flash("Account created successfully 🎉 Please login")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "Username already exists"

    return render_template("register.html", error=error)

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            error = "Please enter username and password"
        else:
            conn = get_db_connection()
            user = conn.execute(
                "SELECT * FROM users WHERE username=? AND password=?",
                (username.strip(), password)
            ).fetchone()
            conn.close()

            if user:
                session["user"] = username
                return redirect(url_for("home"))
            else:
                error = "Invalid username or password"

    return render_template("login.html", error=error)

# ---------------- HOME (PROTECTED) ----------------
@app.route("/", methods=["GET", "POST"])
def home():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    error = None

    if request.method == "POST":
        amount = request.form.get("amount")
        category = request.form.get("category")
        date = request.form.get("date")
        description = request.form.get("description")

        if not amount or not category or not date:
            error = "Amount, Category and Date are required."
        elif int(amount) <= 0:
            error = "Amount must be greater than zero."
        else:
            conn.execute(
                "INSERT INTO expenses (amount, category, date, description) VALUES (?, ?, ?, ?)",
                (amount, category, date, description)
            )
            conn.commit()
            flash("Expense added successfully ✅")

    expenses = conn.execute("SELECT * FROM expenses").fetchall()
    total = sum(exp["amount"] for exp in expenses)

    chart_rows = conn.execute("""
        SELECT category, SUM(amount) as total
        FROM expenses
        GROUP BY category
    """).fetchall()

    categories = [row["category"] for row in chart_rows]
    amounts = [row["total"] for row in chart_rows]

    conn.close()

    return render_template(
        "index.html",
        expenses=expenses,
        total=total,
        error=error,
        categories=categories,
        amounts=amounts
    )

# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
def delete(id):
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    conn.execute("DELETE FROM expenses WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Expense deleted 🗑")
    return redirect(url_for("home"))

# ---------------- EDIT ----------------
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    expense = conn.execute(
        "SELECT * FROM expenses WHERE id=?", (id,)
    ).fetchone()

    if expense is None:
        conn.close()
        return redirect(url_for("home"))

    if request.method == "POST":
        conn.execute("""
            UPDATE expenses
            SET amount=?, category=?, date=?, description=?
            WHERE id=?
        """, (
            request.form["amount"],
            request.form["category"],
            request.form["date"],
            request.form["description"],
            id
        ))
        conn.commit()
        conn.close()
        flash("Expense updated ✏️")
        return redirect(url_for("home"))

    conn.close()
    return render_template("edit.html", expense=expense)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)
