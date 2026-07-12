"""逐题评估 - 每道题完成后立即写文件"""
import os, sys, json

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "backend"))
from services.llm_service import LLMService

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_results.json")

def run():
    questions = [
        ("什么是PRD？包含哪些核心部分？", "PRD=产品需求文档，含：背景目标、用户故事、功能需求、非功能需求、优先级、验收标准。"),
        ("什么是MVP？其作用是什么？", "MVP=最小可行产品，核心作用是快速验证假设、降低试错成本、避免过度投入。"),
    ]
    
    llm = LLMService()
    results = []
    
    for i, (q, gt) in enumerate(questions):
        r = {"q": q, "accuracy": 0, "completeness": 0}
        print(f"[{i+1}/{len(questions)}] {q}", flush=True)
        
        try:
            ans = llm._call([
                {"role":"system","content":"你是全科学习助手，准确回答。"},
                {"role":"user","content":q}
            ], max_tokens=400, retries=1)
            
            prompt = f'评估回答:\n问题:{q}\n参考:{gt}\n回答:{ans[:400]}\n对准确性和完整性各打0-10分。只输出JSON:{{"accuracy":8,"completeness":7}}'
            raw = llm._call([
                {"role":"system","content":"只输出JSON。"},
                {"role":"user","content":prompt}
            ], max_tokens=200, retries=1)
            
            raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            s = json.loads(raw)
            r["accuracy"] = s.get("accuracy", 0)
            r["completeness"] = s.get("completeness", 0)
            print(f"  => accuracy={r['accuracy']} completeness={r['completeness']}", flush=True)
        except Exception as e:
            print(f"  ERROR: {e}", flush=True)
        
        results.append(r)
        
        # 每题完后立刻写文件
        acc = sum(x["accuracy"] for x in results) / len(results)
        comp = sum(x["completeness"] for x in results) / len(results)
        tmp = {"accuracy": round(acc,1), "completeness": round(comp,1), "overall": round((acc+comp)/2,1), "details": results}
        with open(OUT, "w") as f:
            json.dump(tmp, f, ensure_ascii=False, indent=2)

    print(f"\n=== 完成 ===")
    print(f"准确性: {tmp['accuracy']}/10  完整性: {tmp['completeness']}/10  综合: {tmp['overall']}/10")
    print(f"结果: {OUT}")

if __name__ == "__main__":
    run()
