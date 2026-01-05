from flask import Flask, render_template, request, redirect, url_for, flash
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount INTEGER NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------------- HOME ----------------
@app.route("/", methods=["GET", "POST"])
def home():
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
    conn = get_db_connection()
    conn.execute("DELETE FROM expenses WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Expense deleted 🗑")
    return redirect(url_for("home"))

# ---------------- EDIT ----------------
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
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

# ---------------- RUN ----------------
# if __name__ == "__main__":
    # app.run(debug=True)
