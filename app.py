from flask import Flask, render_template_string, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import tempfile

app = Flask(__name__)
app.secret_key = 'my-secret-key-12345'

# ============ استفاده از دیتابیس موقت در Render ============
# این کار باعث میشه دیتابیس توی مسیری که دسترسی داره ساخته بشه
db_path = os.path.join(tempfile.gettempdir(), 'industrial.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ============ مدل دستگاه ============
class Machine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(200), nullable=False)
    model = db.Column(db.String(100))
    brand = db.Column(db.String(100))
    location = db.Column(db.String(200))
    status = db.Column(db.String(50), default='فعال')
    next_service = db.Column(db.String(50))

# ============ ایجاد دیتابیس و داده‌های اولیه ============
with app.app_context():
    db.create_all()
    if not Machine.query.first():
        m1 = Machine(code='M-001', name='کولر گازی', model='XZ-2000', brand='گالی', location='تهران', status='فعال', next_service='۱۴۰۳-۰۴-۲۵')
        m2 = Machine(code='M-002', name='ژنراتور', model='G-500', brand='کاترپیلار', location='تهران', status='تعمیر', next_service='۱۴۰۳-۰۴-۱۰')
        m3 = Machine(code='M-003', name='پمپ آب', model='P-100', brand='پنتاکس', location='تهران', status='تعمیر', next_service='۱۴۰۳-۰۵-۲۰')
        db.session.add_all([m1, m2, m3])
        db.session.commit()

