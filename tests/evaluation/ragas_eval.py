"""
RAGAS 评估脚本 - 量化 RAG 管道质量
评估维度：Faithfulness, Answer Relevancy, Context Precision, Context Recall

使用方法：
    python tests/evaluation/ragas_eval.py
    python tests/evaluation/ragas_eval.py --questions tests/evaluation/test_questions.json
    python tests/evaluation/ragas_eval.py --output results.json
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# 项目根目录 + backend 加入 path
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "backend"))

from config import BASE_DIR


# ============================================================
# 1. 数据加载
# ============================================================

def load_test_questions(filepath: str = None) -> List[Dict]:
    """加载测试问题集"""
    if filepath is None:
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_questions.json")

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Test questions file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print(f"[加载] 从 {filepath} 加载了 {len(questions)} 道测试题")
    for q in questions:
        print(f"  [{q['id']}] {q['type']} | {q['difficulty']}: {q['question'][:50]}...")
    return questions


# ============================================================
# 2. RAG Pipeline 调用
# ============================================================

class RAGPipeline:
    """RAG 管道：检索 + 生成"""

    def __init__(self):
        self.vector_store = None
        self.llm_service = None

    def _init_services(self):
        """延迟初始化，避免导入时加载重模型"""
        if self.vector_store is None:
            from backend.services.vector_store import VectorStore
            self.vector_store = VectorStore()
            print("[RAG] VectorStore 初始化完成")

        if self.llm_service is None:
            from backend.services.llm_service import LLMService
            self.llm_service = LLMService()
            print("[RAG] LLMService 初始化完成")

    def retrieve(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """检索阶段：从向量数据库获取相关文档片段"""
        self._init_services()
        results = self.vector_store.search(query, top_k=top_k)
        if not results:
            print(f"  [检索] 未找到相关文档片段 (query: {query[:50]}...)")
        else:
            print(f"  [检索] 返回 {len(results)} 个片段, top similarity: {results[0][1]:.4f}")
        return results

    def generate(self, query: str, context_chunks: List[str]) -> str:
        """生成阶段：基于上下文生成回答"""
        self._init_services()

        if not context_chunks:
            return "（无相关上下文可用）"

        context_text = "\n\n---\n\n".join([
            f"[参考资料 {i+1}]\n{chunk}" for i, chunk in enumerate(context_chunks)
        ])

        prompt = f"""基于以下参考资料回答用户问题。如果资料中包含相关信息，请严格基于资料回答；如果资料中信息不足，请基于你的知识补充，但需明确标注。

参考资料：
{context_text}

用户问题：{query}

请给出准确、简洁的回答。"""

        try:
            answer = self.llm_service._call(
                [{"role": "system", "content": "你是一个专业的学习助手，基于提供的资料回答问题。"},
                 {"role": "user", "content": prompt}],
                max_tokens=1024
            )
            print(f"  [生成] 回答长度: {len(answer)} 字符")
            return answer
        except Exception as e:
            print(f"  [生成] 错误: {e}")
            return f"[生成失败: {e}]"

    def run(self, question: str, top_k: int = 5) -> Dict:
        """
        执行完整 RAG 管道：检索 → 生成

        Returns:
            {
                "question": str,
                "answer": str,
                "contexts": [str, ...],
                "retrieval_scores": [float, ...],
                "time_retrieve_ms": float,
                "time_generate_ms": float,
            }
        """
        t0 = time.time()
        results = self.retrieve(question, top_k=top_k)
        t_retrieve = (time.time() - t0) * 1000

        context_chunks = [chunk for chunk, score in results]
        retrieval_scores = [score for chunk, score in results]

        t1 = time.time()
        answer = self.generate(question, context_chunks)
        t_generate = (time.time() - t1) * 1000

        return {
            "question": question,
            "answer": answer,
            "contexts": context_chunks,
            "retrieval_scores": retrieval_scores,
            "time_retrieve_ms": round(t_retrieve, 2),
            "time_generate_ms": round(t_generate, 2),
        }


# ============================================================
# 3. RAGAS 指标计算（简化实现）
# ============================================================

class RAGASMetrics:
    """
    RAGAS 指标简化实现

    由于 ragas 库未在项目依赖中，此处实现核心指标的简化版本。
    各指标含义与 RAGAS 标准保持一致。
    """

    def __init__(self, llm_service=None):
        self.llm = llm_service

    def _ensure_llm(self):
        """确保 LLM 服务可用"""
        if self.llm is None:
            from backend.services.llm_service import LLMService
            self.llm = LLMService()

    # ── Faithfulness（忠实度） ──
    # 衡量生成答案中有多少内容可以从检索到的上下文中推导出来

    def faithfulness(self, answer: str, contexts: List[str]) -> float:
        """
        计算 Faithfulness（忠实度）

        方法：提取答案中的断言（claims），检查每个断言是否被上下文支持。
        简化版使用 LLM 直接评分。
        """
        if not answer or not contexts:
            return 0.0

        self._ensure_llm()
        context_text = "\n\n".join(contexts)

        prompt = f"""请评估以下 AI 回答相对于参考资料的忠实度。

