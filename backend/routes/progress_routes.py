"""
API 路由 - 学习进度与报告
"""
from flask import Blueprint, request, jsonify, g, send_from_directory
from services.report_service import ReportService
from models.database import (
    ProgressDAO, KnowledgeDAO, StudySessionDAO,
    ReportDAO, ConversationDAO, AssessmentDAO, get_db
)
from backend.middleware.auth import require_auth
import os

progress_bp = Blueprint("progress", __name__)


@progress_bp.route("/api/progress", methods=["GET"])
@require_auth
def get_progress():
    progress = ProgressDAO.get_all(user_id=g.user_id)

    conn = get_db()
    for p in progress:
        doc_id = p["document_id"]
        assessment_stats = conn.execute(
            "SELECT COUNT(*) as total, "
            "COALESCE(MAX(score), 0) as best_score, "
            "COALESCE(AVG(score), 0) as avg_score, "
            "COALESCE(SUM(correct_count), 0) as total_correct "
            "FROM assessments WHERE document_id = ? AND status = 'completed' AND user_id = ?",
            (doc_id, g.user_id)
        ).fetchone()
        p["assessment_count"] = assessment_stats["total"] if assessment_stats else 0
        p["best_score"] = round(float(assessment_stats["best_score"] or 0), 1) if assessment_stats else 0
        p["avg_score"] = round(float(assessment_stats["avg_score"] or 0), 1) if assessment_stats else 0
    conn.close()

    return jsonify({"progress": progress})


@progress_bp.route("/api/progress/stats", methods=["GET"])
@require_auth
def get_stats():
    stats = ProgressDAO.get_stats(user_id=g.user_id)
    return jsonify(stats)


@progress_bp.route("/api/progress/<int:doc_id>", methods=["PUT"])
@require_auth
def update_progress(doc_id):
    data = request.get_json() or {}
    status = data.get("status")
    confidence = data.get("confidence")
    notes = data.get("notes")

    ProgressDAO.update(doc_id, status=status, confidence=confidence, notes=notes)
    return jsonify({"status": "updated"})


@progress_bp.route("/api/knowledge/weak", methods=["GET"])
@require_auth
def get_weak_points():
    limit = request.args.get("limit", 10, type=int)
    points = KnowledgeDAO.get_weak_points(limit, user_id=g.user_id)
    return jsonify({"weak_points": points})


@progress_bp.route("/api/knowledge/encounter", methods=["POST"])
@require_auth
def record_encounter():
    data = request.get_json() or {}
    document_id = data.get("document_id")
    topic = data.get("topic")
    mastery = data.get("mastery", "learning")
    if document_id and topic:
        KnowledgeDAO.upsert(document_id, topic, mastery, user_id=g.user_id)
        return jsonify({"status": "recorded"})
    return jsonify({"error": "缺少参数"}), 400


@progress_bp.route("/api/reports/generate", methods=["POST"])
@require_auth
def generate_report():
    data = request.get_json() or {}
    week_start = data.get("week_start")
    week_end = data.get("week_end")

    if week_start and week_end:
        result = ReportService.generate_manual_report(week_start, week_end, user_id=g.user_id)
    else:
        result = ReportService.generate_weekly_report(user_id=g.user_id)

    return jsonify(result)


@progress_bp.route("/api/reports", methods=["GET"])
@require_auth
def list_reports():
    limit = request.args.get("limit", 5, type=int)
    reports = ReportDAO.get_latest(limit, user_id=g.user_id)
    return jsonify({"reports": reports})


@progress_bp.route("/api/reports/<int:report_id>", methods=["GET"])
@require_auth
def get_report(report_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM weekly_reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "报告不存在"}), 404
    return jsonify(dict(row))