# ============ HTML قالب‌ها ============
BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سیستم تعمیرات</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    <style>
        * { direction: rtl; text-align: right; }
        body { background: #f0f2f5; font-family: Tahoma; padding-bottom: 70px; }
        .navbar { background: #0d1b2a !important; }
        .navbar-brand { color: #fff !important; font-weight: bold; }
        .card { border-radius: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: none; margin-bottom: 15px; }
        .card-header { background: #fff; border-bottom: 1px solid #e9ecef; font-weight: 600; }
        .stat-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px; padding: 20px; color: #fff; margin-bottom: 15px; }
        .stat-card .stat-number { font-size: 2.5rem; font-weight: 700; }
        .stat-card .stat-label { font-size: 0.9rem; opacity: 0.9; }
        .stat-card.stat-green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
        .stat-card.stat-orange { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .stat-card.stat-red { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
        .status-badge { padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 500; }
        .status-active { background: #d4edda; color: #155724; }
        .status-maintenance { background: #fff3cd; color: #856404; }
        .status-inactive { background: #f8d7da; color: #721c24; }
        .mobile-menu { background: #0d1b2a; padding: 10px; position: fixed; bottom: 0; left: 0; right: 0; z-index: 999; display: flex; justify-content: space-around; }
        .mobile-menu a { color: #a0b4c8; text-decoration: none; font-size: 12px; text-align: center; }
        .mobile-menu a.active { color: #fff; }
        .mobile-menu i { font-size: 22px; display: block; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="/">🔧 سیستم تعمیرات</a>
        </div>
    </nav>
    <div class="container" style="padding-top: 15px;">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, msg in messages %}
                    <div class="alert alert-{{ category }}">{{ msg }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
    <div class="mobile-menu">
        <a href="/" class="active"><i class="bi bi-grid-1x2-fill"></i>داشبورد</a>
        <a href="/machines"><i class="bi bi-building"></i>دستگاه‌ها</a>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

DASHBOARD = '''
{% extends base_template %}
{% block content %}
<div class="row">
    <div class="col-6"><div class="stat-card"><div class="stat-number">{{ total }}</div><div class="stat-label">تعداد دستگاه‌ها</div></div></div>
    <div class="col-6"><div class="stat-card stat-green"><div class="stat-number">{{ active }}</div><div class="stat-label">فعال</div></div></div>
    <div class="col-6"><div class="stat-card stat-orange"><div class="stat-number">{{ maintenance }}</div><div class="stat-label">در حال تعمیر</div></div></div>
    <div class="col-6"><div class="stat-card stat-red"><div class="stat-number">{{ inactive }}</div><div class="stat-label">غیرفعال</div></div></div>
</div>
<div class="card">
    <div class="card-header">📋 لیست دستگاه‌ها</div>
    <div class="card-body p-0">
        <table class="table table-hover mb-0">
            <thead class="table-light"><tr><th>نام</th><th>وضعیت</th></tr></thead>
            <tbody>{% for m in machines %}<tr><td>{{ m.name }}</td><td><span class="status-badge status-{{ 'active' if m.status=='فعال' else 'maintenance' if m.status=='تعمیر' else 'inactive' }}">{{ m.status }}</span></td></tr>{% endfor %}</tbody>
        </table>
    </div>
</div>
{% endblock %}
'''

MACHINES_LIST = '''
{% extends base_template %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
    <h5>🏭 دستگاه‌ها</h5>
    <a href="/add-machine" class="btn btn-primary btn-sm">➕ جدید</a>
</div>
{% for m in machines %}
<div class="card">
    <div class="card-body">
        <h6>{{ m.name }}</h6>
        <span class="badge bg-secondary">{{ m.code }}</span>
        <span class="status-badge status-{{ 'active' if m.status=='فعال' else 'maintenance' if m.status=='تعمیر' else 'inactive' }}">{{ m.status }}</span>
        <p class="small mt-2 mb-0">📍 {{ m.location }}</p>
        <p class="small">📅 سرویس بعدی: {{ m.next_service or '-' }}</p>
        <a href="/delete-machine/{{ m.id }}" class="btn btn-danger btn-sm" onclick="return confirm('حذف شود؟')">🗑️ حذف</a>
    </div>
</div>
{% endfor %}
{% endblock %}
'''

ADD_MACHINE = '''
{% extends base_template %}
{% block content %}
<div class="card">
    <div class="card-header bg-primary text-white">➕ دستگاه جدید</div>
    <div class="card-body">
        <form method="POST">
            <div class="mb-2"><label class="form-label">کد دستگاه</label><input type="text" name="code" class="form-control" required placeholder="M-001"></div>
            <div class="mb-2"><label class="form-label">نام دستگاه</label><input type="text" name="name" class="form-control" required></div>
            <div class="mb-2"><label class="form-label">مدل</label><input type="text" name="model" class="form-control"></div>
            <div class="mb-2"><label class="form-label">برند</label><input type="text" name="brand" class="form-control"></div>
            <div class="mb-2"><label class="form-label">مکان</label><input type="text" name="location" class="form-control" required></div>
            <div class="mb-2"><label class="form-label">وضعیت</label>
                <select name="status" class="form-select">
                    <option value="فعال">فعال</option>
                    <option value="تعمیر">در حال تعمیر</option>
                    <option value="غیرفعال">غیرفعال</option>
                </select>
            </div>
            <div class="mb-2"><label class="form-label">سرویس بعدی</label><input type="text" name="next_service" class="form-control" placeholder="۱۴۰۳-۰۴-۲۵"></div>
            <button type="submit" class="btn btn-success w-100">ثبت دستگاه</button>
        </form>
    </div>
</div>
{% endblock %}
'''

# ============ روت‌ها ============
@app.route('/')
def index():
    machines = Machine.query.all()
    return render_template_string(DASHBOARD, 
        base_template=BASE_TEMPLATE,
        machines=machines,
        total=len(machines),
        active=Machine.query.filter_by(status='فعال').count(),
        maintenance=Machine.query.filter_by(status='تعمیر').count(),
        inactive=Machine.query.filter_by(status='غیرفعال').count()
    )

@app.route('/machines')
def machines():
    return render_template_string(MACHINES_LIST, 
        base_template=BASE_TEMPLATE,
        machines=Machine.query.all()
    )

@app.route('/add-machine', methods=['GET', 'POST'])
def add_machine():
    if request.method == 'POST':
        m = Machine(
            code=request.form.get('code'),
            name=request.form.get('name'),
            model=request.form.get('model'),
            brand=request.form.get('brand'),
            location=request.form.get('location'),
            status=request.form.get('status'),
            next_service=request.form.get('next_service')
        )
        db.session.add(m)
        db.session.commit()
        flash('دستگاه اضافه شد!', 'success')
        return redirect(url_for('machines'))
    return render_template_string(ADD_MACHINE, base_template=BASE_TEMPLATE)

@app.route('/delete-machine/<int:id>')
def delete_machine(id):
    m = Machine.query.get_or_404(id)
    db.session.delete(m)
    db.session.commit()
    flash('حذف شد!', 'danger')
    return redirect(url_for('machines'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
