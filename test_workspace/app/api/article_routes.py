from flask import Blueprint, request, jsonify, current_app, g
from models import db, Article
from datetime import datetime

article_bp = Blueprint('article', __name__) 

@article_bp.before_request
def load_user_data():
    # 假设用户认证已在其他地方处理，这里只是为了演示API的结构
    # 实际应用中，需要从请求头或会话中获取当前用户ID
    if 'user_id' not in g or g.user_id is None:
        # 模拟未登录用户，实际应返回401
        pass

@article_bp.route('/', methods=['POST'])
def create_article():
    # 检查用户是否登录
    if g.user_id is None:
        return jsonify({'message': 'Unauthorized'}), 401

    data = request.get_json()
    if not data or 'title' not in data or 'content' not in data:
        return jsonify({'message': 'Missing required fields: title and content'}), 400

    try:
        new_article = Article(
            title=data['title'],
            content=data['content'],
            user_id=g.user_id
        )
        db.session.add(new_article)
        db.session.commit()
        return jsonify({
            'message': 'Article created successfully',
            'article': {
                'id': new_article.id,
                'title': new_article.title,
                'content': new_article.content,
                'author_id': new_article.user_id,
                'created_at': new_article.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating article: {str(e)}'}), 500

@article_bp.route('/', methods=['GET'])
def list_articles():
    # 假设只允许查看已登录用户创建的文章，或者所有文章
    # 这里我们返回所有文章，但实际应考虑权限
    articles = Article.query.order_by(Article.created_at.desc()).all()
    
    article_list = []
    for article in articles:
        article_list.append({
            'id': article.id,
            'title': article.title,
            'content': article.content[:100] + '...' if len(article.content) > 100 else article.content,
            'author_id': article.user_id,
            'created_at': article.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify({'articles': article_list}), 200

@article_bp.route('/<int:article_id>', methods=['GET'])
def get_article_detail(article_id):
    article = Article.query.get_or_404(article_id)
    
    return jsonify({
        'id': article.id,
        'title': article.title,
        'content': article.content,
        'author_id': article.user_id,
        'created_at': article.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }), 200

@article_bp.route('/<int:article_id>', methods=['PUT'])
def update_article(article_id):
    # 权限检查：确保只有文章作者或管理员可以修改
    article = Article.query.get_or_404(article_id)
    if g.user_id != article.user_id: # 简化处理，只允许作者修改
        return jsonify({'message': 'Unauthorized to update this article'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400

    try:
        article.title = data.get('title', article.title)
        article.content = data.get('content', article.content)
        
        db.session.commit()
        return jsonify({
            'message': 'Article updated successfully',
            'article': {
                'id': article.id,
                'title': article.title,
                'content': article.content,
                'author_id': article.user_id,
                'created_at': article.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating article: {str(e)}'}), 500

@article_bp.route('/<int:article_id>', methods=['DELETE'])
def delete_article(article_id):
    # 权限检查：确保只有文章作者或管理员可以删除
    article = Article.query.get_or_404(article_id)
    if g.user_id != article.user_id: # 简化处理，只允许作者删除
        return jsonify({'message': 'Unauthorized to delete this article'}), 403

    try:
        db.session.delete(article)
        db.session.commit()
        return jsonify({'message': 'Article deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting article: {str(e)}'}), 500

# 注册蓝图到主应用
# 注意：在实际的 app.py 中需要导入并注册这个蓝图
# 例如：app.register_blueprint(article_bp, url_prefix='/api/articles')
