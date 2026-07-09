"""性能基准测试 — API 延迟"""
import json, os, sys, time, statistics

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "backend"))
os.chdir(_ROOT)

from backend.app import create_app


def benchmark_endpoint(client, method, path, headers=None, data=None, iterations=5):
    """对端点进行多次调用并返回延迟统计"""
    times = []
    statuses = []
    for _ in range(iterations):
        start = time.perf_counter()
        if method == "GET":
            resp = client.get(path, headers=headers)
        elif method == "POST":
            resp = client.post(path, json=data, headers=headers)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        statuses.append(resp.status_code)
    return {
        "path": path,
        "method": method,
        "min_ms": round(min(times), 1),
        "max_ms": round(max(times), 1),
        "avg_ms": round(statistics.mean(times), 1),
        "p95_ms": round(sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else max(times), 1),
        "status_codes": list(set(statuses))
    }


def main():
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    # 注册并获取 token
    client.post("/api/auth/register", json={
        "username": "perftest", "email": "perf@test.com", "password": "perf123456"
    })
    login = client.post("/api/auth/login", json={
        "username": "perftest", "password": "perf123456"
    })
    token = login.get_json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    benchmarks = [
        ("GET", "/api/health", None, None),
        ("GET", "/api/documents", headers, None),
        ("GET", "/api/dashboard/overview", headers, None),
        ("POST", "/api/auth/login", None, {"username": "perftest", "password": "perf123456"}),
    ]

    targets = {
        "/api/health": 50,
        "/api/documents": 200,
        "/api/dashboard/overview": 300,
        "/api/auth/login": 500,
    }

    results = []
    print(f"{'='*60}")
    print(f"  性能基准测试")
    print(f"{'='*60}")
    print()

    for method, path, h, data in benchmarks:
        result = benchmark_endpoint(client, method, path, headers=h, data=data)
        results.append(result)
        target = targets.get(path, 999)
        status = "PASS" if result["avg_ms"] <= target else "FAIL"
        print(f"  [{status}] {method} {path}")
        print(f"        avg={result['avg_ms']}ms  min={result['min_ms']}ms  max={result['max_ms']}ms  p95={result['p95_ms']}ms  target<{target}ms")
        print()

    all_pass = all(r["avg_ms"] <= targets.get(r["path"], 999) for r in results)
    print(f"  整体结果: {'全部通过' if all_pass else '存在不达标端点'}")
    print()

    # 保存结果
    out_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "perf_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"results": results, "all_pass": all_pass}, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存: {out_path}")


if __name__ == "__main__":
    main()
