"""
学习仪表盘路由 - 聚合所有学习数据
"""
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, g
from backend.middleware.auth import require_auth
from backend.models.database import ProgressDAO, StudySessionDAO, KnowledgeDAO, DocumentDAO, NewsDAO, get_db

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.route("/overview", methods=["GET"])
@require_auth
def dashboard_overview():
    """仪表盘概览 — 聚合关键指标
    ---
    tags:
      - 仪表盘
    responses:
      200:
        description: 仪表盘数据
    """
    user_id = g.user_id
    stats = ProgressDAO.get_stats(user_id)

    # 文档统计
    docs = DocumentDAO.get_all(user_id)
    doc_count = len(docs)
    parsed_count = sum(1 for d in docs if d.get("status") == "parsed")

    # 薄弱知识点
    weak_points_raw = KnowledgeDAO.get_weak_points(limit=5, user_id=user_id)
    weak_points = []
    for w in weak_points_raw:
        weak_points.append({
            "topic": w.get("topic", "未知"),
            "mastery_level": w.get("mastery_level", "weak"),
            "filename": w.get("filename", "")
        })

    # 本周学习数据
    today = datetime.now()
    week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
    week_end = today.strftime("%Y-%m-%d")
    week_stats = StudySessionDAO.get_week_stats(week_start, week_end, user_id)

    # 资讯统计
    news_stats = NewsDAO.get_stats(user_id) if hasattr(NewsDAO, "get_stats") else {}
    unread_news = news_stats.get("unread", 0) if news_stats else 0

    # 本周提问/会话数（从原始SQL获取）
    week_questions = 0
    week_sessions = 0
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM study_sessions WHERE user_id=? AND created_at >= ?",
            (user_id, week_start)
        ).fetchone()
        week_sessions = row["cnt"] if row else 0
        conn.close()
    except:
        pass

    return jsonify({
        "metrics": {
            "doc_count": doc_count,
            "parsed_count": parsed_count,
            "assessment_count": stats.get("total_assessments", 0),
            "weak_points": stats.get("weak_points", 0),
            "week_sessions": week_sessions,
            "week_minutes": week_stats.get("total_time", 0) if week_stats else 0,
            "week_questions": week_stats.get("total_questions", 0) if week_stats else 0,
            "unread_news": unread_news
        },
        "weak_points": weak_points,
        "docs": docs[:5]
    })


@dashboard_bp.route("/heatmap", methods=["GET"])
@require_auth
def study_heatmap():
    """最近 90 天学习热力图数据
    ---
    tags:
      - 仪表盘
    """
    user_id = g.user_id
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT date(created_at) as day, SUM(duration_minutes) as minutes
            FROM study_sessions
            WHERE user_id = ? AND created_at >= date('now', '-90 days', 'localtime')
            GROUP BY day
            ORDER BY day
        """, (user_id,)).fetchall()
        data = [[row["day"], row["minutes"]] for row in rows]
        return jsonify({"data": data})
    finally:
        conn.close()


@dashboard_bp.route("/trend", methods=["GET"])
@require_auth
def learning_trend():
    """近 8 周学习趋势
    ---
    tags:
      - 仪表盘
    """
    user_id = g.user_id
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT strftime('%Y-W%W', created_at) as week,
                   SUM(duration_minutes) as minutes,
                   COUNT(*) as sessions,
                   SUM(questions_asked) as questions
            FROM study_sessions
            WHERE user_id = ? AND created_at >= date('now', '-56 days', 'localtime')
            GROUP BY week
            ORDER BY week
            LIMIT 8
        """, (user_id,)).fetchall()
        data = [{
            "week": row["week"],
            "minutes": row["minutes"] or 0,
            "sessions": row["sessions"] or 0,
            "questions": row["questions"] or 0
        } for row in rows]
        return jsonify({"data": data})
    finally:
        conn.close()
