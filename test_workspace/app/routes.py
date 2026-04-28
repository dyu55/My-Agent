from flask import Blueprint, request, jsonify, redirect, url_for, session, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# 初始化数据库和蓝图
db = SQLAlchemy()
api_bp = Blueprint('api', __name__) 

# --- 数据库模型 ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

# --- 用户认证 API 路由 ---
@api_bp.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'message': 'Missing username or password'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'Username already exists'}), 409

    new_user = User(username=data['username']) 
    new_user.set_password(data['password'])
    
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'User registered successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Registration failed: {str(e)}'}), 500

@api_bp.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'message': 'Missing username or password'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if user and user.check_password(data['password']):
        # 成功登录，返回用户数据和Token（这里简化为返回用户ID和用户名）
        return jsonify({
            'message': 'Login successful',
            'user_id': user.id,
            'username': user.username
        }), 200
    else:
        return jsonify({'message': 'Invalid credentials'}), 401

@api_bp.route('/logout', methods=['POST'])
def logout_user():
    # 在实际应用中，这里应该清除JWT或Session
    return jsonify({'message': 'Logout successful'}), 200

# --- 文章 CRUD API 路由 ---
@api_bp.route('/articles', methods=['POST'])
def create_article():
    # 假设通过请求头或session获取当前用户ID
    # 为了简化，我们假设用户ID是固定的或从请求体获取（实际应从认证机制获取）
    data = request.get_json()
    if not data or 'title' not in data or 'content' not in data:
        return jsonify({'message': 'Missing title or content'}), 400

    # 假设用户ID从请求头或全局状态获取，这里使用一个占位符
    # 实际项目中，应从JWT或Session中获取当前登录用户的ID
    current_user_id = 1 # 假设用户ID为1

    new_article = Article(
        title=data['title'],
        content=data['content'],
        user_id=current_user_id
    )
    
    try:
        db.session.add(new_article)
        db.session.commit()
        return jsonify({'message': 'Article created successfully', 'article': {'id': new_article.id, 'title': new_article.title}}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating article: {str(e)}'}), 500

@api_bp.route('/articles', methods=['GET'])
def get_articles():
    articles = Article.query.all()
    articles_list = [{'id': a.id, 'title': a.title, 'content': a.content, 'user_id': a.user_id} for a in articles]
    return jsonify({'articles': articles_list}), 200

@api_bp.route('/articles/<int:article_id>', methods=['GET'])
def get_article(article_id):
    article = Article.query.get_or_404(article_id)
    return jsonify({'id': article.id, 'title': article.title, 'content': article.content, 'user_id': article.user_id}), 200

@api_bp.route('/articles/<int:article_id>', methods=['PUT'])
def update_article(article_id):
    data = request.get_json()
    article = Article.query.get_or_404(article_id)
    
    if 'title' in data: article.title = data['title']
    if 'content' in data: article.content = data['content']
    
    try:
        db.session.commit()
        return jsonify({'message': 'Article updated successfully', 'article': {'id': article.id, 'title': article.title, 'content': article.content}}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating article: {str(e)}'}), 500

@api_bp.route('/articles/<int:article_id>', methods=['DELETE'])
def delete_article(article_id):
    article = Article.query.get_or_404(article_id)
    try:
        db.session.delete(article)
        db.session.commit()
        return jsonify({'message': 'Article deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting article: {str(e)}'}), 500

# 注册蓝图到主应用（此部分通常在 app.py 中完成）
# 注意：在实际项目中，需要确保db和api_bp在主应用中正确初始化和注册。

# 导出蓝图和模型，供主应用使用
__all__ = ['api_bp', 'User', 'Article']