参考资料：
{context_text[:3000]}

AI 回答：
{answer[:1000]}

请判断 AI 回答中有多少内容可以直接从参考资料中推导或验证。
- 输出一个 0.0 到 1.0 之间的分数
- 1.0 表示所有内容都能在参考资料中找到依据
- 0.0 表示回答完全偏离了参考资料（幻觉）

只输出数字，不要任何其他内容。"""

        try:
            raw = self.llm._call(
                [{"role": "system", "content": "你是一个严格的评估系统。只输出 0.0-1.0 之间的数字。"},
                 {"role": "user", "content": prompt}],
                max_tokens=32,
                retries=1
            )
            return self._parse_score(raw)
        except Exception:
            return self._fallback_faithfulness(answer, contexts)

    def _fallback_faithfulness(self, answer: str, contexts: List[str]) -> float:
        """Faithfulness 降级方案：关键词重叠率"""
        answer_words = set(answer.lower().split())
        context_words = set(" ".join(contexts).lower().split())
        if not answer_words:
            return 0.0
        overlap = answer_words & context_words
        return min(1.0, len(overlap) / len(answer_words) * 1.5)

    # ── Answer Relevancy（回答相关性） ──
    # 衡量生成的回答与原始问题的相关程度

    def answer_relevancy(self, question: str, answer: str) -> float:
        """计算 Answer Relevancy（回答相关性）"""
        if not answer:
            return 0.0

        self._ensure_llm()

        prompt = f"""请评估以下 AI 回答与用户问题的相关性。

用户问题：
{question}

AI 回答：
{answer[:1000]}

请判断这个回答是否切题、是否完整地回答了问题。
- 输出 0.0 到 1.0 之间的分数
- 1.0 表示完全切题且完整
- 0.0 表示答非所问或完全无关

只输出数字，不要任何其他内容。"""

        try:
            raw = self.llm._call(
                [{"role": "system", "content": "你是一个评估系统。只输出 0.0-1.0 之间的数字。"},
                 {"role": "user", "content": prompt}],
                max_tokens=32,
                retries=1
            )
            return self._parse_score(raw)
        except Exception:
            return 0.5  # 无法评估时给中位分

    # ── Context Precision（上下文精确度） ──
    # 衡量检索到的上下文中，有多少是真正与问题相关的

    def context_precision(self, question: str, contexts: List[str]) -> float:
        """
        计算 Context Precision（上下文精确度）

        方法：对每个检索到的上下文片段，判断其与问题的相关性，
        然后按排名位置加权计算 precision@k。
        """
        if not contexts:
            return 0.0

        self._ensure_llm()

        scores = []
        for i, ctx in enumerate(contexts):
            prompt = f"""请判断以下文本片段与用户问题的相关程度。

用户问题：
{question}

文本片段：
{ctx[:500]}

