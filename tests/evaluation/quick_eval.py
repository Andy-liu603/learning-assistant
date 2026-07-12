"""快速 RAG 回答质量评估 — 直接调用 LLM 评分"""
import os, sys, json, time

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "backend"))

from services.llm_service import LLMService

# 测试题
questions = [
    ("什么是产品需求文档（PRD）？它通常包含哪些核心部分？",
     "PRD是产品需求文档，核心部分包括：背景目标、用户故事、功能需求、非功能需求、优先级、验收标准。"),
    ("请解释MVP的概念，并说明它在产品开发中的作用。",
     "MVP是最小可行产品，作用是快速验证核心假设、降低试错成本，避免过度投入未经验证的功能。"),
    ("什么是A/B测试？在什么情况下不适合使用？",
     "A/B测试是将用户随机分为两组，对比不同方案的效果差异。样本量不足、测试周期过短、或存在网络效应时不适用。"),
    ("什么是向量数据库？在RAG系统中为什么需要它？",
     "向量数据库存储和检索高维向量，在RAG中用于语义相似度搜索，将用户问题转化为向量后检索最相关的文档片段。"),
]

llm = LLMService()
scores = []

print("=" * 50)
print(f"  RAG 回答质量评估 — {len(questions)} 道题")
print("=" * 50)
print()

for i, (q, gt) in enumerate(questions):
    print(f"[{i+1}/{len(questions)}] {q[:45]}...", flush=True)
    try:
        # 生成回答
        ans = llm._call([
            {"role": "system", "content": "你是全科学习助手。请准确、简洁地回答。"},
            {"role": "user", "content": q}
        ], max_tokens=512, retries=1)

        # LLM 评分
        score_prompt = (
            "评估以下回答的质量。\n\n"
            f"问题：{q}\n\n"
            f"参考答案：{gt}\n\n"
            f"LLM回答：{ans[:500]}\n\n"
            "对准确性(accuracy)和完整性(completeness)各打0-10分。\n"
            '输出JSON：{"accuracy":8,"completeness":7}'
        )
        raw = llm._call([
            {"role": "system", "content": "只输出 JSON，不要额外内容。"},
            {"role": "user", "content": score_prompt}
        ], max_tokens=256, retries=1)

        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if "```" in raw:
                raw = raw.rsplit("```", 1)[0]
        s = json.loads(raw)
        scores.append(s)
        print(f"  accuracy={s.get('accuracy',0)} completeness={s.get('completeness',0)}", flush=True)
    except Exception as e:
        print(f"  ERROR: {e}", flush=True)
        scores.append({"accuracy": 0, "completeness": 0})
    time.sleep(0.5)

acc = sum(s.get("accuracy", 0) for s in scores) / len(scores)
comp = sum(s.get("completeness", 0) for s in scores) / len(scores)
overall = round((acc + comp) / 2, 1)

print()
print("=" * 50)
print("  评估结果汇总")
print("=" * 50)
print(f"  准确性 (accuracy):     {acc:.1f}/10")
print(f"  完整性 (completeness): {comp:.1f}/10")
print(f"  综合评分:             {overall}/10")
print()

result = {
    "total_questions": len(questions),
    "accuracy": round(acc, 1),
    "completeness": round(comp, 1),
    "overall": overall,
    "details": scores
}

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_results.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"详细结果已保存: {out_path}")
