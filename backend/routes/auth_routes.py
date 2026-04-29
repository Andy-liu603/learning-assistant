"""
认证路由 - 用户注册、登录、Token 刷新、用户设置
"""
import datetime
import json
import jwt
from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
import config
from backend.middleware.auth import require_auth
from backend.models.database import get_db
from backend.utils.logger import log

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    """用户注册"""
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "")

    if not username or not email or not password:
        return jsonify({"error": "用户名、邮箱和密码不能为空"}), 400

    if len(username) < 2 or len(username) > 30:
        return jsonify({"error": "用户名长度 2-30 个字符"}), 400

    if len(password) < 6:
        return jsonify({"error": "密码至少 6 个字符"}), 400

    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email)
        ).fetchone()
        if existing:
            return jsonify({"error": "用户名或邮箱已存在"}), 409

        password_hash = generate_password_hash(password)
        cursor = conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash)
        )
        user_id = cursor.lastrowid

        # 创建默认用户设置
        conn.execute(
            "INSERT INTO user_settings (user_id, preferences) VALUES (?, '{}')",
            (user_id,)
        )
        conn.commit()

        log.info(f"用户注册成功: {username} (id={user_id})")

        token = _gen_token(user_id, username)
        return jsonify({
            "message": "注册成功",
            "user": {"id": user_id, "username": username, "email": email},
            "access_token": token
        }), 201

    except Exception as e:
        log.error(f"注册失败: {e}")
        return jsonify({"error": "注册失败"}), 500
    finally:
        conn.close()


@auth_bp.route("/login", methods=["POST"])
def login():
    """用户登录"""
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400

    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id, username, email, password_hash FROM users WHERE username = ? OR email = ?",
            (username, username)
        ).fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "用户名或密码错误"}), 401

        log.info(f"用户登录: {user['username']} (id={user['id']})")

        token = _gen_token(user["id"], user["username"])
        return jsonify({
            "message": "登录成功",
            "user": {"id": user["id"], "username": user["username"], "email": user["email"]},
            "access_token": token
        })
    except Exception as e:
        log.error(f"登录失败: {e}")
        return jsonify({"error": "登录失败"}), 500
    finally:
        conn.close()


@auth_bp.route("/refresh", methods=["POST"])
@require_auth
def refresh():
    """刷新 token"""
    token = _gen_token(g.user_id, g.username)
    return jsonify({"access_token": token})


@auth_bp.route("/me", methods=["GET"])
@require_auth
def me():
    """获取当前用户信息"""
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id, username, email, created_at FROM users WHERE id = ?",
            (g.user_id,)
        ).fetchone()
        if not user:
            return jsonify({"error": "用户不存在"}), 404
        return jsonify(dict(user))
    finally:
        conn.close()


def _gen_token(user_id: int, username: str) -> str:
    """生成 JWT access token"""
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=config.JWT_EXPIRE_DAYS),
        "iat": datetime.datetime.utcnow()
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")


# ===== 用户设置 =====

@auth_bp.route("/user/settings", methods=["GET"])
@require_auth
def get_settings():
    """获取用户偏好"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT preferences FROM user_settings WHERE user_id = ?", (g.user_id,)
        ).fetchone()
        prefs = json.loads(row["preferences"]) if row and row["preferences"] else {}
        return jsonify({"preferences": prefs})
    finally:
        conn.close()


@auth_bp.route("/user/settings", methods=["PUT"])
@require_auth
def update_settings():
    """更新用户偏好"""
    data = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO user_settings (user_id, preferences) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET preferences = ?, updated_at = datetime('now','localtime')",
            (g.user_id, json.dumps(data), json.dumps(data))
        )
        conn.commit()
        return jsonify({"status": "updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
