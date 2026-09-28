import os
import socket
from urllib.parse import quote_plus
from flask import Flask, render_template_string, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# Secret key needed to sign session cookies
app.secret_key = os.urandom(24)
# Replace with your PostgreSQL connection string (e.g. Neon, Supabase, or AWS RDS)

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

# --- HTML Templates ---

BASE_STYLE = """
<style>
    body { font-family: Arial, sans-serif; margin: 40px auto; max-width: 650px; line-height: 1.6; }
    .node-badge { background: #e2e8f0; padding: 6px 12px; border-radius: 4px; font-weight: bold; margin-bottom: 20px; }
    .post { border: 1px solid #cbd5e1; border-radius: 8px; padding: 16px; margin-bottom: 20px; }
    .top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
    button, .btn { padding: 6px 12px; margin-right: 8px; cursor: pointer; text-decoration: none; border-radius: 4px; }
    .btn-primary { background: #2563eb; color: white; border: none; }
    .input-field { width: 100%; padding: 8px; margin: 8px 0 16px 0; box-sizing: border-box; }
    .error { color: #dc2626; margin-bottom: 12px; }
</style>
"""

INDEX_TEMPLATE = BASE_STYLE + """
<div class="node-badge">🖥️ Handled by Instance: {{ node }}</div>
<div class="top-bar">
    <h2>Ponder News</h2>
    <div>
        {% if session.get('is_admin') %}
            <a href="/admin/new" class="btn btn-primary">+ Create Post</a>
            <a href="/logout" class="btn">Logout</a>
        {% else %}
            <a href="/login" class="btn">Admin Login</a>
        {% endif %}
    </div>
</div>

{% for post in posts %}
<div class="post">
    <h3>{{ post.title }}</h3>
    <p>{{ post.content }}</p>
    <form method="POST" action="/vote/{{ post.id }}" style="display:inline;">
        <button name="vote" value="like">👍 Like ({{ post.likes }})</button>
        <button name="vote" value="dislike">👎 Dislike ({{ post.dislikes }})</button>
    </form>
</div>
{% endfor %}
"""

LOGIN_TEMPLATE = BASE_STYLE + """
<div class="node-badge">🖥️ Handled by Instance: {{ node }}</div>
<h2>Admin Login</h2>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
<form method="POST" action="/login">
    <label>Username</label>
    <input class="input-field" type="text" name="username" required>
    
    <label>Password</label>
    <input class="input-field" type="password" name="password" required>
    
    <button type="submit" class="btn btn-primary">Sign In</button>
    <a href="/" class="btn">Back to Feed</a>
</form>
"""

ADMIN_NEW_TEMPLATE = BASE_STYLE + """
<div class="node-badge">🖥️ Handled by Instance: {{ node }}</div>
<h2>Create New Post</h2>
<form method="POST" action="/admin/new">
    <label>Title</label>
    <input class="input-field" type="text" name="title" placeholder="Post heading..." required>
    
    <label>Content</label>
    <textarea class="input-field" name="content" rows="5" placeholder="Post body text..." required></textarea>
    
    <button type="submit" class="btn btn-primary">Publish</button>
    <a href="/" class="btn">Cancel</a>
</form>
"""

# --- Routes ---

@app.route('/')
def index():
    posts = Post.query.order_by(Post.id.desc()).all()
    return render_template_string(INDEX_TEMPLATE, posts=posts, node=NODE_ID)

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
            
    return render_template_string(LOGIN_TEMPLATE, error=error, node=NODE_ID)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/admin/new', methods=['GET', 'POST'])
def admin_new():
    # Enforce session authentication
    if not session.get('is_admin'):
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        post = Post(title=title, content=content)
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('index'))
        
    return render_template_string(ADMIN_NEW_TEMPLATE, node=NODE_ID)

@app.route('/vote/<int:post_id>', methods=['POST'])
def vote(post_id):
    post = Post.query.get_or_404(post_id)
    action = request.form.get('vote')
    if action == 'like':
        post.likes += 1
    elif action == 'dislike':
        post.dislikes += 1
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)