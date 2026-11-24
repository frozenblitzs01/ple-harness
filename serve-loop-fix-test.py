"""Local verification for the serve.py deliverable gate (no model, no network).

Drives serve.solve() with scripted model replies and a FakeSession backed by
a real temp directory (so the gate's bash probe runs for real), plus direct
unit tests of deliverable_candidates() / deliverable_gate().

Run: /tmp/ple-test-venv/bin/python serve-loop-fix-test.py
Exit 0 = all scenarios pass.
"""

import asyncio
import os
import subprocess
import sys
import tempfile

os.environ.setdefault("MODEL_NAME", "openai-compatible/qwen-flash-character")
os.environ.setdefault("OPENAI_API_KEY", "test")

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HARNESS_DIR)

import serve  # noqa: E402
import taskbridge  # noqa: E402

SMOKE = (
    "Create a file named `hello.txt` in the current working directory (`/app`)"
    " whose entire content is the single line:\n\nHELLO\n\nDo not create any"
    " other files. When the file exists, reply with the word done and stop."
)

EVAL1_ERROR = (
    "Error: Empty parameters received; each tool call must include a valid"
    " JSON object with keys functionName, properties, and optional"
    " returnType. Did you paste the request incorrectly?"
)

FABRICATED = (
    "Done. I ran the analysis:\n"
    "bash(ls -la output/)\n"
    "Tool result: total 0\n"
    "bash(python3 build.py)\n"
    "RESULT: exit code 0\n"
    "I wrote output/submission.zip and verified it. Summary: all checks pass."
)

HALLUCINATED = (
    "Done. I created validation_memo.docx, error_calculation.txt and"
    " rework_recommendations.md in output/. The fire test ran 48 minutes,"
    " the simulation 46 minutes, error -4%. No rework needed."
)


# ---------------------------------------------------------------- fakes

class FakeMessage:
  def __init__(self, content=None, tool_calls=None, finish_reason="stop"):
    self.content = content
    self.tool_calls = tool_calls or []
    self.finish_reason = finish_reason

  def model_dump(self, exclude_none=True):
    out = {"role": "assistant", "content": self.content}
    if self.tool_calls:
      out["tool_calls"] = self.tool_calls
    return out


class FakeChoice:
  def __init__(self, message):
    self.message = message
    self.finish_reason = message.finish_reason


class FakeReply:
  def __init__(self, message):
    self.choices = [FakeChoice(message)]
    self.usage = None


class FakeCompletions:
  def __init__(self, outer):
    self.outer = outer

  async def create(self, **kwargs):
    self.outer.calls += 1
    if not self.outer.replies:
      raise AssertionError("model called with no scripted reply left")
    reply = self.outer.replies.pop(0)
    if reply == "RAISE_TIMEOUT":
      raise asyncio.TimeoutError
    return reply


class FakeChat:
  def __init__(self, outer):
    self.completions = FakeCompletions(outer)


class FakeClient:
  def __init__(self, replies):
    self.replies = list(replies)
    self.calls = 0
    self.chat = FakeChat(self)


def tool_call(name, args, call_id="call-1"):
  return {
      "id": call_id,
      "type": "function",
      "function": {"name": name, "arguments": args},
  }


