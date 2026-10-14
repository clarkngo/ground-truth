from groundtruth import agent, ollama
from groundtruth.chunking import Chunk
from groundtruth.config import RunConfig
from groundtruth.retrieval import Hit


def _hit(id):
    return Hit(Chunk(id, id.split("#")[0], "t", "", "x"), 1.0)


def test_interleave_keeps_every_sub_question_under_the_cap():
    a = [_hit(f"a#{i}") for i in range(4)]
    b = [_hit(f"b#{i}") for i in range(4)]
    c = [_hit(f"c#{i}") for i in range(4)]
    pooled = agent.interleave([a, b, c], 5)
    assert [h.chunk.id for h in pooled] == ["a#0", "b#0", "c#0", "a#1", "b#1"]


def test_planner_falls_back_to_direct_on_bad_json(monkeypatch):
    monkeypatch.setattr(ollama, "chat", lambda *a, **k: ollama.Completion("not json", 1, 1, 1.0))
    subs, _ = agent.plan("q", RunConfig(name="t"))
    assert subs == []


def test_planner_needs_at_least_two_sub_questions(monkeypatch):
    reply = '{"route": "decompose", "sub_questions": ["only one"]}'
    monkeypatch.setattr(ollama, "chat", lambda *a, **k: ollama.Completion(reply, 1, 1, 1.0))
    assert agent.plan("q", RunConfig(name="t"))[0] == []
