from flask import Flask, render_template_string, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

DB = "cmms.db"

# ---------------- DATABASE ----------------

def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS machines(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        model TEXT,
        controller TEXT,
        location TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS failures(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id INTEGER,
        failure_date TEXT,
        description TEXT,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- HTML ----------------

base = """
<!DOCTYPE html>
<html dir="rtl">
<head>
<meta charset="utf-8">
<title>CMMS CNC</title>

<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">

<style>

body{
background:#f5f7fa;
font-family:tahoma;
}

.navbar{
background:#0d6efd;
}

.card{
box-shadow:0 2px 10px rgba(0,0,0,.1);
border:none;
}

</style>

</head>

<body>

<nav class="navbar navbar-dark">
<div class="container">

<a class="navbar-brand" href="/">
CMMS CNC
</a>

<div>
<a class="btn btn-light btn-sm" href="/machines">
دستگاه ها
</a>

<a class="btn btn-warning btn-sm" href="/failure/add">
ثبت خرابی
</a>

</div>

</div>
</nav>

<div class="container mt-4">

{{content|safe}}

</div>

</body>
</html>
"""

# ---------------- DASHBOARD ----------------

@app.route("/")
def dashboard():

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM machines")
    machines = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM failures")
    failures = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM failures WHERE status='باز'")
    open_failures = cur.fetchone()[0]

    conn.close()

    content = f"""
    <div class="row">

        <div class="col-md-4">
            <div class="card p-3">
                <h4>تعداد دستگاه ها</h4>
                <h1>{machines}</h1>
            </div>
        </div>

        <div class="col-md-4">
            <div class="card p-3">
                <h4>کل خرابی ها</h4>
                <h1>{failures}</h1>
            </div>
        </div>

        <div class="col-md-4">
            <div class="card p-3">
                <h4>خرابی باز</h4>
                <h1>{open_failures}</h1>
            </div>
        </div>

    </div>
    """

    return render_template_string(base, content=content)

# ---------------- MACHINES ----------------

@app.route("/machines")
def machines():

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT * FROM machines")
    rows = cur.fetchall()

    conn.close()

    table = """
    <h3>لیست دستگاه ها</h3>

    <a href="/machine/add" class="btn btn-success mb-3">
    افزودن دستگاه
    </a>

    <table class="table table-bordered bg-white">

    <tr>
        <th>ID</th>
        <th>نام</th>
        <th>مدل</th>
        <th>کنترلر</th>
        <th>محل نصب</th>
    </tr>
    """

    for r in rows:
        table += f"""
        <tr>
            <td>{r[0]}</td>
            <td>{r[1]}</td>
            <td>{r[2]}</td>
            <td>{r[3]}</td>
            <td>{r[4]}</td>
        </tr>
        """

    table += "</table>"

    return render_template_string(base, content=table)

# ---------------- ADD MACHINE ----------------

@app.route("/machine/add", methods=["GET","POST"])
def add_machine():

    if request.method == "POST":

        name = request.form["name"]
        model = request.form["model"]
        controller = request.form["controller"]
        location = request.form["location"]

        conn = sqlite3.connect(DB)
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO machines(name,model,controller,location)
        VALUES(?,?,?,?)
        """,(name,model,controller,location))

        conn.commit()
        conn.close()

        return redirect("/machines")

    content = """
    <h3>ثبت دستگاه</h3>

    <form method="post">

    <input class="form-control mb-2" name="name" placeholder="نام دستگاه">

    <input class="form-control mb-2" name="model" placeholder="مدل">

    <input class="form-control mb-2" name="controller" placeholder="FANUC">

    <input class="form-control mb-2" name="location" placeholder="کارگاه">

    <button class="btn btn-primary">
    ذخیره
    </button>

    </form>
    """

    return render_template_string(base, content=content)

# ---------------- ADD FAILURE ----------------

@app.route("/failure/add", methods=["GET","POST"])
def add_failure():

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT id,name FROM machines")
    machines = cur.fetchall()

    if request.method == "POST":

        machine_id = request.form["machine_id"]
        description = request.form["description"]

        cur.execute("""
        INSERT INTO failures(
        machine_id,
        failure_date,
        description,
        status
        )
        VALUES(?,?,?,?)
        """,(
            machine_id,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            description,
            "باز"
        ))

        conn.commit()
        conn.close()

        return redirect("/")

    options = ""

    for m in machines:
        options += f"<option value='{m[0]}'>{m[1]}</option>"

    content = f"""
    <h3>ثبت خرابی</h3>

    <form method="post">

    <select name="machine_id" class="form-control mb-2">
    {options}
    </select>

    <textarea
    class="form-control mb-2"
    name="description"
    placeholder="شرح خرابی">
    </textarea>

    <button class="btn btn-danger">
    ثبت خرابی
    </button>

    </form>
    """

    return render_template_string(base, content=content)

# ---------------- FAILURES ----------------

@app.route("/failures")
def failures():

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
    SELECT
    failures.id,
    machines.name,
    failures.failure_date,
    failures.description,
    failures.status
    FROM failures
    LEFT JOIN machines
    ON machines.id = failures.machine_id
    ORDER BY failures.id DESC
    """)

    rows = cur.fetchall()

    conn.close()

    html = """
    <h3>خرابی ها</h3>

    <table class='table table-bordered bg-white'>

    <tr>
        <th>کد</th>
        <th>دستگاه</th>
        <th>تاریخ</th>
        <th>شرح</th>
        <th>وضعیت</th>
    </tr>
    """

    for r in rows:
        html += f"""
        <tr>
            <td>{r[0]}</td>
            <td>{r[1]}</td>
            <td>{r[2]}</td>
            <td>{r[3]}</td>
            <td>{r[4]}</td>
        </tr>
        """

    html += "</table>"

    return render_template_string(base, content=html)

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
