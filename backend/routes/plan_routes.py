"""
学习计划路由 - AI 生成结构化学习计划
"""
import json
from flask import Blueprint, jsonify, request, g
from backend.middleware.auth import require_auth
from backend.models.database import get_db
from backend.utils.logger import log

plan_bp = Blueprint("plan", __name__, url_prefix="/api/plans")


@plan_bp.route("/generate", methods=["POST"])
@require_auth
def generate_plan():
    """生成学习计划
    ---
    tags:
      - 学习计划
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            topic:
              type: string
            duration_days:
              type: integer
            current_level:
              type: string
            daily_hours:
              type: integer
    """
    user_id = g.user_id
    data = request.get_json(silent=True) or {}
    topic = data.get("topic", "未指定主题")
    duration_days = int(data.get("duration_days", 7))
    current_level = data.get("current_level", "beginner")
    daily_hours = int(data.get("daily_hours", 1))

    try:
        from services.llm_service import LLMService
        llm = LLMService()
        prompt = f"""请为以下学习需求生成一个 {duration_days} 天的结构化学习计划。

主题：{topic}
当前水平：{current_level}
每天可用时间：{daily_hours} 小时

要求：
1. 每天安排 2-3 个具体的学习任务
2. 任务粒度适中（20-60分钟/个）
3. 循序渐进，前三天打基础，中段深入，末段综合
4. 包含每天的学习目标和推荐资源类型

输出 JSON 格式：
{{
  "topic": "{topic}",
  "overview": "一句学习目标概述",
  "days": [
    {{
      "day": 1,
      "title": "当天学习主题",
      "goal": "学习目标",
      "tasks": ["任务1", "任务2"],
      "resources": "推荐资源类型，如教材/视频/论文/实践"
    }}
  ]
}}

只输出 JSON，不要任何额外内容。"""
        raw = llm._call(
            [{"role": "system", "content": "你是一个专业的学习规划师，擅长将复杂的学习目标拆解为每日可执行任务。只输出 JSON。"},
             {"role": "user", "content": prompt}],
            max_tokens=4096
        )
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0] if "```" in raw else raw
        plan_data = json.loads(raw)

        # 存储计划
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO study_plans (topic, duration_days, current_level, daily_hours, content, progress, status, user_id, source) "
                "VALUES (?, ?, ?, ?, ?, '{}', 'active', ?, 'manual')",
                (topic, duration_days, current_level, daily_hours, json.dumps(plan_data, ensure_ascii=False), user_id)
            )
            conn.commit()
            plan_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            plan_data["id"] = plan_id
            plan_data["status"] = "active"
            return jsonify({"plan": plan_data})
        finally:
            conn.close()

    except json.JSONDecodeError as e:
        log.error(f"学习计划 JSON 解析失败: {e}")
        return jsonify({"error": "计划生成失败，请重试"}), 500
    except Exception as e:
        log.error(f"学习计划生成失败: {e}")
        return jsonify({"error": str(e)}), 500


@plan_bp.route("/list", methods=["GET"])
@require_auth
def list_plans():
    """获取学习计划列表
    ---
    tags:
      - 学习计划
    """
    user_id = g.user_id
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, topic, duration_days, current_level, daily_hours, status, created_at "
            "FROM study_plans WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        plans = [{
            "id": r["id"],
            "topic": r["topic"],
            "duration_days": r["duration_days"],
            "current_level": r["current_level"],
            "daily_hours": r["daily_hours"],
            "status": r["status"],
            "created_at": r["created_at"]
        } for r in rows]
        return jsonify({"plans": plans})
    finally:
        conn.close()


@plan_bp.route("/<int:plan_id>", methods=["GET"])
@require_auth
def get_plan(plan_id):
    """获取学习计划详情
    ---
    tags:
      - 学习计划
    """
    user_id = g.user_id
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM study_plans WHERE id = ? AND user_id = ?",
            (plan_id, user_id)
        ).fetchone()
        if not row:
            return jsonify({"error": "计划不存在"}), 404

        plan = {
            "id": row["id"],
            "topic": row["topic"],
            "duration_days": row["duration_days"],
            "current_level": row["current_level"],
            "daily_hours": row["daily_hours"],
            "status": row["status"],
            "source": row["source"],
            "created_at": row["created_at"]
        }
        try:
            plan["content"] = json.loads(row["content"])
        except:
            plan["content"] = {}
        try:
            plan["progress"] = json.loads(row["progress"])
        except:
            plan["progress"] = {}

        return jsonify({"plan": plan})
    finally:
        conn.close()


@plan_bp.route("/<int:plan_id>/progress", methods=["PUT"])
@require_auth
def update_progress(plan_id):
    """更新学习计划进度
    ---
    tags:
      - 学习计划
    """
    user_id = g.user_id
    data = request.get_json(silent=True) or {}
    day = str(data.get("day", ""))
    completed = bool(data.get("completed", False))

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT progress FROM study_plans WHERE id = ? AND user_id = ?",
            (plan_id, user_id)
        ).fetchone()
        if not row:
            return jsonify({"error": "计划不存在"}), 404

        progress = json.loads(row["progress"]) if row["progress"] else {}
        progress[day] = completed

        conn.execute(
            "UPDATE study_plans SET progress = ? WHERE id = ?",
            (json.dumps(progress), plan_id)
        )
        conn.commit()
        return jsonify({"progress": progress})
    finally:
        conn.close()