输出 0（不相关）或 1（相关）。只输出数字。"""

            try:
                raw = self.llm._call(
                    [{"role": "system", "content": "你是一个相关性判断系统。只输出 0 或 1。"},
                     {"role": "user", "content": prompt}],
                    max_tokens=8,
                    retries=1
                )
                score = self._parse_score(raw)
                scores.append(score)
            except Exception:
                scores.append(0.0)

        if not scores or sum(scores) == 0:
            return 0.0

        # 加权平均：位置越靠前权重越大
        weighted = sum(s / (i + 1) for i, s in enumerate(scores))
        return weighted / len(scores)

    # ── Context Recall（上下文召回率） ──
    # 衡量 ground truth 中的内容有多少被检索到的上下文覆盖

    def context_recall(self, ground_truth: str, contexts: List[str]) -> float:
        """
        计算 Context Recall（上下文召回率）

        方法：将 ground truth 分解为关键信息点，检查每个信息点
        是否在检索到的上下文中出现。
        """
        if not ground_truth or not contexts:
            return 0.0

        self._ensure_llm()
        context_text = "\n\n".join(contexts)

        prompt = f"""请评估检索到的参考资料对标准答案的覆盖率。

标准答案（ground truth）：
{ground_truth[:1000]}

检索到的参考资料：
{context_text[:3000]}

请判断标准答案中的关键信息有多少能在参考资料中找到。
- 输出 0.0 到 1.0 之间的分数
- 1.0 表示标准答案的所有关键信息都能在参考资料中找到
- 0.0 表示参考资料完全不包含标准答案的信息