@progress_bp.route("/api/knowledge/mastery", methods=["GET"])
@require_auth
def get_knowledge_mastery():
    doc_id = request.args.get("document_id", type=int)

    conn = get_db()
    if doc_id:
        rows = conn.execute(
            "SELECT kp.topic, kp.mastery_level, kp.encounter_count, "
            "kp.correct_count, kp.document_id, d.filename as source_file "
            "FROM knowledge_points kp JOIN documents d ON kp.document_id = d.id "
            "WHERE kp.document_id = ? AND kp.user_id = ? ORDER BY kp.encounter_count DESC",
            (doc_id, g.user_id)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT kp.topic, kp.mastery_level, kp.encounter_count, "
            "kp.correct_count, kp.document_id, d.filename as source_file "
            "FROM knowledge_points kp JOIN documents d ON kp.document_id = d.id "
            "WHERE kp.user_id = ? ORDER BY kp.encounter_count DESC LIMIT 30",
            (g.user_id,)
        ).fetchall()

    doc_stats = {}
    doc_rows = conn.execute(
        "SELECT document_id, COUNT(*) as assess_count, "
        "COALESCE(AVG(score), 0) as avg_score "
        "FROM assessments WHERE status='completed' AND user_id=? GROUP BY document_id",
        (g.user_id,)
    ).fetchall()
    for dr in doc_rows:
        doc_stats[dr["document_id"]] = {
            "assess_count": dr["assess_count"],
            "avg_score": round(float(dr["avg_score"]), 1)
        }
    conn.close()

    points = []
    level_rate_map = {"mastered": 90, "familiar": 70, "learning": 40, "weak": 15, "unknown": 0}

    for r in rows:
        d = dict(r)
        enc = d["encounter_count"] or 0
        cor = d["correct_count"] or 0
        if enc > 0 and cor > 0:
            d["mastery_rate"] = round(cor / enc * 100, 1)
        elif enc > 0:
            d["mastery_rate"] = level_rate_map.get(d["mastery_level"], 40)
        else:
            d["mastery_rate"] = 0.0
        did = d.get("document_id")
        d["doc_assess_count"] = doc_stats.get(did, {}).get("assess_count", 0)
        d["doc_avg_score"] = doc_stats.get(did, {}).get("avg_score", 0)
        points.append(d)

    return jsonify({"knowledge_points": points})


@progress_bp.route("/api/progress/overview", methods=["GET"])
@require_auth
def get_progress_overview():
    stats = ProgressDAO.get_stats(user_id=g.user_id)

    conn = get_db()
    recent = conn.execute(
        "SELECT a.*, d.filename FROM assessments a "
        "JOIN documents d ON a.document_id = d.id "
        "WHERE a.status = 'completed' AND a.user_id = ? "
        "ORDER BY a.created_at DESC LIMIT 5",
        (g.user_id,)
    ).fetchall()

    mastery_dist = conn.execute(
        "SELECT mastery_level, COUNT(*) as count FROM knowledge_points "
        "WHERE user_id = ? GROUP BY mastery_level",
        (g.user_id,)
    ).fetchall()
    conn.close()

    mastery_map = {}
    for r in mastery_dist:
        mastery_map[r["mastery_level"]] = r["count"]

    return jsonify({
        "stats": stats,
        "recent_assessments": [dict(r) for r in recent],
        "mastery_distribution": mastery_map
    })


@progress_bp.route("/api/reports/<int:report_id>/download", methods=["GET"])
@require_auth
def download_report(report_id):
    """下载报告 Markdown 文件"""
    conn = get_db()
    row = conn.execute("SELECT * FROM weekly_reports WHERE id = ? AND user_id = ?", (report_id, g.user_id)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "报告不存在"}), 404

    file_path = row["file_path"]
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "报告文件不存在"}), 404

    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    return send_from_directory(directory, filename, as_attachment=True,
                               download_name=filename,
                               mimetype="text/markdown; charset=utf-8")


@progress_bp.route("/api/progress/calendar", methods=["GET"])
@require_auth
def get_calendar():
    """返回最近 90 天的学习活跃度日历数据"""
    from datetime import datetime, timedelta
    days = request.args.get("days", 90, type=int)

    conn = get_db()
    # 从 study_sessions 和 assessments 统计每日学习活动
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT DATE(created_at) as date, COUNT(*) as count FROM ("
        "  SELECT created_at FROM study_sessions WHERE user_id=? AND created_at >= ? "
        "  UNION ALL "
        "  SELECT completed_at as created_at FROM assessments WHERE user_id=? AND status='completed' AND completed_at >= ?"
        ") GROUP BY DATE(created_at) ORDER BY date",
        (g.user_id, start_date, g.user_id, start_date)
    ).fetchall()
    conn.close()

    calendar = []
    for r in rows:
        calendar.append({"date": r["date"], "count": r["count"]})

    return jsonify({"calendar": calendar, "days": days})


