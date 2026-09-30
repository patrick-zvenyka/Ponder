import os
import socket
from urllib.parse import quote_plus
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='assets', static_url_path='/assets')
# Secret key needed to sign session cookies
app.secret_key = os.urandom(24)

# PostgreSQL connection string
password = quote_plus("rAKA4NHj2K.FxV$")
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql+psycopg2://postgres.yzfxbmzctireowjjdfdp:{password}@aws-0-eu-west-2.pooler.supabase.com:6543/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
NODE_ID = socket.gethostname()

# --- Database Models ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)

# Create tables and seed initial admin if not existing
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        default_admin = User(
            username='admin',
            password_hash=generate_password_hash('AdminPass123!')
        )
        db.session.add(default_admin)
        db.session.commit()

# --- Routes ---

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.order_by(Post.id.desc()).paginate(
        page=page, per_page=4, error_out=False
    )
    return render_template(
        'index.html', posts=pagination.items, pagination=pagination, node=NODE_ID
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password_input = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password_input):
            session['is_admin'] = True
            session['admin_user'] = user.username
            return redirect(url_for('admin_new'))
        else:
            error = "Invalid username or password"
            
    return render_template('admin_login.html', error=error, node=NODE_ID)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/admin/new', methods=['GET', 'POST'])
def admin_new():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        post = Post(title=title, content=content)
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('index'))
        
    return render_template('admin_dashboard.html', node=NODE_ID)

@app.route('/vote/<int:post_id>', methods=['POST'])
def vote(post_id):
    post = Post.query.get_or_404(post_id)
    action = request.form.get('vote')
    if action == 'like':
        post.likes += 1
    elif action == 'dislike':
        post.dislikes += 1
    db.session.commit()
    page = request.form.get('page', 1, type=int)
    return redirect(url_for('index', page=page))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)