只输出数字，不要任何其他内容。"""

        try:
            raw = self.llm._call(
                [{"role": "system", "content": "你是一个评估系统。只输出 0.0-1.0 之间的数字。"},
                 {"role": "user", "content": prompt}],
                max_tokens=32,
                retries=1
            )
            return self._parse_score(raw)
        except Exception:
            return self._fallback_context_recall(ground_truth, contexts)

    def _fallback_context_recall(self, ground_truth: str, contexts: List[str]) -> float:
        """Context Recall 降级方案：n-gram 重叠率"""
        def get_ngrams(text: str, n: int = 3) -> set:
            words = text.lower().split()
            return {" ".join(words[i:i+n]) for i in range(len(words)-n+1)}

        gt_ngrams = get_ngrams(ground_truth)
        ctx_text = " ".join(contexts)
        ctx_ngrams = get_ngrams(ctx_text)

        if not gt_ngrams:
            return 0.0
        return min(1.0, len(gt_ngrams & ctx_ngrams) / len(gt_ngrams))

    # ── 分数解析 ──

    def _parse_score(self, raw: str) -> float:
        """从 LLM 输出中解析 0.0-1.0 的分数"""
        raw = raw.strip()
        # 尝试直接转换为 float
        try:
            score = float(raw)
            return max(0.0, min(1.0, score))
        except ValueError:
            pass
        # 尝试提取数字
        import re
        match = re.search(r'(\d+\.?\d*)', raw)
        if match:
            score = float(match.group(1))
            return max(0.0, min(1.0, score))
        # 兜底
        if "高" in raw or "相关" in raw or "yes" in raw.lower():
            return 0.8
        elif "低" in raw or "不相关" in raw or "no" in raw.lower():
            return 0.2
        return 0.5


# ============================================================
# 4. 评估执行
# ============================================================

def run_evaluation(
    questions: List[Dict],
    top_k: int = 5,
    verbose: bool = True
) -> Dict:
    """
    对测试问题集执行完整的 RAGAS 评估

    Returns:
        包含每个问题和整体汇总的评估结果字典
    """
    pipeline = RAGPipeline()
    metrics = RAGASMetrics()

    results = []
    total = len(questions)

    print(f"\n{'='*60}")
    print(f"  开始评估 - {total} 道测试题")
    print(f"{'='*60}")

    for idx, q in enumerate(questions, 1):
        question = q["question"]
        ground_truth = q["ground_truth"]
        q_type = q.get("type", "unknown")
        q_difficulty = q.get("difficulty", "unknown")

        print(f"\n[{idx}/{total}] Q{q['id']} [{q_type}] [{q_difficulty}]")
        print(f"  Q: {question[:80]}...")

        # 执行 RAG 管道
        rag_result = pipeline.run(question, top_k=top_k)

        # 计算 RAGAS 指标
        print(f"  计算指标...")
        t0 = time.time()

        fa = metrics.faithfulness(rag_result["answer"], rag_result["contexts"])
        ar = metrics.answer_relevancy(question, rag_result["answer"])
        cp = metrics.context_precision(question, rag_result["contexts"])
        cr = metrics.context_recall(ground_truth, rag_result["contexts"])

        eval_time = (time.time() - t0) * 1000

        result = {
            "id": q["id"],
            "question": question[:100],
            "type": q_type,
            "difficulty": q_difficulty,
            "ground_truth": ground_truth[:200],
            "rag_answer": rag_result["answer"][:500],
            "contexts": [c[:200] for c in rag_result["contexts"][:3]],
            "retrieval_scores": rag_result["retrieval_scores"][:3],
            "time_retrieve_ms": rag_result["time_retrieve_ms"],
            "time_generate_ms": rag_result["time_generate_ms"],
            "metrics": {
                "faithfulness": round(fa, 4),
                "answer_relevancy": round(ar, 4),
                "context_precision": round(cp, 4),
                "context_recall": round(cr, 4),
            },
            "eval_time_ms": round(eval_time, 2),
        }

        results.append(result)

        if verbose:
            print(f"  Faithfulness:       {fa:.4f}")
            print(f"  Answer Relevancy:   {ar:.4f}")
            print(f"  Context Precision:  {cp:.4f}")
            print(f"  Context Recall:     {cr:.4f}")
            print(f"  检索耗时: {rag_result['time_retrieve_ms']}ms | "
                  f"生成耗时: {rag_result['time_generate_ms']}ms | "
                  f"评估耗时: {eval_time:.0f}ms")

    # 计算汇总指标
    summary = _compute_summary(results)

    return {
        "eval_metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_questions": total,
            "top_k": top_k,
        },
        "results": results,
        "summary": summary,
    }


def _compute_summary(results: List[Dict]) -> Dict:
    """计算所有题目的汇总统计"""
    if not results:
        return {}

    metrics_keys = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]

    def _avg(vals):
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    def _median(vals):
        if not vals:
            return 0.0
        sorted_vals = sorted(vals)
        n = len(sorted_vals)
        if n % 2 == 1:
            return round(sorted_vals[n // 2], 4)
        return round((sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2, 4)

    overall = {}
    for key in metrics_keys:
        vals = [r["metrics"][key] for r in results]
        overall[key] = {
            "mean": _avg(vals),
            "median": _median(vals),
            "min": round(min(vals), 4),
            "max": round(max(vals), 4),
            "std": round(_std(vals), 4),
        }

    # 按类型分组
    by_type = {}
    for r in results:
        t = r["type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(r)

    type_summary = {}
    for t, items in by_type.items():
        type_summary[t] = {
            "count": len(items),
            "avg_performance": round(_avg([
                sum(r["metrics"][k] for k in metrics_keys) / len(metrics_keys)
                for r in items
            ]), 4),
        }

    # 按难度分组
    by_difficulty = {}
    for r in results:
        d = r["difficulty"]
        if d not in by_difficulty:
            by_difficulty[d] = []
        by_difficulty[d].append(r)

    difficulty_summary = {}
    for d, items in by_difficulty.items():
        difficulty_summary[d] = {
            "count": len(items),
            "avg_performance": round(_avg([
                sum(r["metrics"][k] for k in metrics_keys) / len(metrics_keys)
                for r in items
            ]), 4),
        }

    # 性能统计
    retrieve_times = [r["time_retrieve_ms"] for r in results]
    generate_times = [r["time_generate_ms"] for r in results]

    return {
        "overall_metrics": overall,
        "by_type": type_summary,
        "by_difficulty": difficulty_summary,
        "performance": {
            "avg_retrieve_ms": round(_avg(retrieve_times), 2),
            "avg_generate_ms": round(_avg(generate_times), 2),
            "total_time_ms": round(sum(retrieve_times) + sum(generate_times), 2),
        },
        "ragas_score": round(_avg([
            overall[k]["mean"] for k in metrics_keys
        ]), 4),
    }


def _std(vals: List[float]) -> float:
    """标准偏差"""
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    variance = sum((x - mean) ** 2 for x in vals) / (len(vals) - 1)
    return variance ** 0.5


# ============================================================
# 5. 输出格式化
# ============================================================

def print_report(report: Dict):
    """输出格式化的评估报告（控制台表格）"""
    meta = report["eval_metadata"]
    results = report["results"]
    summary = report["summary"]

    print(f"\n{'='*70}")
    print(f"  RAGAS 评估报告")
    print(f"  评估时间: {meta['timestamp']}")
    print(f"  测试题目数: {meta['total_questions']}")
    print(f"  检索 Top-K: {meta['top_k']}")
    print(f"{'='*70}")

    # ── 逐题详情 ──
    print(f"\n{'─'*70}")
    print(f"  {'ID':<4} {'类型':<10} {'难度':<8} {'Faith':<8} {'Relev':<8} {'CPrec':<8} {'CRecall':<8}")
    print(f"  {'─'*4} {'─'*10} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")

    for r in results:
        m = r["metrics"]
        print(f"  {r['id']:<4} {r['type']:<10} {r['difficulty']:<8} "
              f"{m['faithfulness']:<8.4f} {m['answer_relevancy']:<8.4f} "
              f"{m['context_precision']:<8.4f} {m['context_recall']:<8.4f}")

    # ── 整体汇总 ──
    over = summary["overall_metrics"]
    print(f"\n{'─'*70}")
    print(f"  【整体汇总】")
    print(f"{'─'*70}")
    print(f"  {'指标':<22} {'均值':<10} {'中位数':<10} {'最小值':<10} {'最大值':<10} {'标准差':<10}")
    print(f"  {'─'*22} {'─'*10} {'─'*10} {'─'*10} {'─'*10} {'─'*10}")

    label_map = {
        "faithfulness": "Faithfulness",
        "answer_relevancy": "Answer Relevancy",
        "context_precision": "Context Precision",
        "context_recall": "Context Recall",
    }
    for key, label in label_map.items():
        s = over[key]
        print(f"  {label:<22} {s['mean']:<10.4f} {s['median']:<10.4f} "
              f"{s['min']:<10.4f} {s['max']:<10.4f} {s['std']:<10.4f}")

    # ── RAGAS 综合分 ──
    print(f"\n  {'─'*70}")
    print(f"  RAGAS 综合得分: {summary['ragas_score']:.4f}")
    print(f"  {'─'*70}")

    # ── 按类型/难度分组 ──
    print(f"\n  【按题目类型】")
    for t, s in summary["by_type"].items():
        print(f"    {t:<15}: {s['count']} 题, 平均表现 {s['avg_performance']:.4f}")

    print(f"\n  【按难度】")
    for d, s in summary["by_difficulty"].items():
        print(f"    {d:<15}: {s['count']} 题, 平均表现 {s['avg_performance']:.4f}")

    # ── 性能 ──
    perf = summary["performance"]
    print(f"\n  【性能统计】")
    print(f"    平均检索耗时: {perf['avg_retrieve_ms']:.0f}ms")
    print(f"    平均生成耗时: {perf['avg_generate_ms']:.0f}ms")
    print(f"    总耗时:       {perf['total_time_ms']:.0f}ms")

    # ── 诊断建议 ──
    print(f"\n  【诊断建议】")
    diag = _diagnose(summary)
    for line in diag:
        print(f"    {line}")

    print(f"\n{'='*70}\n")


def _diagnose(summary: Dict) -> List[str]:
    """根据评估结果生成诊断建议"""
    tips = []
    over = summary["overall_metrics"]

    fa_mean = over["faithfulness"]["mean"]
    ar_mean = over["answer_relevancy"]["mean"]
    cp_mean = over["context_precision"]["mean"]
    cr_mean = over["context_recall"]["mean"]

    if fa_mean < 0.6:
        tips.append(f"[!] Faithfulness 偏低 ({fa_mean:.2f})：存在幻觉风险，建议优化 retrieval top_k 或 prompt 设计")
    elif fa_mean >= 0.85:
        tips.append(f"[+] Faithfulness 优秀 ({fa_mean:.2f})：回答忠实于参考资料")

    if ar_mean < 0.6:
        tips.append(f"[!] Answer Relevancy 偏低 ({ar_mean:.2f})：回答不够切题，建议优化生成 prompt 强调问答匹配")
    elif ar_mean >= 0.85:
        tips.append(f"[+] Answer Relevancy 优秀 ({ar_mean:.2f})：回答与问题高度相关")

    if cp_mean < 0.6:
        tips.append(f"[!] Context Precision 偏低 ({cp_mean:.2f})：检索返回了过多不相关内容，建议调整 chunk_size 或 embedding 模型")
    elif cp_mean >= 0.85:
        tips.append(f"[+] Context Precision 优秀 ({cp_mean:.2f})：检索结果非常精确")

    if cr_mean < 0.6:
        tips.append(f"[!] Context Recall 偏低 ({cr_mean:.2f})：检索遗漏了关键信息，建议增加 top_k 或优化分块策略")
    elif cr_mean >= 0.85:
        tips.append(f"[+] Context Recall 优秀 ({cr_mean:.2f})：检索覆盖了大部分关键信息")

    if fa_mean >= 0.85 and ar_mean >= 0.85 and cp_mean >= 0.85 and cr_mean >= 0.85:
        tips.append("[+] 四项指标均优秀，RAG 管道质量很高！")

    if fa_mean < 0.5 and cp_mean < 0.5 and cr_mean < 0.5:
        tips.append("[!] 多项指标偏低，建议检查向量数据库是否已入库测试相关的文档")

    return tips


def save_report(report: Dict, output_path: str):
    """保存评估结果到 JSON 文件"""
    # 移除过长文本以减小文件体积
    compact = {
        "eval_metadata": report["eval_metadata"],
        "summary": report["summary"],
        "results": [],
    }
    for r in report["results"]:
        compact["results"].append({
            "id": r["id"],
            "type": r["type"],
            "difficulty": r["difficulty"],
            "question": r["question"],
            "rag_answer_short": r["rag_answer"][:200],
            "metrics": r["metrics"],
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(compact, f, ensure_ascii=False, indent=2)
    print(f"[结果] 已保存到 {os.path.abspath(output_path)}")


# ============================================================
# 6. 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="RAGAS 评估脚本 - 量化 RAG 管道质量")
    parser.add_argument(
        "--questions", "-q",
        default=None,
        help="测试问题 JSON 文件路径（默认: tests/evaluation/test_questions.json）"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="评估结果输出 JSON 文件路径（默认: 自动生成时间戳文件名）"
    )
    parser.add_argument(
        "--top-k", "-k",
        type=int, default=5,
        help="检索返回的文档片段数量（默认: 5）"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="静默模式，不输出逐题详情"
    )
    parser.add_argument(
        "--only", "-n",
        type=int, default=None,
        help="仅评估前 N 道题"
    )

    args = parser.parse_args()

    # 加载测试题
    questions_path = args.questions
    questions = load_test_questions(questions_path)

    if args.only:
        questions = questions[:args.only]
        print(f"[限制] 仅评估前 {args.only} 道题")

    # 执行评估
    report = run_evaluation(questions, top_k=args.top_k, verbose=not args.quiet)

    # 输出报告
    print_report(report)

    # 保存结果
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"ragas_results_{timestamp}.json"
        )
    save_report(report, output_path)

    return report


if __name__ == "__main__":
    main()
