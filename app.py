from flask import Flask, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import tempfile

app = Flask(__name__)
app.secret_key = 'my-secret-key-12345'

# ============ دیتابیس ============
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

# ============ مدل تعمیرات ============
class MaintenanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'))
    machine = db.relationship('Machine', backref='maintenances')
    date = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(500))
    type = db.Column(db.String(50))
    cost = db.Column(db.Float, default=0)

# ============ ایجاد دیتابیس ============
with app.app_context():
    db.create_all()
    if not Machine.query.first():
        m1 = Machine(code='M-001', name='کولر گازی', model='XZ-2000', brand='گالی', location='تهران', status='فعال', next_service='۱۴۰۳-۰۴-۲۵')
        m2 = Machine(code='M-002', name='ژنراتور', model='G-500', brand='کاترپیلار', location='تهران', status='تعمیر', next_service='۱۴۰۳-۰۴-۱۰')
        m3 = Machine(code='M-003', name='پمپ آب', model='P-100', brand='پنتاکس', location='تهران', status='تعمیر', next_service='۱۴۰۳-۰۵-۲۰')
        db.session.add_all([m1, m2, m3])
        db.session.commit()

# ============ HTML اصلی ============
MAIN_HTML = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سیستم تعمیرات</title>
    <style>
        * {{ direction: rtl; text-align: right; box-sizing: border-box; }}
        body {{ background: #f0f2f5; font-family: Tahoma, Arial, sans-serif; margin: 0; padding-bottom: 70px; }}
        .navbar {{ background: #0d1b2a; color: white; padding: 15px 20px; }}
        .navbar-brand {{ color: white; font-weight: bold; font-size: 1.5rem; text-decoration: none; }}
        .container {{ max-width: 1000px; margin: 0 auto; padding: 15px; }}
        .card {{ background: white; border-radius: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); padding: 15px; margin-bottom: 15px; }}
        .card-header {{ font-weight: 600; font-size: 1.1rem; padding-bottom: 10px; border-bottom: 1px solid #e9ecef; margin-bottom: 10px; }}
        .stat-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px; padding: 20px; color: white; margin-bottom: 15px; text-align: center; }}
        .stat-card .stat-number {{ font-size: 2.5rem; font-weight: 700; }}
        .stat-card .stat-label {{ font-size: 0.9rem; opacity: 0.9; }}
        .stat-card.stat-green {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }}
        .stat-card.stat-orange {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
        .stat-card.stat-red {{ background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }}
        .row {{ display: flex; flex-wrap: wrap; margin: 0 -8px; }}
        .col-6 {{ width: 50%; padding: 0 8px; box-sizing: border-box; }}
        .col-12 {{ width: 100%; padding: 0 8px; box-sizing: border-box; }}
        .chart-container {{ height: 200px; display: flex; align-items: flex-end; justify-content: center; gap: 8px; padding: 10px 0; }}
        .bar {{ display: flex; flex-direction: column; align-items: center; width: 40px; }}
        .bar-fill {{ width: 30px; border-radius: 4px 4px 0 0; transition: height 0.5s; min-height: 10px; }}
        .bar-label {{ font-size: 10px; color: #666; margin-top: 4px; }}
        .bar-value {{ font-size: 11px; font-weight: bold; margin-bottom: 2px; }}
        .pie-chart {{ display: flex; justify-content: center; gap: 20px; padding: 10px 0; }}
        .pie-item {{ display: flex; flex-direction: column; align-items: center; }}
        .pie-circle {{ width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: bold; color: white; }}
        .pie-label {{ font-size: 12px; margin-top: 4px; color: #555; }}
        .pie-percent {{ font-size: 14px; font-weight: bold; }}
        .status-badge {{ padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 500; display: inline-block; }}
        .status-active {{ background: #d4edda; color: #155724; }}
        .status-maintenance {{ background: #fff3cd; color: #856404; }}
        .status-inactive {{ background: #f8d7da; color: #721c24; }}
        .mobile-menu {{ background: #0d1b2a; padding: 10px; position: fixed; bottom: 0; left: 0; right: 0; z-index: 999; display: flex; justify-content: space-around; }}
        .mobile-menu a {{ color: #a0b4c8; text-decoration: none; font-size: 12px; text-align: center; padding: 5px 0; }}
        .mobile-menu a.active {{ color: white; }}
        .btn {{ display: inline-block; padding: 8px 16px; border-radius: 8px; border: none; cursor: pointer; text-decoration: none; font-size: 14px; }}
        .btn-primary {{ background: #0d1b2a; color: white; }}
        .btn-success {{ background: #28a745; color: white; width: 100%; }}
        .btn-danger {{ background: #dc3545; color: white; }}
        .btn-sm {{ padding: 4px 12px; font-size: 12px; }}
        .form-control {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; box-sizing: border-box; margin: 5px 0; }}
        .form-label {{ display: block; margin-bottom: 4px; font-weight: 500; }}
        .form-select {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; background: white; }}
        .table {{ width: 100%; border-collapse: collapse; }}
        .table th, .table td {{ padding: 10px; text-align: right; border-bottom: 1px solid #e9ecef; }}
        .table th {{ background: #f8f9fa; font-weight: 600; }}
        .alert {{ padding: 12px 16px; border-radius: 8px; margin-bottom: 15px; }}
        .alert-success {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
        .alert-danger {{ background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
        .text-muted {{ color: #6c757d; }}
        .mb-2 {{ margin-bottom: 10px; }}
        .mb-3 {{ margin-bottom: 15px; }}
        .d-flex {{ display: flex; }}
        .justify-content-between {{ justify-content: space-between; }}
        .align-items-center {{ align-items: center; }}
        .w-100 {{ width: 100%; }}
        .badge {{ display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; background: #6c757d; color: white; }}
        .bg-secondary {{ background: #6c757d; }}
        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
        .text-center {{ text-align: center; }}
        @media (max-width: 600px) {{ .grid-2 {{ grid-template-columns: 1fr; }} .col-6 {{ width: 100%; }} }}
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="container" style="padding: 0;">
            <a class="navbar-brand" href="/">🔧 سیستم تعمیرات</a>
        </div>
    </nav>
    <div class="container">
        {messages}
        {content}
    </div>
    <div class="mobile-menu">
        <a href="/" class="active"><span style="font-size:22px;">🏠</span><br>داشبورد</a>
        <a href="/machines"><span style="font-size:22px;">📦</span><br>دستگاه‌ها</a>
        <a href="/maintenance"><span style="font-size:22px;">📊</span><br>تعمیرات</a>
        <a href="/add-machine"><span style="font-size:22px;">➕</span><br>جدید</a>
    </div>
</body>
</html>
"""

# ============ صفحه اصلی ============
@app.route('/')
def index():
    machines = Machine.query.all()
    total = len(machines)
    active = Machine.query.filter_by(status='فعال').count()
    maintenance = Machine.query.filter_by(status='تعمیر').count()
    inactive = Machine.query.filter_by(status='غیرفعال').count()
    
    total_percent = total or 1
    active_percent = round((active / total_percent) * 100)
    maintenance_percent = round((maintenance / total_percent) * 100)
    inactive_percent = round((inactive / total_percent) * 100)
    
    months = []
    counts = []
    now = datetime.utcnow()
    for i in range(6):
        month = now - timedelta(days=i*30)
        month_name = f'{month.year}/{month.month:02d}'
        count = MaintenanceRecord.query.filter(
            db.extract('year', MaintenanceRecord.date) == month.year,
            db.extract('month', MaintenanceRecord.date) == month.month
        ).count()
        months.append(month_name)
        counts.append(count)
    months.reverse()
    counts.reverse()
    max_count = max(counts) if counts else 1
    
    bars_html = ''
    colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe']
    for i, (month, count) in enumerate(zip(months, counts)):
        height = (count / max_count) * 150 if max_count > 0 else 0
        color = colors[i % len(colors)]
        bars_html += f'''
        <div class="bar">
            <div class="bar-value">{count}</div>
            <div class="bar-fill" style="height:{height}px;background:{color};"></div>
            <div class="bar-label">{month}</div>
        </div>
        '''
    
    content = f'''
    <div class="row">
        <div class="col-6"><div class="stat-card"><div class="stat-number">{total}</div><div class="stat-label">تعداد دستگاه‌ها</div></div></div>
        <div class="col-6"><div class="stat-card stat-green"><div class="stat-number">{active}</div><div class="stat-label">فعال</div></div></div>
        <div class="col-6"><div class="stat-card stat-orange"><div class="stat-number">{maintenance}</div><div class="stat-label">در حال تعمیر</div></div></div>
        <div class="col-6"><div class="stat-card stat-red"><div class="stat-number">{inactive}</div><div class="stat-label">غیرفعال</div></div></div>
    </div>
    
    <div class="grid-2">
        <div class="card">
            <div class="card-header">📊 وضعیت دستگاه‌ها</div>
            <div class="pie-chart">
                <div class="pie-item">
                    <div class="pie-circle" style="background:#28a745;">{active_percent}%</div>
                    <div class="pie-label">✅ فعال</div>
                </div>
                <div class="pie-item">
                    <div class="pie-circle" style="background:#ffc107;">{maintenance_percent}%</div>
                    <div class="pie-label">⚠️ تعمیر</div>
                </div>
                <div class="pie-item">
                    <div class="pie-circle" style="background:#dc3545;">{inactive_percent}%</div>
                    <div class="pie-label">❌ غیرفعال</div>
                </div>
            </div>
        </div>
        <div class="card">
            <div class="card-header">📈 تعمیرات ماهانه</div>
            <div class="chart-container">
                {bars_html}
            </div>
        </div>
    </div>
    
    <div class="card">
        <div class="card-header">📋 لیست دستگاه‌ها</div>
        <table class="table">
            <thead><tr><th>نام</th><th>وضعیت</th><th>سرویس بعدی</th></tr></thead>
            <tbody>
    '''
    for m in machines:
        cls = 'active' if m.status == 'فعال' else 'maintenance' if m.status == 'تعمیر' else 'inactive'
        content += f'<tr><td>{m.name}</td><td><span class="status-badge status-{cls}">{m.status}</span></td><td>{m.next_service or "-"}</td></tr>'
    content += '''
            </tbody>
        </table>
    </div>
    '''
    
    return MAIN_HTML.format(messages='', content=content)

# ============ مدیریت دستگاه‌ها ============
@app.route('/machines')
def machines():
    machines = Machine.query.all()
    content = '''
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 style="margin:0;">🏭 دستگاه‌ها</h5>
        <a href="/add-machine" class="btn btn-primary btn-sm">➕ جدید</a>
    </div>
    '''
    for m in machines:
        cls = 'active' if m.status == 'فعال' else 'maintenance' if m.status == 'تعمیر' else 'inactive'
        content += f'''
        <div class="card">
            <div class="card-body">
                <h6 style="margin:0 0 8px 0;">{m.name}</h6>
                <span class="badge bg-secondary">{m.code}</span>
                <span class="status-badge status-{cls}">{m.status}</span>
                <p class="text-muted" style="margin:8px 0 4px 0;">📍 {m.location}</p>
                <p class="text-muted" style="margin:0 0 8px 0;">📅 سرویس بعدی: {m.next_service or '-'}</p>
                <a href="/delete-machine/{m.id}" class="btn btn-danger btn-sm" onclick="return confirm('حذف شود؟')">🗑️ حذف</a>
            </div>
        </div>
        '''
    return MAIN_HTML.format(messages='', content=content)

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
    
    content = '''
    <div class="card">
        <div class="card-header" style="background:#0d1b2a;color:white;border-radius:16px 16px 0 0;padding:15px;">➕ دستگاه جدید</div>
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
                <button type="submit" class="btn btn-success">ثبت دستگاه</button>
            </form>
        </div>
    </div>
    '''
    return MAIN_HTML.format(messages='', content=content)

@app.route('/delete-machine/<int:id>')
def delete_machine(id):
    m = Machine.query.get_or_404(id)
    db.session.delete(m)
    db.session.commit()
    flash('حذف شد!', 'danger')
    return redirect(url_for('machines'))

@app.route('/maintenance')
def maintenance_list():
    records = MaintenanceRecord.query.order_by(MaintenanceRecord.date.desc()).limit(20).all()
    content = '''
    <div class="card">
        <div class="card-header">📝 آخرین تعمیرات</div>
        <table class="table">
            <thead><tr><th>دستگاه</th><th>تاریخ</th><th>نوع</th><th>هزینه</th></tr></thead>
            <tbody>
    '''
    for r in records:
        content += f'''
        <tr>
            <td>{r.machine.name if r.machine else 'نامشخص'}</td>
            <td>{r.date.strftime('%Y/%m/%d')}</td>
            <td>{r.type}</td>
            <td>{int(r.cost):,} تومان</td>
        </tr>
        '''
    content += '''
            </tbody>
        </table>
    </div>
    '''
    return MAIN_HTML.format(messages='', content=content)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
