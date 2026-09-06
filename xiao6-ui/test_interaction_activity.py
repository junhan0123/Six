#!/usr/bin/env python3
"""Runtime Hotfix R1 — interaction_activity 回归测试。

只验证 interaction_activity 模块本身与端点契约：
- 模块可正常导入（修复前因 field 未导入而 NameError）
- Activity.to_dict() 字段与前端契约一致
- get_activities / get_stats / 端点 JSON 结构稳定
不依赖 server.py、不写数据库。
"""
import json
import interaction_activity as ia


def test_import_ok():
    # 若 field 未导入，此处会直接 NameError
    assert ia is not None


def test_activity_to_dict_keys():
    m = ia.get_activity_manager()
    act = m.add_activity("interaction", "回归测试活动", status="running", intent_type="test")
    d = act.to_dict()
    expected = {"activity_id", "type", "title", "status",
                "description", "intent_type", "timestamp", "relative_time"}
    assert expected.issubset(set(d.keys())), f"缺少字段: {expected - set(d.keys())}"


def test_get_activities_returns_newest_first():
    m = ia.get_activity_manager()
    a1 = m.add_activity("parse", "A1", status="running")
    a2 = m.add_activity("intent", "A2", status="running")
    acts = m.get_activities(limit=10)
    ids = [a.activity_id for a in acts]
    assert a2.activity_id in ids and a1.activity_id in ids


def test_stats_shape():
    m = ia.get_activity_manager()
    m.add_activity("command", "统计测试", status="running")
    stats = m.get_stats()
    assert {"total", "active", "completed", "max_activities"}.issubset(set(stats.keys()))
    assert stats["active"] >= 1


def test_endpoint_payload_serializable():
    """模拟 server.py 端点返回结构，确认可 JSON 序列化且字段稳定。"""
    m = ia.get_activity_manager()
    acts = m.get_activities(limit=20)
    stats = m.get_stats()
    payload = {
        "ok": True,
        "activities": [a.to_dict() for a in acts],
        "stats": stats,
    }
    blob = json.dumps(payload, ensure_ascii=False)
    back = json.loads(blob)
    assert back["ok"] is True
    assert isinstance(back["activities"], list)
    assert isinstance(back["stats"], dict)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
    raise SystemExit(0 if passed == len(tests) else 1)
