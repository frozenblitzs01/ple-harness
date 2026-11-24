"""Stub verification for the serve.py agent-loop fix (design 2026-11-24, section 6).
No network, no API key, no Codespace services: drives serve.solve() with
scripted model replies and an in-memory fake container (dict filesystem).
Run: python3 serve-loop-fix-test.py
"""
import asyncio
import json
import os
import sys

os.environ.setdefault("MODEL_NAME", "qwen-flash-character")
os.environ.setdefault("OPENAI_API_KEY", "test-dummy")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import openai  # noqa: F401
except ImportError:
    import types as _types
    _fake_openai = _types.ModuleType("openai")
    class _APIError(Exception):
        pass
    class _AsyncOpenAI:
        def __init__(self, *args, **kwargs):
            pass
    _fake_openai.AsyncOpenAI = _AsyncOpenAI
    _fake_openai.APIError = _APIError
    sys.modules["openai"] = _fake_openai

import serve


class FakeSession:
    def __init__(self, instruction, workdir="/app/files", time_left=21600, fail_probe=False):
        self.instruction = instruction
        self.workdir = workdir
        self.final_message = None
        self._time_left = time_left
        self._fail_probe = fail_probe
        self.fs = {}
        self.mtime = {}
        self._clock = 1000
        self.logs = []
        self.usage_calls = []

    def time_left(self):
        return self._time_left

    async def log(self, text):
        self.logs.append(text)

    async def usage(self, *args):
        self.usage_calls.append(args)

    def _key(self, path):
        if path.startswith("/"):
            return path
        return self.workdir.rstrip("/") + "/" + path

    async def exec(self, cmd, timeout_sec=None):
        if self._fail_probe and "GATE_FILE" in cmd:
            raise RuntimeError("probe boom")
        out = []
        if "GATE_FILE" in cmd or "GATE_DIR" in cmd:
            import re as _re
            for line in cmd.splitlines():
                m = _re.search(r"GATE_FILE (\d+)", line)
                if m:
                    pm = _re.search(r"\[ -f '?([^'\s\]]+)'?", line)
                    p = pm.group(1) if pm else ""
                    key = p if p in self.fs else self._key(p)
                    if key in self.fs:
                        out.append(f"GATE_FILE {m.group(1)} OK {len(self.fs[key])} {self.mtime[key]}")
                    else:
                        out.append(f"GATE_FILE {m.group(1)} NO")
                    continue
                m = _re.search(r"GATE_DIR (\d+)", line)
                if m:
                    pm = _re.search(r"\[ -d '?([^'\s\]]+)'?", line)
                    p = pm.group(1) if pm else ""
                    prefix = p if p.startswith("/") else self.workdir.rstrip("/") + "/" + p
                    files = sorted(k for k in self.fs if k == prefix or k.startswith(prefix.rstrip("/") + "/"))
                    if files:
                        out.append(f"GATE_DIR {m.group(1)} OK")
                        for k in files:
                            out.append(f"{k}|{len(self.fs[k])}|{self.mtime[k]}")
                        out.append(f"GATE_DIR_END {m.group(1)}")
                    else:
                        out.append(f"GATE_DIR {m.group(1)} NO")
                    continue
            return {"exit_code": 0, "output": "\n".join(out) + "\n", "truncated": False, "timed_out": False}
        stripped = cmd.strip()
        if stripped == "echo ok":
            return {"exit_code": 0, "output": "ok\n", "truncated": False, "timed_out": False}
        if stripped == "ls":
            return {"exit_code": 0, "output": "\n".join(sorted(self.fs)) + "\n", "truncated": False, "timed_out": False}
        if stripped.startswith("cat "):
            key = self._key(stripped[4:].strip())
            return {"exit_code": 0, "output": self.fs.get(key, ""), "truncated": False, "timed_out": False}
        return {"exit_code": 0, "output": "", "truncated": False, "timed_out": False}

    async def read_file(self, path):
        return self.fs.get(self._key(path), "")

    async def write_file(self, path, content):
        key = self._key(path)
        self._clock += 1
        self.fs[key] = content if isinstance(content, str) else content.decode()
        self.mtime[key] = self._clock
        return f"Wrote {len(self.fs[key])} bytes to {path}"


class FakeMsg:
    def __init__(self, content=None, tool_calls=None, finish_reason="stop"):
        self.content = content
        self.tool_calls = tool_calls
        self.finish_reason = finish_reason

    def model_dump(self, exclude_none=False):
        d = {"role": "assistant", "content": self.content}
        if self.tool_calls is not None:
            d["tool_calls"] = self.tool_calls
        if exclude_none and self.content is None:
            d.pop("content", None)
        return d


def tool_call(call_id, name, args):
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


class FakeResp:
    def __init__(self, msg):
        self.choices = [type("Choice", (), {"message": msg, "finish_reason": msg.finish_reason})()]
        self.usage = None


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0
        self.last_messages = None
        self.chat = self
        self.completions = self

    async def create(self, **kwargs):
        self.calls += 1
        self.last_messages = kwargs.get("messages")
        idx = min(self.calls - 1, len(self.replies) - 1)
        return FakeResp(self.replies[idx])


def text_reply(text):
    return FakeMsg(content=text, tool_calls=None)


def run_scenario(coro):
    return asyncio.run(coro)


ERROR_TEXT = ("Error: Empty parameters received; each tool call must include a valid "
              "JSON object with keys functionName, properties, and optional returnType. "
              "Did you paste the request incorrectly?")


