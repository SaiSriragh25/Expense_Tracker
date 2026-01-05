from flask import Flask, render_template, request, redirect, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "expense_secret_key"

def get_db_connection():
    conn = sqlite3.connect("expenses.db")
    conn.row_factory = sqlite3.Row
    return conn


# Create table once
conn = get_db_connection()
conn.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount INTEGER,
    category TEXT,
    date TEXT,
    description TEXT
)
""")
conn.close()


@app.route("/", methods=["GET", "POST"])
def home():
    conn = get_db_connection()
    error = None

    # Add expense
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

    # Chart data (group by category)
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


@app.route("/delete/<int:id>")
def delete(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM expenses WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Expense deleted 🗑")
    return redirect("/")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    conn = get_db_connection()
    expense = conn.execute(
        "SELECT * FROM expenses WHERE id=?", (id,)
    ).fetchone()

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
        return redirect("/")

    conn.close()
    return render_template("edit.html", expense=expense)


if __name__ == "__main__":
    app.run(debug=True)
