from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "college_discovery_secret"


import os
import mysql.connector

def get_db():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        port=int(os.environ.get("DB_PORT", 3306)),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME")
    )
@app.route("/")
def home():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM colleges ORDER BY rating DESC LIMIT 6"
    )
    colleges = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("index.html", colleges=colleges)


@app.route("/colleges")
def colleges():
    search = request.args.get("search", "")
    city = request.args.get("city", "")
    course = request.args.get("course", "")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM colleges WHERE 1=1"
    values = []

    if search:
        query += " AND (name LIKE %s OR city LIKE %s)"
        search_value = "%" + search + "%"
        values.extend([search_value, search_value])

    if city:
        query += " AND city = %s"
        values.append(city)

    if course:
        query += " AND course = %s"
        values.append(course)

    query += " ORDER BY rating DESC"

    cursor.execute(query, values)
    result = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "colleges.html",
        colleges=result,
        search=search,
        city=city,
        course=course
    )


@app.route("/college/<int:college_id>")
def college_details(college_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM colleges WHERE id = %s",
        (college_id,)
    )

    college = cursor.fetchone()

    cursor.close()
    conn.close()

    if college is None:
        return "College not found"

    return render_template("colleges.html", college=college)


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                (name, email, hashed_password)
            )

            conn.commit()

            cursor.close()
            conn.close()

            return redirect(url_for("login"))

        except mysql.connector.IntegrityError:

            cursor.close()
            conn.close()

            return "Email already registered"

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect(url_for("home"))

        return "Wrong email or password"

    return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


@app.route("/favorite/<int:college_id>")
def favorite(college_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM favorites WHERE user_id = %s AND college_id = %s",
        (user_id, college_id)
    )

    existing = cursor.fetchone()

    if existing:

        cursor.execute(
            "DELETE FROM favorites WHERE user_id = %s AND college_id = %s",
            (user_id, college_id)
        )

    else:

        cursor.execute(
            "INSERT INTO favorites (user_id, college_id) VALUES (%s, %s)",
            (user_id, college_id)
        )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(request.referrer or url_for("home"))


@app.route("/favorites")
def favorites():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT colleges.*
        FROM colleges
        JOIN favorites
        ON colleges.id = favorites.college_id
        WHERE favorites.user_id = %s
    """, (session["user_id"],))

    colleges = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("favorites.html", colleges=colleges)


@app.route("/compare")
def compare():

    ids = request.args.get("ids", "")

    if not ids:
        return render_template("compare.html", colleges=[])

    id_list = ids.split(",")

    placeholders = ",".join(["%s"] * len(id_list))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    query = f"""
        SELECT *
        FROM colleges
        WHERE id IN ({placeholders})
    """

    cursor.execute(query, id_list)

    colleges = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("compare.html", colleges=colleges)


if __name__ == "__main__":
    app.run(debug=True)