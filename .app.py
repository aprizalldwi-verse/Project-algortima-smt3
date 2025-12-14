from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import json, os, re
from typing import List

app = Flask(__name__)
app.secret_key = "super-secret-change-this"

DATA_FILE = "mahasiswa.json"
USERS_FILE = "users.json"

# ---------- Data model ----------
JURUSAN_LIST = [
    "Teknik Informatika",
    "Manajemen",
    "Hukum",
    "Sastra Inggris",
    "PJOK",
    "PGSD",
    "Ilmu Komunikasi"
]

class ValidationError(Exception):
    pass

class Mahasiswa:
    def __init__(self, nim, nama, kelas, ipk, jurusan):
        self.nim = str(nim)
        self.nama = nama
        self.kelas = kelas
        self.ipk = float(ipk)
        self.jurusan = jurusan

    def to_dict(self):
        return {
            "nim": self.nim,
            "nama": self.nama,
            "kelas": self.kelas,
            "ipk": self.ipk,
            "jurusan": self.jurusan
        }

# ---------- Validation ----------
def validate_input(nim, nama, kelas, ipk, jurusan):
    if not re.match(r'^\d{12}$', nim):
        raise ValidationError("NIM harus 12 digit angka")
    if not re.match(r'^[A-Za-z ]+$', nama):
        raise ValidationError("Nama hanya huruf dan spasi")
    if not re.match(r'^[A-Za-z0-9]+$', kelas):
        raise ValidationError("Kelas hanya huruf & angka")
    ipk = float(ipk)
    if not (0 <= ipk <= 4):
        raise ValidationError("IPK harus 0 - 4")
    if jurusan not in JURUSAN_LIST:
        raise ValidationError("Jurusan tidak valid")

# ---------- Load & Save ----------
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        raw = json.load(f)
        return [Mahasiswa(**m) for m in raw]

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump([m.to_dict() for m in data], f, indent=4)

# ---------- Default admin ----------
users = load_users()
if "admin" not in users:
    users["admin"] = generate_password_hash("12345")
    save_users(users)

# ---------- Login Required ----------
def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

# ================= HOME =================
@app.route("/")
def home():
    return render_template("home.html")

# ================= LOGIN =================
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        users = load_users()
        if u in users and check_password_hash(users[u], p):
            session["user"] = u
            return redirect(url_for("index"))
        flash("Login gagal", "error")
    return render_template("login.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        users = load_users()
        if u in users:
            flash("Username sudah ada")
        else:
            users[u] = generate_password_hash(p)
            save_users(users)
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ================= INDEX =================
@app.route("/index")
@login_required
def index():
    data = load_data()
    return render_template("index.html", data=data, jurusan_list=JURUSAN_LIST)

# ================= MAHASISWA =================
@app.route("/mahasiswa")
@login_required
def mahasiswa_page():
    return render_template("mahasiswa.html", data=load_data())

@app.route("/tambah", methods=["GET","POST"])
@login_required
def tambah():
    if request.method == "POST":
        nim = request.form["nim"]
        nama = request.form["nama"]
        kelas = request.form["kelas"]
        ipk = request.form["ipk"]
        jurusan = request.form["jurusan"]

        validate_input(nim, nama, kelas, ipk, jurusan)

        data = load_data()
        # Cek NIM duplikat
        if any(m.nim == nim for m in data):
            flash("NIM sudah ada", "error")
            return redirect(url_for("tambah"))

        data.append(Mahasiswa(nim, nama, kelas, ipk, jurusan))
        save_data(data)
        return redirect(url_for("index"))

    return render_template("tambah.html", jurusan_list=JURUSAN_LIST)

# ================= EDIT =================
@app.route("/edit/<nim>", methods=["GET","POST"])
@login_required
def edit(nim):
    data = load_data()
    mhs = next((m for m in data if m.nim == nim), None)
    if not mhs:
        flash("Mahasiswa tidak ditemukan", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        nama = request.form["nama"]
        kelas = request.form["kelas"]
        ipk = request.form["ipk"]
        jurusan = request.form["jurusan"]

        validate_input(nim, nama, kelas, ipk, jurusan)

        # Update data
        mhs.nama = nama
        mhs.kelas = kelas
        mhs.ipk = float(ipk)
        mhs.jurusan = jurusan
        save_data(data)
        return redirect(url_for("index"))

    return render_template("edit.html", mhs=mhs, jurusan_list=JURUSAN_LIST)

# ================= DELETE =================
@app.route("/hapus/<nim>")
@login_required
def hapus(nim):
    data = load_data()
    data = [m for m in data if m.nim != nim]
    save_data(data)
    flash("Data berhasil dihapus", "success")
    return redirect(url_for("index"))

# ================= DASHBOARD =================
@app.route("/dashboard")
@login_required
def dashboard():
    data = load_data()
    total = len(data)
    avg_ipk = round(sum(m.ipk for m in data) / total, 2) if total else 0
    per_jurusan = {j: len([m for m in data if m.jurusan == j]) for j in JURUSAN_LIST}

    return render_template("dashboard.html",
        total=total,
        avg_ipk=avg_ipk,
        per_jurusan=per_jurusan
    )

# ================= RUN =================
if __name__ == "__main__":
    if not os.path.exists(DATA_FILE):
        save_data([])
    app.run(debug=True)
