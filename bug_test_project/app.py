import os
from flask import Flask, jsonify, request
from config import Config
from api.tasks import task_bp
from api.users import user_bp
from utils.database import init_db, get_db_session

# 初始化Flask应用
app = Flask(__name__)
app.config.from_object(Config)

# 注册蓝图
app.register_blueprint(task_bp, url_prefix='/api/tasks')
app.register_blueprint(user_bp, url_prefix='/api/users')

@app.before_request
def before_request():
    # 在每个请求开始时初始化数据库会话
    # 实际项目中，这里可能需要更复杂的依赖注入或上下文管理
    pass

@app.teardown_request
def teardown_request(exception=None):
    # 在每个请求结束时关闭数据库会话
    # 假设 get_db_session() 提供了上下文管理或清理机制
    # 实际应用中，应确保会话被正确关闭或回滚
    pass

@app.route('/')
def index():
    return jsonify({"message": "Welcome to the Task Management API"})

if __name__ == '__main__':
    # 确保数据库初始化
    # 实际部署中，数据库初始化应通过迁移工具完成
    print("Initializing database...")
    init_db()
    # 使用环境变量或配置文件中的端口
    port = os.environ.get('PORT', 5000)
    app.run(debug=True, host='0.0.0.0', port=int(port))
