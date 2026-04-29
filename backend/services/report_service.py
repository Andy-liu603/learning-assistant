"""
周报生成服务
"""
import os
from datetime import datetime, timedelta
from pathlib import Path
from dateutil import relativedelta
import config
from models.database import (
    ProgressDAO, KnowledgeDAO, StudySessionDAO,
    ReportDAO, DocumentDAO, ConversationDAO
)
from services.claude_service import ClaudeService


class ReportService:
    """学习报告生成"""

    @staticmethod
    def get_week_range(reference_date: datetime = None):
        """获取本周的起止日期（周一到周日）"""
        ref = reference_date or datetime.now()
        # 找到本周一
        monday = ref - timedelta(days=ref.weekday())
        sunday = monday + timedelta(days=6)
        return (
            monday.strftime("%Y-%m-%d 00:00:00"),
            sunday.strftime("%Y-%m-%d 23:59:59")
        )

    @staticmethod
    def generate_weekly_report(user_id=None) -> dict:
        week_start, week_end = ReportService.get_week_range()

        stats = StudySessionDAO.get_week_stats(week_start, week_end, user_id=user_id)
        weak_points = KnowledgeDAO.get_weak_points(limit=10, user_id=user_id)

        from models.database import get_db
        conn = get_db()
        if user_id:
            recent_kp = conn.execute(
                "SELECT DISTINCT topic FROM knowledge_points "
                "WHERE last_encountered_at BETWEEN ? AND ? AND user_id = ? "
                "ORDER BY last_encountered_at DESC LIMIT 10",
                (week_start, week_end, user_id)
            ).fetchall()
        else:
            recent_kp = conn.execute(
                "SELECT DISTINCT topic FROM knowledge_points "
                "WHERE last_encountered_at BETWEEN ? AND ? ORDER BY last_encountered_at DESC LIMIT 10",
                (week_start, week_end)
            ).fetchall()
        conn.close()
        recent_topics = [r["topic"] for r in recent_kp]

        claude = ClaudeService()
        report_content = claude.generate_weekly_report(
            study_stats=stats,
            weak_points=weak_points,
            recent_topics=recent_topics
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"weekly_report_{timestamp}.md"
        file_path = config.REPORT_DIR / filename
        file_path.write_text(report_content, encoding="utf-8")

        report_id = ReportDAO.create(week_start, week_end, report_content, stats, file_path, user_id=user_id)

        return {
            "content": report_content,
            "id": report_id,
            "file_path": str(file_path),
            "week_start": week_start,
            "week_end": week_end,
            "stats": stats
        }

    @staticmethod
    def generate_manual_report(week_start: str, week_end: str, user_id=None) -> dict:
        start = f"{week_start} 00:00:00"
        end = f"{week_end} 23:59:59"

        stats = StudySessionDAO.get_week_stats(start, end, user_id=user_id)
        weak_points = KnowledgeDAO.get_weak_points(limit=10, user_id=user_id)

        from models.database import get_db
        conn = get_db()
        if user_id:
            recent_kp = conn.execute(
                "SELECT DISTINCT topic FROM knowledge_points "
                "WHERE last_encountered_at BETWEEN ? AND ? AND user_id = ? "
                "ORDER BY last_encountered_at DESC LIMIT 10",
                (start, end, user_id)
            ).fetchall()
        else:
            recent_kp = conn.execute(
                "SELECT DISTINCT topic FROM knowledge_points "
                "WHERE last_encountered_at BETWEEN ? AND ? ORDER BY last_encountered_at DESC LIMIT 10",
                (start, end)
            ).fetchall()
        conn.close()
        recent_topics = [r["topic"] for r in recent_kp]

        claude = ClaudeService()
        report_content = claude.generate_weekly_report(
            study_stats=stats,
            weak_points=weak_points,
            recent_topics=recent_topics
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"weekly_report_{timestamp}.md"
        file_path = config.REPORT_DIR / filename
        file_path.write_text(report_content, encoding="utf-8")

        report_id = ReportDAO.create(start, end, report_content, stats, file_path, user_id=user_id)

        return {
            "content": report_content,
            "id": report_id,
            "file_path": str(file_path),
            "week_start": start,
            "week_end": end,
            "stats": stats
        }