@progress_bp.route("/api/progress/mastery", methods=["GET"])
@require_auth
def get_mastery():
    """五级掌握度综合数据"""
    conn = get_db()

    # 所有知识点统计
    kp_rows = conn.execute(
        "SELECT kp.topic, kp.mastery_level, kp.encounter_count, kp.correct_count, "
        "kp.document_id, d.filename as source_file "
        "FROM knowledge_points kp JOIN documents d ON kp.document_id = d.id "
        "WHERE kp.user_id = ? ORDER BY kp.encounter_count DESC",
        (g.user_id,)
    ).fetchall()

    # 每个文档的测评统计
    doc_rows = conn.execute(
        "SELECT lp.document_id, d.filename, lp.status, lp.confidence_score as confidence, "
        "COALESCE(MAX(a.score), 0) as best_score, "
        "COUNT(a.id) as assess_count, "
        "COALESCE(AVG(a.score), 0) as avg_score "
        "FROM learning_progress lp "
        "JOIN documents d ON lp.document_id = d.id "
        "LEFT JOIN assessments a ON a.document_id = lp.document_id AND a.status='completed' AND a.user_id=? "
        "WHERE lp.user_id = ? "
        "GROUP BY lp.document_id ORDER BY d.created_at DESC",
        (g.user_id, g.user_id)
    ).fetchall()

    # 总文档数和学习天数统计
    total_docs = len(doc_rows)
    study_day_row = conn.execute(
        "SELECT COUNT(DISTINCT DATE(created_at)) as days FROM study_sessions WHERE user_id=?",
        (g.user_id,)
    ).fetchone()
    study_days = study_day_row["days"] if study_day_row else 0

    conn.close()

    # 五级掌握度映射
    def calc_mastery_level(avg_score, assess_count, mastery_level):
        if assess_count == 0:
            return 0  # L0 未接触
        if assess_count >= 3 and avg_score >= 90:
            return 4  # L4 专家
        if assess_count >= 2 and avg_score >= 80:
            return 3  # L3 精通
        if assess_count >= 1 and avg_score >= 60:
            return 2  # L2 熟悉
        if assess_count >= 1:
            return 1  # L1 入门
        return 0

    level_names = {0: "未接触", 1: "入门", 2: "熟悉", 3: "精通", 4: "专家"}
    level_colors = {
        0: "#9CA3AF",  # gray
        1: "#F59E0B",  # amber
        2: "#3B82F6",  # blue
        3: "#22C55E",  # green
        4: "#8B5CF6",  # purple
    }

    # 知识点掌握度计算
    knowledge_points = []
    level_dist = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    for r in kp_rows:
        enc = r["encounter_count"] or 0
        cor = r["correct_count"] or 0
        if enc > 0 and cor > 0:
            rate = round(cor / enc * 100, 1)
        elif enc > 0:
            rate = 20.0
        else:
            rate = 0.0

        # 映射到五级
        if rate >= 90:
            lvl = 4
        elif rate >= 70:
            lvl = 3
        elif rate >= 40:
            lvl = 2
        elif enc > 0:
            lvl = 1
        else:
            lvl = 0

        level_dist[lvl] += 1
        knowledge_points.append({
            "topic": r["topic"],
            "level": lvl,
            "level_name": level_names[lvl],
            "level_color": level_colors[lvl],
            "mastery_rate": rate,
            "encounter_count": enc,
            "correct_count": cor,
            "source_file": r["source_file"],
            "document_id": r["document_id"]
        })

    # 文档掌握度
    doc_mastery = []
    for r in doc_rows:
        lvl = calc_mastery_level(r["avg_score"], r["assess_count"], r["status"])
        doc_mastery.append({
            "document_id": r["document_id"],
            "filename": r["filename"],
            "level": lvl,
            "level_name": level_names[lvl],
            "level_color": level_colors[lvl],
            "best_score": round(float(r["best_score"]), 1),
            "avg_score": round(float(r["avg_score"]), 1),
            "assess_count": r["assess_count"],
            "status": r["status"]
        })

    # 薄弱点（L0/L1 知识点）
    weak_points = [kp for kp in knowledge_points if kp["level"] <= 1][:8]

    # 总掌握率
    total_kps = len(knowledge_points)
    if total_kps > 0:
        mastered_kps = level_dist[3] + level_dist[4]
        mastery_rate = round(mastered_kps / total_kps * 100, 1)
    else:
        mastery_rate = 0

    return jsonify({
        "total_docs": total_docs,
        "total_knowledge_points": total_kps,
        "mastery_rate": mastery_rate,
        "study_days": study_days,
        "weak_count": len(weak_points),
        "level_distribution": level_dist,
        "level_names": level_names,
        "level_colors": level_colors,
        "knowledge_points": knowledge_points,
        "doc_mastery": doc_mastery,
        "weak_points": weak_points
    })


@progress_bp.route("/api/study-session", methods=["POST"])
@require_auth
def record_study_session():
    """记录学习时长"""
    data = request.get_json() or {}
    document_id = data.get("document_id")
    session_type = data.get("session_type", "review")
    duration_minutes = data.get("duration_minutes", 0)
    questions = data.get("questions", 0)
    notes = data.get("notes", "")

    if not document_id:
        return jsonify({"error": "缺少 document_id"}), 400
    if duration_minutes <= 0:
        return jsonify({"error": "duration_minutes 必须 > 0"}), 400

    sid = StudySessionDAO.create(
        document_id, session_type=session_type,
        duration=duration_minutes, questions=questions,
        notes=notes, user_id=g.user_id
    )
    return jsonify({"status": "recorded", "session_id": sid})
