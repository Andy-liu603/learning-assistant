"""
RAG 质量评估脚本（简化版 — 不依赖 ragas 库）
直接使用 LLM 评判回答质量
"""
import os, sys, json, time

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "backend"))

from config import BASE_DIR


def load_questions():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_questions.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def call_llm(prompt):
    """直接调用 LLM"""
    from services.llm_service import LLMService
    llm = LLMService()
    return llm._call(
        [{"role": "system", "content": "你是一个专业的评估专家。只输出 JSON，不要任何额外内容。"},
         {"role": "user", "content": prompt}],
        max_tokens=1024, retries=2
    )


def score_answer(question, ground_truth, llm_answer):
    """用 LLM 评分单项回答"""
    prompt = f"""请评估以下回答的质量。

问题：{question}

参考答案（Ground Truth）：{ground_truth}

LLM 回答：{llm_answer}

请从以下维度评分（0-10 分）：
- accuracy：回答的事实准确性
- completeness：回答是否覆盖了参考答案的关键要点
- relevance：回答与问题的相关性

输出 JSON 格式：
{{"accuracy": 8, "completeness": 7, "relevance": 9, "comment": "一句话总评"}}

只输出 JSON。"""
    try:
        raw = call_llm(prompt)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0] if "```" in raw else raw
        return json.loads(raw)
    except Exception as e:
        return {"accuracy": 0, "completeness": 0, "relevance": 0, "comment": f"评分失败: {e}"}


def generate_answer(question):
    """用学习助手 LLM 生成回答"""
    prompt = f"""请回答以下问题。回答要准确、完整、有结构。

问题：{question}

请直接给出你的回答。"""
    from services.llm_service import LLMService
    llm = LLMService()
    return llm._call(
        [{"role": "system", "content": "你是一个全科全能个人学习助手。请准确、结构化地回答用户问题。"},
         {"role": "user", "content": prompt}],
        max_tokens=2048, retries=2
    )


def main():
    questions = load_questions()
    print(f"\n{'='*60}")
    print(f"  RAG 回答质量评估 — {len(questions)} 道题")
    print(f"{'='*60}\n")

    results = []
    scores = {"accuracy": [], "completeness": [], "relevance": []}

    for i, q in enumerate(questions):
        print(f"[{i+1}/{len(questions)}] {q['question'][:50]}... ({q['type']}/{q['difficulty']})")

        try:
            answer = generate_answer(q["question"])
            score = score_answer(q["question"], q["ground_truth"], answer)

            for k in ["accuracy", "completeness", "relevance"]:
                scores[k].append(score.get(k, 0))

            print(f"     accuracy={score.get('accuracy',0)} completeness={score.get('completeness',0)} relevance={score.get('relevance',0)}")
            results.append({"id": q["id"], **score, "answer_preview": answer[:100]})

        except Exception as e:
            print(f"     ERROR: {e}")
            for k in ["accuracy", "completeness", "relevance"]:
                scores[k].append(0)

        time.sleep(0.5)

    print(f"\n{'='*60}")
    print(f"  评估结果汇总")
    print(f"{'='*60}")

    for k in ["accuracy", "completeness", "relevance"]:
        vals = scores[k]
        avg = sum(vals) / len(vals) if vals else 0
        print(f"  {k:15s}: avg={avg:.1f}/10  min={min(vals)}  max={max(vals)}")

    overall = sum(sum(v) for v in scores.values()) / (len(scores) * len(questions)) if questions else 0
    print(f"\n  综合评分: {overall:.1f}/10")

    report = {
        "total_questions": len(questions),
        "average_scores": {k: round(sum(v)/len(v), 1) if v else 0 for k, v in scores.items()},
        "overall_score": round(overall, 1),
        "details": results
    }

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果: {out_path}")


if __name__ == "__main__":
    main()