class FakeSession:
  """taskbridge.Session surface backed by a real temp directory."""

  def __init__(self, instruction, time_left_value=6 * 3600, fail_probe=False):
    self._tmp = tempfile.TemporaryDirectory()
    self.root = self._tmp.name
    self.workdir = self.root
    self.instruction = instruction
    self.final_message = ""
    self._time_left = time_left_value
    self._fail_probe = fail_probe
    self.logs = []

  def time_left(self):
    return self._time_left

  async def log(self, text):
    self.logs.append(text)

  async def usage(self, *args):
    pass

  def _resolve(self, path):
    if os.path.isabs(path):
      return path
    return os.path.join(self.root, path)

  async def exec(self, command, timeout_sec=120):
    if self._fail_probe and 'echo "F ' in command:
      raise taskbridge.TaskError("probe exec failed (test)")
    result = subprocess.run(
        ["bash", "-c", command],
        cwd=self.root,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )
    return {
        "exit_code": result.returncode,
        "output": result.stdout + result.stderr,
        "truncated": False,
        "timed_out": False,
    }

  async def read_file(self, path):
    with open(self._resolve(path), "rb") as fh:
      return fh.read()

  async def write_file(self, path, content):
    full = self._resolve(path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    data = content.encode("utf-8")
    with open(full, "wb") as fh:
      fh.write(data)
    return len(data)


def run_solve(session, replies):
  client = FakeClient(replies)
  serve.client = client
  result = asyncio.run(serve.solve(session))
  return result, client


def check(name, condition, detail=""):
  if not condition:
    raise AssertionError(f"FAIL {name}: {detail}")
  print(f"PASS {name}")


# ---------------------------------------------------------------- scenarios

def scenario_1_text_only_done_then_real_work():
  """Text-only 'done' with no deliverable is nudged, not accepted."""
  session = FakeSession(
      "Design the roof deck. Write the deliverable to"
      " `output/submission.zip`."
  )
  replies = [
      FakeReply(FakeMessage(
          "Done. The roof deck design is complete and saved to"
          " output/submission.zip.")),
      FakeReply(FakeMessage(tool_calls=[
          tool_call("write_file",
                    '{"path": "output/submission.zip", "content": "PK fake zip"}'),
      ])),
      FakeReply(FakeMessage("Summary: output/submission.zip written.")),
  ]
  result, client = run_solve(session, replies)
  check("s1 returns the real summary", result.startswith("Summary:"),
        repr(result))
  check("s1 final_message is the summary",
        session.final_message.startswith("Summary:"), repr(session.final_message))
  check("s1 zip exists on disk",
        os.path.exists(os.path.join(session.root, "output/submission.zip")))
  check("s1 took 3 model calls", client.calls == 3, str(client.calls))


def scenario_2_malformed_tool_call_retried():
  """Error echoed as text is retried, never accepted as the summary."""
  session = FakeSession("Do the task. Deliverable: `output/submission.zip`.")
  replies = [
      FakeReply(FakeMessage(EVAL1_ERROR)),
      FakeReply(FakeMessage(tool_calls=[
          tool_call("bash", '{"command": "echo ok"}'),
      ])),
      FakeReply(FakeMessage(tool_calls=[
          tool_call("write_file",
                    '{"path": "output/submission.zip", "content": "PK fake zip"}'),
      ])),
      FakeReply(FakeMessage("Summary: done after retry.")),
  ]
  result, client = run_solve(session, replies)
  check("s2 returns the summary, not the error",
        result.startswith("Summary:"), repr(result))
  check("s2 final_message is not the error text",
        "Empty parameters" not in session.final_message,
        repr(session.final_message))
  check("s2 took 4 model calls", client.calls == 4, str(client.calls))


def scenario_3_fabricated_transcript_rejected():
  """Fake tool-call transcript in text is rejected with a sharp nudge."""
  session = FakeSession("Do the task. Deliverable: `output/submission.zip`.")
  replies = [
      FakeReply(FakeMessage(FABRICATED)),
      FakeReply(FakeMessage(tool_calls=[
          tool_call("write_file",
                    '{"path": "output/submission.zip", "content": "PK fake zip"}'),
      ])),
      FakeReply(FakeMessage("Summary: real work done.")),
  ]
  result, client = run_solve(session, replies)
  check("s3 returns the real summary", result.startswith("Summary:"),
        repr(result))
  check("s3 final_message is not the fabricated text",
        "bash(" not in session.final_message, repr(session.final_message))
  check("s3 took 3 model calls", client.calls == 3, str(client.calls))


def scenario_4_hallucinated_completion_honest_end():
  """Eval-2 shape: nudged, then an honest no-deliverable return, FS empty."""
  session = FakeSession(
      "Validate the fire test. Save the files that make up your answer under"
      " `output/`."
  )
  replies = [FakeReply(FakeMessage(HALLUCINATED)) for _ in range(12)]
  result, client = run_solve(session, replies)
  check("s4 honest no-deliverable message",
        result.startswith("The run ended without a deliverable on disk."),
        repr(result))
  check("s4 does not repeat the hallucinated claim",
        "48 minutes" not in result and "validation_memo" not in result,
        repr(result))
  # Fix A creates output/ (empty) at run start, so "empty" now means the
  # directory holds no files, not that it does not exist.
  out_dir = os.path.join(session.root, "output")
  check("s4 no deliverable files written",
        not os.path.exists(out_dir) or not os.listdir(out_dir))
  # Fix B adds exactly one turn: the last-chance write is offered at the
  # terminal condition, the model replies with text again, then the run
  # ends honestly.
  check("s4 bounded calls (3 nudges + 5 gate nudges + 1 forced turn + 1)",
        client.calls == 10, str(client.calls))


def scenario_5_smoke_regression():
  """Kit smoke task: hello.txt parsed from the instruction, gate passes."""
  files, dirs = serve.deliverable_candidates(SMOKE)
  check("s5 hello.txt parsed from instruction", "hello.txt" in files, str(files))
  session = FakeSession(SMOKE)
  replies = [
      FakeReply(FakeMessage(tool_calls=[
          tool_call("write_file",
                    '{"path": "hello.txt", "content": "HELLO\\n"}'),
      ])),
      FakeReply(FakeMessage("done")),
  ]
  result, client = run_solve(session, replies)
  check("s5 returns done", result == "done", repr(result))
  check("s5 took 2 model calls", client.calls == 2, str(client.calls))
  # The instruction-parse path is what passes this: output/-only would fail.
  session2 = FakeSession(SMOKE)
  files2, dirs2 = ["output/submission.zip"], ["output"]
  baseline = asyncio.run(serve._gate_baseline(session2, files2, dirs2))
  asyncio.run(session2.write_file("hello.txt", "HELLO\n"))
  gate, _detail = asyncio.run(
      serve.deliverable_gate(session2, files2, dirs2, baseline))
  check("s5 output-only gate would block the smoke task",
        gate == "missing", gate)


def scenario_6_wrap_up_honest_return():
  """Wrap-up with no deliverable: one last-chance write (Fix B), then an
  honest return when the model still writes nothing."""
  session = FakeSession(
      "Do the task. Deliverable: `output/submission.zip`.",
      time_left_value=100,
  )
  replies = [
      FakeReply(FakeMessage("Summary: almost done.")),
      FakeReply(FakeMessage("Summary: still no deliverable.")),
  ]
  result, client = run_solve(session, replies)
  check("s6 honest return in wrap-up",
        result.startswith("The run ended without a deliverable on disk."),
        repr(result))
  check("s6 exactly 2 model calls (forced turn + honest return)",
        client.calls == 2, str(client.calls))


def scenario_7_unknown_gate_fails_open():
  """Probe failure fails open: the model's summary is still returned."""
  session = FakeSession(SMOKE, fail_probe=True)
  replies = [
      FakeReply(FakeMessage(tool_calls=[
          tool_call("write_file",
                    '{"path": "hello.txt", "content": "HELLO\\n"}'),
      ])),
      FakeReply(FakeMessage("done")),
  ]
  result, client = run_solve(session, replies)
  check("s7 returns the summary on probe failure", result == "done",
        repr(result))
  check("s7 probe failure logged",
        any("baseline probe failed" in line for line in session.logs),
        str(session.logs))


def scenario_8_missing_dir_write_lands():
  """Fix A (fire-test shape): the agent echoes a file into output/ without
  mkdir -p. The harness creates output/ at run start, so the write lands
  and the gate accepts the summary. Without Fix A the redirect fails and
  the run ends with no deliverable."""
  session = FakeSession(
      "Validate the fire test. Save the files that make up your answer under"
      " `output/`."
  )
  summary = "Summary: validation memo written to output/."
  replies = [
      FakeReply(FakeMessage(tool_calls=[
          tool_call("bash",
                    '{"command": "echo MEMO > output/Validation_Memo.docx"}'),
      ])),
      FakeReply(FakeMessage(summary)),
  ]
  result, client = run_solve(session, replies)
  check("s8 returns the summary", result == summary, repr(result))
  memo = os.path.join(session.root, "output/Validation_Memo.docx")
  check("s8 memo exists on disk", os.path.exists(memo))
  with open(memo) as fh:
    check("s8 memo has the written content", "MEMO" in fh.read())
  check("s8 took 2 model calls", client.calls == 2, str(client.calls))


def scenario_9_forced_minimal_deliverable():
  """Fix B: at the end of the budget with no deliverable, the model gets one
  last-chance instruction to write a minimal best-effort deliverable; the
  final message then says plainly it is best-effort, not complete."""
  session = FakeSession(
      "Design the roof deck. Write your answer to `output/submission.zip`."
  )
  summary = "Summary: partial roof deck design written."
  replies = (
      [FakeReply(FakeMessage("Done. The roof deck design is complete."))
       for _ in range(9)]
      + [
          FakeReply(FakeMessage(tool_calls=[
              tool_call("write_file",
                        '{"path": "output/submission.zip", "content": "PK partial"}'),
          ])),
          FakeReply(FakeMessage(summary)),
      ]
  )
  result, client = run_solve(session, replies)
  check("s9 returns the summary with the best-effort note",
        result.startswith(serve.FORCED_WRITE_NOTE), repr(result))
  check("s9 summary text is included", summary in result, repr(result))
  check("s9 final_message carries the note",
        session.final_message == result, repr(session.final_message))
  check("s9 partial deliverable exists on disk",
        os.path.exists(os.path.join(session.root, "output/submission.zip")))
  check("s9 bounded calls (3 nudges + 5 gate nudges + 1 forced offer"
        " + 1 write + 1 summary)",
        client.calls == 11, str(client.calls))


def scenario_10_forced_turn_timeout_ends_honestly():
  """Fix B: if the last-chance turn itself runs out of time, the run ends
  honestly instead of looping on zero-second timeouts."""
  session = FakeSession(
      "Do the task. Deliverable: `output/submission.zip`.",
      time_left_value=100,
  )
  replies = [
      FakeReply(FakeMessage("Summary: almost done.")),
      "RAISE_TIMEOUT",
  ]
  result, client = run_solve(session, replies)
  check("s10 honest return after the forced turn times out",
        result.startswith("The run ended without a deliverable on disk."),
        repr(result))
  check("s10 exactly 2 model calls", client.calls == 2, str(client.calls))


def unit_gate_baseline():
  """Pre-existing input files never count; a new deliverable does."""
  session = FakeSession(
      "Use `calc_book.xlsx`. Deliverable: `output/submission.zip`."
  )
  asyncio.run(session.write_file("calc_book.xlsx", "input"))
  files, dirs = serve.deliverable_candidates(session.instruction)
  check("u1 input file parsed as candidate", "calc_book.xlsx" in files,
        str(files))
  baseline = asyncio.run(serve._gate_baseline(session, files, dirs))
  gate, _ = asyncio.run(
      serve.deliverable_gate(session, files, dirs, baseline))
  check("u1 input-only state is missing", gate == "missing", gate)
  asyncio.run(session.write_file("output/submission.zip", "PK fake zip"))
  gate, detail = asyncio.run(
      serve.deliverable_gate(session, files, dirs, baseline))
  check("u1 new deliverable is ok", gate == "ok", f"{gate} {detail}")
  check("u1 detail names the zip", "submission.zip" in detail, detail)


def unit_roof_deck_instruction():
  """Real roof-deck task.md: the absolute deliverable path is parsed."""
  with open(
      "/home/hatch/workspace/kaggle/ple/dataset/tasks/roof-deck-design/"
      "environment/filesystem/"
      "final_batch4__structural_task7_roof_deck_design__blind/task.md"
  ) as fh:
    instruction = fh.read()
  files, _dirs = serve.deliverable_candidates(instruction)
  check("u2 absolute submission.zip parsed",
        "/filesystem/final_batch4__structural_task7_roof_deck_design__blind"
        "/output/submission.zip" in files, str(files[:5]))


def main():
  scenario_1_text_only_done_then_real_work()
  scenario_2_malformed_tool_call_retried()
  scenario_3_fabricated_transcript_rejected()
  scenario_4_hallucinated_completion_honest_end()
  scenario_5_smoke_regression()
  scenario_6_wrap_up_honest_return()
  scenario_7_unknown_gate_fails_open()
  scenario_8_missing_dir_write_lands()
  scenario_9_forced_minimal_deliverable()
  scenario_10_forced_turn_timeout_ends_honestly()
  unit_gate_baseline()
  unit_roof_deck_instruction()
  print("ALL SCENARIOS PASS")


if __name__ == "__main__":
  main()