def scenario_1():
    instruction = "Design the roof deck. Write your answer to `output/submission.zip`."
    summary = "Done. Deliverable: output/submission.zip with the roof deck design."
    replies = [
        text_reply("Done. The roof deck design is complete."),
        FakeMsg(content="", tool_calls=[tool_call("c1", "write_file", {"path": "output/submission.zip", "content": "ZIPDATA"})]),
        text_reply(summary),
    ]
    client = FakeClient(replies)
    serve.client = client
    session = FakeSession(instruction)
    result = run_scenario(serve.solve(session))
    assert result == summary, result
    assert session.final_message == summary
    assert "/app/files/output/submission.zip" in session.fs, session.fs
    assert client.calls == 3, client.calls
    print("scenario 1 (text-only done, no deliverable -> gated, then delivered): PASS")


def scenario_2():
    instruction = "Design the roof deck. Write your answer to `output/submission.zip`."
    summary = "Done. Deliverable: output/submission.zip."
    replies = [
        text_reply(ERROR_TEXT),
        FakeMsg(content="", tool_calls=[tool_call("c1", "bash", {"command": "echo ok"})]),
        FakeMsg(content="", tool_calls=[tool_call("c2", "write_file", {"path": "output/submission.zip", "content": "ZIPDATA"})]),
        text_reply(summary),
    ]
    client = FakeClient(replies)
    serve.client = client
    session = FakeSession(instruction)
    result = run_scenario(serve.solve(session))
    assert result == summary, result
    assert session.final_message == summary
    assert ERROR_TEXT not in (session.final_message or "")
    assert "/app/files/output/submission.zip" in session.fs
    print("scenario 2 (malformed tool call -> retried, not fatal): PASS")


def scenario_3():
    instruction = "Size the LV cables. Write your answer to `output/submission.zip`."
    fake = ("I will size the cables. bash(command='ls')\nRESULT\noutput\n"
            "bash(command='cat sizing.py')\nRESULT\ncode here\n"
            "I wrote output/submission.zip with the sized cables.")
    summary = "Done. Deliverable: output/submission.zip."
    replies = [
        text_reply(fake),
        FakeMsg(content="", tool_calls=[tool_call("c1", "write_file", {"path": "output/submission.zip", "content": "ZIPDATA"})]),
        text_reply(summary),
    ]
    client = FakeClient(replies)
    serve.client = client
    session = FakeSession(instruction)
    result = run_scenario(serve.solve(session))
    assert result == summary, result
    assert session.final_message == summary
    assert "/app/files/output/submission.zip" in session.fs
    assert any(m.get("role") == "user" and "shows tool calls as text" in m.get("content", "") for m in (client.last_messages or [])), client.last_messages
    print("scenario 3 (fabricated transcript -> rejected, real tool call follows): PASS")


def scenario_4():
    instruction = "Validate the fire test. Save the files that make up your answer under `output/`."
    hallucinated = ("I have completed the analysis and generated the required deliverables "
                    "under `/app/workspace/output`. Deliverables: validation_memo.docx, "
                    "error_calculation.txt, rework_recommendations.md. Governing criterion "
                    "achieved in test: 48 min; in simulation: 46 min. Error: -4%.")
    replies = [text_reply(hallucinated)]
    client = FakeClient(replies)
    serve.client = client
    session = FakeSession(instruction)
    result = run_scenario(serve.solve(session))
    assert result.startswith("The run ended without a deliverable on disk."), result
    assert session.final_message == result
    assert "validation_memo" not in result, result
    assert not session.fs, session.fs
    print("scenario 4 (hallucinated completion -> honest end, no deliverable): PASS")


SMOKE_INSTRUCTION = ("Create a file named `hello.txt` in the current working directory "
                    "(`/app`) whose entire content is the single line: HELLO. Do not create "
                    "any other files. When the file exists, reply with the word done and stop.")


def scenario_5():
    files, dirs = serve.deliverable_candidates(SMOKE_INSTRUCTION)
    assert "hello.txt" in files, files
    replies = [
        FakeMsg(content="", tool_calls=[tool_call("c1", "write_file", {"path": "hello.txt", "content": "HELLO"})]),
        text_reply("done"),
    ]
    client = FakeClient(replies)
    serve.client = client
    session = FakeSession(SMOKE_INSTRUCTION, workdir="/app")
    result = run_scenario(serve.solve(session))
    assert result == "done", result
    assert session.final_message == "done"
    assert session.fs.get("/app/hello.txt") == "HELLO", session.fs
    print("scenario 5 (smoke regression: hello.txt parsed from instruction): PASS")


def scenario_6():
    instruction = "Validate the fire test. Save the files that make up your answer under `output/`."
    replies = [text_reply("I have completed the analysis. Deliverables are in output/.")]
    client = FakeClient(replies)
    serve.client = client
    session = FakeSession(instruction, time_left=100)
    result = run_scenario(serve.solve(session))
    assert result.startswith("The run ended without a deliverable on disk."), result
    assert client.calls == 1, client.calls
    print("scenario 6 (wrap-up with missing deliverable -> prompt honest return): PASS")


def scenario_7():
    instruction = "Design the roof deck. Write your answer to `output/submission.zip`."
    summary = "Done. Deliverable: output/submission.zip with the roof deck design."
    replies = [text_reply(summary)]
    client = FakeClient(replies)
    serve.client = client
    session = FakeSession(instruction, fail_probe=True)
    result = run_scenario(serve.solve(session))
    assert summary in result, result
    assert not result.startswith("The run ended without a deliverable")
    assert session.final_message == result
    assert any("deliverable gate unknown" in m for m in session.logs), session.logs
    print("scenario 7 (unknown gate fails open, logged): PASS")


if __name__ == "__main__":
    scenario_1()
    scenario_2()
    scenario_3()
    scenario_4()
    scenario_5()
    scenario_6()
    scenario_7()
    print("ALL STUB SCENARIOS PASSED")
