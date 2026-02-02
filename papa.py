import os
import sys

# Fail fast with a helpful message when a dependency is missing
try:
    import bleach
    from datetime import datetime
    from flask import Flask, render_template, request, redirect, url_for, flash, session
    from flask_sqlalchemy import SQLAlchemy
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    from werkzeug.security import generate_password_hash, check_password_hash
except ImportError as e:
    missing = str(e).split()[-1].strip("'\"")
    print(f"Missing dependency: {missing}. Please install project dependencies with:\n    pip install -r requirements.txt")
    sys.exit(1)

app = Flask(__name__, template_folder=os.path.dirname(__file__))
# Use env vars for production configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secure-key-default-replace-me')
app.config['DEBUG'] = os.environ.get('DEBUG', 'False').lower() in ('1','true','yes')

# Simple health check endpoint used by hosting platforms
@app.route('/health')
def health():
    try:
        # quick DB check
        db.session.execute('SELECT 1')
        return 'OK', 200
    except Exception:
        return 'DB error', 500

# Serve a favicon (point to static SVG)
@app.route('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='favicon.svg'))
#ดึงค่า URLฐานข้อมลจากตัวแปรระบบ (จะไปตั้งค่าใน Render)
# Normalize DATABASE_URL: some providers return 'postgres://' which SQLAlchemy may not accept
db_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:adminworakanlnwzaza@db.xuigjtlhxvpjhlvecfmo.supabase.co:5432/postgres' )
if db_url and db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

limiter = Limiter(key_func=get_remote_address, app=app, storage_uri="memory://")

#
class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    content = db.Column(db.Text)
    date_posted = db.Column(db.DateTime, default=datetime.now)

# Admin user stored in DB for persistent password
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    password_hash = db.Column(db.String(255), nullable=False)


def set_admin_password(plaintext):
    admin = Admin.query.first()
    if not admin:
        admin = Admin(password_hash=generate_password_hash(plaintext))
        db.session.add(admin)
    else:
        admin.password_hash = generate_password_hash(plaintext)
    db.session.commit()


def check_admin_password(plaintext):
    admin = Admin.query.first()
    if admin:
        return check_password_hash(admin.password_hash, plaintext)
    # fallback: if an env password exists and matches, bootstrap and persist it
    env_pw = os.environ.get('ADMIN_PASSWORD')
    if env_pw and plaintext == env_pw:
        set_admin_password(plaintext)
        return True
    return False

# Create tables and bootstrap admin if env password provided
with app.app_context():
    db.create_all()
    if Admin.query.first() is None:
        env_pw = os.environ.get('ADMIN_PASSWORD')
        if env_pw:
            set_admin_password(env_pw)

#
@app.route('/', methods=['GET', 'POST'])
#@limiter.limit("10 per minute")
def index():
    if request.method == 'POST':
        if request.form.get('extra_field'): return "Bot Detected!", 400
        name = bleach.clean(request.form.get('name', 'ผ้ไม่ออกนาม'))
        content = bleach.clean(request.form.get('content', ''))

        if not content.strip():
            flash("กรุณาใส่รายละเอียด")
            return redirect(url_for('index'))
        
        new_item = Complaint(name=name, content=content)
        db.session.add(new_item)
        db.session.commit()

        flash("ส่งเรื่องเรียบร้อย วัยรุ่น!")
        return redirect(url_for('index'))
    
    return render_template('index.html')

#
#
# (Optional) environment-provided admin password used only to bootstrap DB
ADMIN_PASS = os.environ.get('ADMIN_PASSWORD')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        pw = request.form.get('pw', '')
        if not check_admin_password(pw):
            flash("รหัสผ่านไม่ถูกต้อง")
            return redirect(url_for('admin_login'))
        session['is_admin'] = True
        flash("เข้าสู่ระบบผู้ดูแลเรียบร้อย")
        return redirect(url_for('admin_view'))
    return render_template('admin_login.html')

@app.route('/secret-admin-view')
def admin_view():
    # Require admin session
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    items = Complaint.query.order_by(Complaint.date_posted.desc()).all()
    return render_template('admin_view.html', complaints=items)

@app.route('/admin-change-password', methods=['GET', 'POST'])
def admin_change_password():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        current = request.form.get('current', '')
        newpw = request.form.get('new', '')
        if not check_admin_password(current):
            flash('รหัสผ่านปัจจุบันไม่ถูกต้อง')
            return redirect(url_for('admin_change_password'))
        if not newpw or len(newpw) < 6:
            flash('รหัสผ่านต้องมีความยาวอย่างน้อย 6 ตัวอักษร')
            return redirect(url_for('admin_change_password'))
        set_admin_password(newpw)
        flash('เปลี่ยนรหัสผ่านเรียบร้อย')
        return redirect(url_for('admin_view'))
    return render_template('admin_change_password.html')

@app.route('/admin-logout')
def admin_logout():
    session.pop('is_admin', None)
    flash("ออกจากระบบแล้ว")
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)