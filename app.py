from flask import Flask, request, redirect, url_for, flash, render_template_string
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import tempfile
import json

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
        
        for i in range(12):
            m = MaintenanceRecord(
                machine_id=1 if i % 2 == 0 else 2,
                date=datetime.utcnow() - timedelta(days=i*30),
                description=f'تعمیر دوره‌ای {i+1}',
                type='دوره‌ای' if i % 3 == 0 else 'پیشگیرانه' if i % 3 == 1 else 'اضطراری',
                cost=100000 + (i * 50000)
            )
            db.session.add(m)
        db.session.commit()

# ============ HTML اصلی با CDN داخلی ============
MAIN_HTML = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سیستم تعمیرات</title>
    <!-- استفاده از CDN داخلی ایران -->
    <script src="https://cdn.iran.liara.run/chart.js/4.4.0/chart.umd.min.js"></script>
    <style>
        * { direction: rtl; text-align: right; box-sizing: border-box; }
        body { background: #f0f2f5; font-family: Tahoma, Arial, sans-serif; margin: 0; padding-bottom: 70px; }
        .navbar { background: #0d1b2a; color: white; padding: 15px 20px; }
        .navbar-brand { color: white; font-weight: bold; font-size: 1.5rem; text-decoration: none; }
        .container { max-width: 1000px; margin: 0 auto; padding: 15px; }
        .card { background: white; border-radius: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); padding: 15px; margin-bottom: 15px; }
        .card-header { font-weight: 600; font-size: 1.1rem; padding-bottom: 10px; border-bottom: 1px solid #e9ecef; margin-bottom: 10px; }
        .stat-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px; padding: 20px; color: white; margin-bottom: 15px; text-align: center; }
        .stat-card .stat-number { font-size: 2.5rem; font-weight: 700; }
        .stat-card .stat-label { font-size: 0.9rem; opacity: 0.9; }
        .stat-card.stat-green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
        .stat-card.stat-orange { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .stat-card.stat-red { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
        .row { display: flex; flex-wrap: wrap; margin: 0 -8px; }
        .col-6 { width: 50%; padding: 0 8px; box-sizing: border-box; }
        .col-12 { width: 100%; padding: 0 8px; box-sizing: border-box; }
        .chart-container { height: 220px; width: 100%; position: relative; }
        .status-badge { padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 500; display: inline-block; }
        .status-active { background: #d4edda; color: #155724; }
        .status-maintenance { background: #fff3cd; color: #856404; }
        .status-inactive { background: #f8d7da; color: #721c24; }
        .mobile-menu { background: #0d1b2a; padding: 10px; position: fixed; bottom: 0; left: 0; right: 0; z-index: 999; display: flex; justify-content: space-around; }
        .mobile-menu a { color: #a0b4c8; text-decoration: none; font-size: 12px; text-align: center; padding: 5px 0; }
        .mobile-menu a.active { color: white; }
        .mobile-menu i { font-size: 22px; display: block; }
        .btn { display: inline-block; padding: 8px 16px; border-radius: 8px; border: none; cursor: pointer; text-decoration: none; font-size: 14px; }
        .btn-primary { background: #0d1b2a; color: white; }
        .btn-success { background: #28a745; color: white; width: 100%; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-sm { padding: 4px 12px; font-size: 12px; }
        .form-control { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; box-sizing: border-box; margin: 5px 0; }
        .form-label { display: block; margin-bottom: 4px; font-weight: 500; }
        .form-select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; background: white; }
        .table { width: 100%; border-collapse: collapse; }
        .table th, .table td { padding: 10px; text-align: right; border-bottom: 1px solid #e9ecef; }
        .table th { background: #f8f9fa; font-weight: 600; }
        .alert { padding: 12px 16px; border-radius: 8px; margin-bottom: 15px; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-danger { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .text-muted { color: #6c757d; }
        .mb-2 { margin-bottom: 10px; }
        .mb-3 { margin-bottom: 15px; }
        .mt-2 { margin-top: 10px; }
        .d-flex { display: flex; }
        .justify-content-between { justify-content: space-between; }
        .align-items-center { align-items: center; }
        .w-100 { width: 100%; }
        .badge { display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; background: #6c757d; color: white; }
        .bg-secondary { background: #6c757d; }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        @media (max-width: 600px) { .grid-2 { grid-template-columns: 1fr; } .col-6 { width: 100%; } }
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
    <script>
        {script}
    </script>
</body>
</html>
"""

# ============ کمک‌کننده ============
def get_messages():
    msgs = []
    for category, msg in get_flashed_messages(with_categories=True):
        msgs.append(f'<div class="alert alert-{category}">{msg}</div>')
    return ''.join(msgs)

# ============ صفحه اصلی ============
@app.route('/')
def index():
    machines = Machine.query.all()
    total = len(machines)
    active = Machine.query.filter_by(status='فعال').count()
    maintenance = Machine.query.filter_by(status='تعمیر').count()
    inactive = Machine.query.filter_by(status='غیرفعال').count()
    
    months = []
    counts = []
    costs = []
    now = datetime.utcnow()
    for i in range(6):
        month = now - timedelta(days=i*30)
        month_name = f'{month.year}/{month.month:02d}'
        count = MaintenanceRecord.query.filter(
            db.extract('year', MaintenanceRecord.date) == month.year,
            db.extract('month', MaintenanceRecord.date) == month.month
        ).count()
        cost = db.session.query(db.func.sum(MaintenanceRecord.cost)).filter(
            db.extract('year', MaintenanceRecord.date) == month.year,
            db.extract('month', MaintenanceRecord.date) == month.month
        ).scalar() or 0
        months.append(month_name)
        counts.append(count)
        costs.append(int(cost))
    
    months.reverse()
    counts.reverse()
    costs.reverse()
    
    pie_data = json.dumps([active, maintenance, inactive])
    bar_labels = json.dumps(months)
    bar_data = json.dumps(counts)
    cost_data = json.dumps(costs)
    
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
            <div class="chart-container">
                <canvas id="statusPieChart"></canvas>
            </div>
        </div>
        <div class="card">
            <div class="card-header">📈 تعمیرات ماهانه</div>
            <div class="chart-container">
                <canvas id="monthlyBarChart"></canvas>
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
    
    script = f'''
        document.addEventListener('DOMContentLoaded', function() {{
            try {{
                const ctx1 = document.getElementById('statusPieChart').getContext('2d');
                new Chart(ctx1, {{
                    type: 'pie',
                    data: {{
                        labels: ['فعال', 'در حال تعمیر', 'غیرفعال'],
                        datasets: [{{
                            data: {pie_data},
                            backgroundColor: ['#28a745', '#ffc107', '#dc3545'],
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                position: 'bottom',
                                labels: {{ font: {{ size: 12 }} }}
                            }}
                        }}
                    }}
                }});
            }} catch(e) {{
                console.log('Chart error:', e);
            }}
            
            try {{
                const ctx2 = document.getElementById('monthlyBarChart').getContext('2d');
                new Chart(ctx2, {{
                    type: 'bar',
                    data: {{
                        labels: {bar_labels},
                        datasets: [
                            {{
                                label: 'تعداد تعمیرات',
                                data: {bar_data},
                                backgroundColor: '#667eea',
                                borderRadius: 4
                            }},
                            {{
                                label: 'هزینه (تومان)',
                                data: {cost_data},
                                backgroundColor: '#f093fb',
                                borderRadius: 4,
                                yAxisID: 'y1'
                            }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                position: 'bottom',
                                labels: {{ font: {{ size: 10 }} }}
                            }}
                        }},
                        scales: {{
                            y: {{ beginAtZero: true }},
                            y1: {{
                                position: 'left',
                                beginAtZero: true,
                                grid: {{ drawOnChartArea: false }}
                            }}
                        }}
                    }}
                }});
            }} catch(e) {{
                console.log('Chart error:', e);
            }}
        }});
    '''
    
    return MAIN_HTML.format(messages='', content=content, script=script)

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
    return MAIN_HTML.format(messages='', content=content, script='')

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
    return MAIN_HTML.format(messages='', content=content, script='')

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
    return MAIN_HTML.format(messages='', content=content, script='')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
