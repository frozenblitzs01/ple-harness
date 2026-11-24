# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A minimal harness: one model, three tools, one loop.

The model gets the task and three tools that act in the task container. Each
tool call runs there and its result goes back to the model, until the model
answers without calling a tool. That answer is the final message.
"""

import asyncio
import json
import os
import re
import shlex

import openai
import taskbridge

MODEL = os.environ["MODEL_NAME"]
# The model's highest reasoning level: max for Claude, GLM, GPT-6 and
# DeepSeek-V4, high for the others (Gemini refuses max). REASONING_EFFORT
# overrides it.
MAX_EFFORT_MODELS = ("claude", "glm", "gpt-6", "deepseek-v4")
EFFORT = os.environ.get("REASONING_EFFORT") or (
    "max" if any(m in MODEL.lower() for m in MAX_EFFORT_MODELS) else "high"
)
WRAP_UP_SEC = 240  # ask for the summary this long before the time limit
WRAP_UP = {
    "role": "user",
    "content": "Time is almost up. Stop and reply with your summary.",
}
RESULT_CHARS = 20_000  # a longer tool result loses its middle
# Seconds between retries once the SDK's own quick retries are exhausted.
RETRY_WAITS = (5, 15, 30, 60, 120)
# How endpoints word a 400 saying the conversation no longer fits the context
# window: Claude, OpenAI and vLLM, Gemini, xAI.
CONTEXT_FULL = re.compile(
    r"context.?(length|window)|prompt is too long|maximum prompt length"
    r"|exceed[^.]{0,40}(token|context)",
    re.I,
)
CUT_KEEP = 1000  # characters a tool result keeps once the context is full
# times in a row an empty or cut-off reply gets a "continue" before the run
# stops
MAX_NUDGES = 3
# deliverable-missing nudges before the run stops honestly (§1)
MAX_GATE_NUDGES = 5
# consecutive identical tool-error replies before the run stops honestly (§2)
MAX_ERR_RETRIES = 3
# note prepended to the final message when the deliverable only exists
# because of the last-chance write (Fix B): the file is best-effort and may
# be partial, so the message must not present it as a complete delivery.
FORCED_WRITE_NOTE = (
    "Best-effort deliverable written at the time limit; the summary below"
    " describes what was actually produced. "
)
# lower it for a small context window
MAX_OUTPUT_TOKENS = int(os.environ.get("MAX_OUTPUT_TOKENS", "32000"))
# Claude caches a prompt prefix only when marked with cache_control. Each call
# marks the system prompt and the latest message (using 2 of Claude's 4 cache
# breakpoints) so each turn reads the prior conversation from cache. Other
# providers cache automatically without markers.
CACHE_MARK = "claude" in MODEL.lower()

# The evaluator sets OPENAI_BASE_URL and OPENAI_API_KEY for every model.
# The SDK handles quick retries; recover() handles longer backoffs. Because
# calls are non-streaming, a max-effort response can take over 15 minutes
# before any bytes arrive, so the timeout matches the egress proxy's 30-minute
# idle limit.
client = openai.AsyncOpenAI(max_retries=5, timeout=1800)

SYSTEM = 'You are an expert engineer working on a task in a Linux container with no internet access. Your tools act inside it, and bash starts in {workdir}. Read the task and the files it points to before you start. Compute with code, not by hand. Write each deliverable exactly where and in the format the task asks, then open it again to check it. When you are done, reply without calling a tool: a short summary of each deliverable, where it is, and the key results. Do every action by calling the provided function tools, never by writing a tool call as text or JSON in your reply, and never claim a file or change exists until a tool result confirms it.'


def tool(name, description, **params):
  """Builds an OpenAI function-tool definition dictionary.

  Args:
    name: Tool function name.
    description: Human-readable tool description.
    **params: Parameter names mapped to their JSON Schema type strings.

  Returns:
    An OpenAI function-tool specification dictionary.
  """
  return {
      "type": "function",
      "function": {
          "name": name,
          "description": description,
          "parameters": {
              "type": "object",
              "properties": {k: {"type": v} for k, v in params.items()},
              "required": list(params),
          },
      },
  }


TOOLS = [
    tool(
        "bash",
        "Run a bash command (120 s limit) and return its exit code and output.",
        command="string",
    ),
    tool("read_file", "Read a text file.", path="string"),
    tool(
        "write_file",
        "Create or overwrite a file; parent folders are created.",
        path="string",
        content="string",
    ),
]


def clip(text):
  """Truncates `text` in the middle if it exceeds `RESULT_CHARS` characters.

  Args:
    text: Tool output string to clip.

  Returns:
    The original string if within `RESULT_CHARS`, or a middle-truncated string.
  """
  if len(text) <= RESULT_CHARS:
    return text
  half = RESULT_CHARS // 2
  return (
      f"{text[:half]}\n[... {len(text) - RESULT_CHARS} characters cut"
      f" ...]\n{text[-half:]}"
  )


def marked(messages):
  """Returns the messages a model call sends.

  For Claude, this is a copy whose system prompt and newest message carry
  `cache_control`. The stored conversation stays as it is, so each turn marks
  its own newest message.

  Args:
    messages: The conversation so far, in OpenAI chat format.

  Returns:
    `messages` itself for other models, or the marked copy for Claude.
  """
  if not CACHE_MARK:
    return messages
  out = list(messages)
  for i in {0, len(out) - 1}:
    m, content = out[i], out[i].get("content")
    if isinstance(content, str) and content:
      out[i] = {
          **m,
          "content": [{
              "type": "text",
              "text": content,
              "cache_control": {"type": "ephemeral"},
          }],
      }
    else:
      out[i] = {**m, "cache_control": {"type": "ephemeral"}}
  return out


async def run_tool(session, fn):
  """Executes a single tool call in the task container and returns its output.

  Rewrites `fn["arguments"]` as canonical JSON (or `"{}"` if invalid) so the
  conversation history remains valid for strict endpoints. Any tool failure is
  returned as an error string for the model.

  Args:
    session: Active `taskbridge.Session` connected to the task container.
    fn: Function-call dictionary containing `name` and `arguments`.

  Returns:
    The clipped tool output or error string to send back to the model.
  """
  name = fn["name"]
  try:
    args = json.loads(fn["arguments"] or "{}")
    if not isinstance(args, dict):
      raise TypeError("not a JSON object")
    fn["arguments"] = json.dumps(args, allow_nan=False)
  except (TypeError, ValueError) as exc:
    fn["arguments"] = "{}"
    return (
        f"error: the arguments are not a JSON object ({exc}); send the call"
        " again"
    )
  try:
    if name == "bash":
      result = await session.exec(args["command"])
      return clip(f"exit code {result['exit_code']}\n{result['output']}")
    if name == "read_file":
      return clip(
          (await session.read_file(args["path"])).decode("utf-8", "replace")
      )
    if name == "write_file":
      return (
          f"wrote {await session.write_file(args['path'], args['content'])}"
          f" bytes to {args['path']}"
      )
    return f"error: there is no tool named {name}"
  # ValueError: content with an unpaired surrogate
  except (taskbridge.TaskError, KeyError, ValueError) as exc:
    return f"error: {type(exc).__name__}: {exc}"


async def recover(session, messages, exc, waits, until):
  """Handles a failed model call and returns whether to retry.

  On a 400 context-overflow error, shortens the oldest tool results. On a rate
  limit, server error, or connection drop, sleeps for the next interval in
  `RETRY_WAITS` (capped at the wrap-up deadline). Errors are logged rather than
  added to the conversation.

  Args:
    session: Active `taskbridge.Session` for the task.
    messages: The conversation, shortened in place when the context is full.
    exc: The `openai.APIError` the call raised.
    waits: Iterator over the remaining intervals in `RETRY_WAITS`.
    until: Seconds before the time limit at which the wrap-up starts.

  Returns:
    `True` to retry the call, `False` to re-raise.
  """
  status = getattr(exc, "status_code", None)  # None: no HTTP answer
  if status == 400 and CONTEXT_FULL.search(str(exc)):
    return await shorten(session, messages)
  wait = next(waits, None)
  if wait is None or not (
      status is None or status in (408, 409, 429) or status >= 500
  ):
    return False
  left = session.time_left()
  if left is not None and left > until:
    wait = min(wait, left - until)
  await session.log(
      f"model call failed ({str(exc)[:200]}); again in {wait:.0f} s"
  )
  await asyncio.sleep(wait)
  return True


async def shorten(session, messages):
  """Truncates the older half of long tool results to `CUT_KEEP` characters.

  Repeated calls truncate progressively newer results. Claude's thinking blocks
  are kept intact because each block's signature is self-contained and Claude
  rejects tool loops if the latest assistant turn loses its thinking block.

  Args:
    session: Active `taskbridge.Session` for the task.
    messages: The conversation, modified in place.

  Returns:
    Whether any tool result was truncated.
  """
  long = [
      n
      for n, m in enumerate(messages)
      if m["role"] == "tool" and len(m["content"]) > 2 * CUT_KEEP
  ]
  if not long:
    return False
  cut = long[: max(1, len(long) // 2)]
  for n in cut:
    messages[n]["content"] = (
        messages[n]["content"][:CUT_KEEP]
        + "\n[... cut to save context; run the tool again if needed]"
    )
  await session.log(f"context full: cut {len(cut)} old tool results")
  return True


# --- Deliverable gate (§1), tool-error (§2) and fabrication (§3) guards ---
#
# The 2026-11-24 Codespace evals all scored 0.0 because the loop trusted the
# model's words: a text reply claiming completion was accepted although no
# deliverable existed on disk. These helpers make solve() check the disk
# itself before accepting any reply as final.

DELIVERABLE_PATH_RE = re.compile(r"`([^`\n]{1,120})`")
PATH_LIKE_EXTS = (
    ".zip", ".txt", ".md", ".docx", ".pdf", ".py", ".xlsx", ".csv", ".json",
    ".html", ".tex",
)
# The probe script stays small even for instructions naming many files.
MAX_GATE_CANDIDATES = 60


def deliverable_candidates(instruction):
  """Paths the instruction names as deliverables, plus the output/ convention.

  Returns (file_paths, dir_paths): paths relative to the workdir unless
  absolute. A backticked span ending in "/" is a directory that must contain
  files; a span containing "/" or ending in a known extension is a file.
  """
  files, dirs = ["output/submission.zip"], ["output"]
  seen_f, seen_d = set(files), set(dirs)
  for match in DELIVERABLE_PATH_RE.finditer(instruction or ""):
    token = match.group(1).strip()
    if not token:
      continue
    if token.endswith("/"):
      key = token.rstrip("/")
      if key and key not in seen_d:
        seen_d.add(key)
        dirs.append(key)
    elif "/" in token or token.lower().endswith(PATH_LIKE_EXTS):
      if token not in seen_f:
        seen_f.add(token)
        files.append(token)
  return files[:MAX_GATE_CANDIDATES], dirs[:10]


TOOL_ERROR_RE = re.compile(
    r"^\s*error[: ]|empty parameters|must include a valid json object"
    r"|did you paste the request incorrectly",
    re.I,
)
FABRICATED_MARKERS = (
    "bash(", "read_file(", "write_file(", '{"functionname"',
    '"function_name"', "<tool_call>", "function_calls", "tool result:",
)


def looks_like_tool_error(text):
  """Whether a text-only reply is a tool error echoed as text, not a summary."""
  return bool(text and TOOL_ERROR_RE.search(text))


def looks_fabricated(text, used_tool):
  """Whether a no-tool reply fakes a tool-call transcript in plain text.

  Only applies before the model has used any real tool: once it genuinely
  used tools, a summary describing past work is normal and the deliverable
  gate is the check that applies.
  """
  if used_tool or not text:
    return False
  low = text.lower()
  hits = sum(1 for marker in FABRICATED_MARKERS if marker in low)
  claims_file = bool(
      re.search(
          r"\b(wrote|created|saved|written)\b.{0,60}\.(zip|txt|md|docx|pdf|py|xlsx)",
          low,
      )
  )
  return hits >= 2 or (hits >= 1 and claims_file)


def _gate_probe_script(files, dirs):
  """One read-only bash probe: one `F <i> ...` / `D <j> ...` line per candidate.

  Files print existence, size and mtime; directories print file count and a
  hash of their file listing. Paths are shell-quoted; the probe writes nothing.
  """
  lines = []
  for i, path in enumerate(files):
    quoted = shlex.quote(path)
    lines.append(
        f'if [ -f {quoted} ]; then echo "F {i} 1 $(stat -c %s {quoted})'
        f' $(stat -c %Y {quoted})"; else echo "F {i} 0 - -"; fi'
    )
  for j, path in enumerate(dirs):
    quoted = shlex.quote(path)
    lines.append(
        f'if [ -d {quoted} ]; then echo "D {j} $(find {quoted} -type f'
        f' 2>/dev/null | wc -l) $(find {quoted} -type f -printf \'%p %s'
        f' %T@\\n\' 2>/dev/null | sort | md5sum | cut -d\' \' -f1)";'
        f' else echo "D {j} - -"; fi'
    )
  return "\n".join(lines)


def _parse_gate_output(output):
  """Parses probe output into ({file_i: (size, mtime) | None}, {dir_j: ...}).

  Returns None when the output carries no usable probe line.
  """
  files, dirs = {}, {}
  for line in (output or "").splitlines():
    parts = line.split()
    if len(parts) == 5 and parts[0] == "F" and parts[1].isdigit():
      files[int(parts[1])] = (
          None if parts[2] == "0" else (parts[3], parts[4])
      )
    elif len(parts) == 4 and parts[0] == "D" and parts[1].isdigit():
      dirs[int(parts[1])] = None if parts[2] == "-" else (parts[2], parts[3])
  if not files and not dirs:
    return None
  return files, dirs


async def _ensure_deliverable_dirs(session, files, dirs):
  """Best-effort mkdir -p of the deliverable dirs and file parents (Fix A).

  Runs once at solve() start, before the baseline snapshot, so a model write
  to a standard path cannot fail for a missing directory: the fire-test eval
  wrote /app/output/Validation_Memo.docx via echo without mkdir -p, so the
  file never existed and the gate correctly found nothing. The baseline is
  taken after, so the empty directories never count as delivered. A failure
  is logged, never fatal: the model can still create the directories itself.
  """
  targets = set(dirs)
  for path in files:
    parent = os.path.dirname(path)
    if parent:
      targets.add(parent)
  if not targets:
    return
  cmd = "mkdir -p " + " ".join(shlex.quote(p) for p in sorted(targets))
  try:
    await session.exec(cmd, timeout_sec=30)
  except taskbridge.TaskError as exc:
    await session.log(
        "deliverable directories could not be created"
        f" ({str(exc)[:200]}); continuing"
    )


async def _gate_baseline(session, files, dirs):
  """One probe at the start of solve(); None when it fails (gate fails open)."""
  try:
    result = await session.exec(
        _gate_probe_script(files, dirs), timeout_sec=30
    )
    snapshot = _parse_gate_output(result.get("output", ""))
  except taskbridge.TaskError as exc:
    await session.log(
        "deliverable baseline probe failed"
        f" ({str(exc)[:200]}); gate will fail open"
    )
    return None
  if snapshot is None:
    await session.log(
        "deliverable baseline probe returned nothing usable;"
        " gate will fail open"
    )
    return None
  return snapshot


async def deliverable_gate(session, files, dirs, baseline):
  """Tri-state disk check: ("ok" | "missing" | "unknown", detail).

  A path counts as delivered only when it is new or changed since the
  baseline snapshot, so pre-existing input files never count. "unknown"
  fails open: a hidden task whose deliverable layout the gate cannot parse
  must not be blocked by the gate.
  """
  if baseline is None:
    return "unknown", "the deliverable check could not run"
  try:
    result = await session.exec(
        _gate_probe_script(files, dirs), timeout_sec=30
    )
    snapshot = _parse_gate_output(result.get("output", ""))
  except taskbridge.TaskError as exc:
    await session.log(
        f"deliverable gate probe failed ({str(exc)[:200]}); failing open"
    )
    return "unknown", "the deliverable check could not run"
  if snapshot is None:
    await session.log(
        "deliverable gate probe returned nothing usable; failing open"
    )
    return "unknown", "the deliverable check could not run"
  now_files, now_dirs = snapshot
  base_files, base_dirs = baseline
  delivered = []
  for i, path in enumerate(files):
    now = now_files.get(i)
    if now is not None and base_files.get(i) != now:
      delivered.append(f"`{path}`")
  for j, path in enumerate(dirs):
    now = now_dirs.get(j)
    if now is not None and now[0] != "0" and base_dirs.get(j) != now:
      delivered.append(f"`{path}/`")
  if delivered:
    return "ok", "found " + ", ".join(delivered[:3])
  missing = []
  for i, path in enumerate(files):
    now = now_files.get(i)
    if now is None:
      missing.append(f"`{path}` does not exist")
    elif base_files.get(i) == now:
      missing.append(f"`{path}` is unchanged since the start")
    if len(missing) >= 2:
      break
  for j, path in enumerate(dirs):
    now = now_dirs.get(j)
    if now is None:
      missing.append(f"`{path}/` does not exist")
    elif now[0] == "0":
      missing.append(f"`{path}/` is empty")
    elif base_dirs.get(j) == now:
      missing.append(f"`{path}/` is unchanged since the start")
    if len(missing) >= 3:
      break
  return "missing", "; ".join(missing) or "no deliverable found"


def _gate_nudge_text(detail, nudge_number, remaining):
  """Escalating nudge after a summary claims completion with no deliverable."""
  if nudge_number >= 3:
    return (
        f"Still no deliverable on disk ({detail}). Write a first COMPLETE"
        " version now, even if imperfect — a file on disk is what gets"
        f" graded. You have {remaining} more tries before I stop."
    )
  return (
      "Your summary says the work is done, but I checked the container and"
      f" the deliverable is not on disk yet: {detail}. Continue working with"
      " the tools — write the deliverable first, then give your summary."
  )


def _forced_write_text(detail, files):
  """Last-chance instruction (Fix B) when the budget is nearly gone and no
  deliverable exists: write a minimal best-effort version now."""
  target = files[0] if files else "output/submission.zip"
  return (
      "Time is almost up and there is still no deliverable on disk"
      f" ({detail}). This is your last chance: use the tools now to write"
      f" a minimal best-effort version of the deliverable to `{target}`"
      " (or under `output/` for a multi-file answer) from the work you"
      " have done so far — even if it is partial or incomplete, a file on"
      " disk can still score, while no file scores 0 for certain. Then"
      " reply with a summary that says plainly what you actually wrote"
      " and what is still missing or incomplete — do not claim it is"
      " complete."
  )


async def _end_at_time_limit(session, files, dirs, baseline):
  """Honest return when the last-chance turn itself runs out of time (Fix B).

  The budget is gone, so the run ends here instead of looping on
  zero-second model-call timeouts.
  """
  gate, detail = await deliverable_gate(session, files, dirs, baseline)
  if gate == "ok":
    session.final_message = (
        "The run ended at the time limit with a deliverable on disk. "
        + detail
    )
  elif gate == "unknown":
    session.final_message = (
        "The run ended at the time limit; the deliverable check could"
        " not run, so nothing was verified."
    )
  else:
    session.final_message = (
        "The run ended without a deliverable on disk. " + detail
    )
  return session.final_message


async def solve(session):
  """Runs the minimal tool-calling loop on `session` until completion.

  Args:
    session: Active `taskbridge.Session` for the task.

  Returns:
    The final summary message from the model.
  """
  messages = [
      {"role": "system", "content": SYSTEM.format(workdir=session.workdir)},
      {"role": "user", "content": session.instruction},
  ]
  # The deliverable gate (§1): snapshot the container before the model does
  # any work, so pre-existing input files never count as deliverables.
  files, dirs = deliverable_candidates(session.instruction)
  # Fix A: create the deliverable directories first, so the baseline sees
  # the (empty) directories and a later write still counts as delivered.
  await _ensure_deliverable_dirs(session, files, dirs)
  baseline = await _gate_baseline(session, files, dirs)
  # head: the start of an answer cut off at the output limit
  nudges, head, waits = 0, "", iter(RETRY_WAITS)
  gate_nudges, err_streak, last_err = 0, 0, ""
  # Fix B: the last-chance write is offered once per run; the granted turn
  # gets one tool call even when time is nearly up.
  forced_write_offered, forced_write_turn = False, False
  while True:
    left = session.time_left()  # None when the task has no time limit
    wrap_up = left is not None and left < WRAP_UP_SEC
    # Fix B: the granted turn gets tools even when time is nearly up. Only
    # the call shaping uses the suppressed value (call_wrap_up); wrap_up
    # itself still records that time is nearly up, so the accept branch
    # ends the run afterwards instead of treating it as a normal nudge.
    force_turn = forced_write_turn
    call_wrap_up = wrap_up and not force_turn
    if call_wrap_up and messages[-1:] != [WRAP_UP]:  # asked once, also on a retry
      messages.append(dict(WRAP_UP))
    # The forced-write turn may use the whole remaining time: the task's
    # hard time limit is the backstop, and the call is cut there instead of
    # at the wrap-up point.
    if left is None or call_wrap_up:
      call_timeout = None
    elif force_turn:
      call_timeout = left
    else:
      call_timeout = left - WRAP_UP_SEC
    try:  # a call still running when the wrap-up starts is stopped
      reply = await asyncio.wait_for(
          client.chat.completions.create(
              model=MODEL,
              messages=marked(messages),
              tools=TOOLS,
              tool_choice="none" if call_wrap_up else "auto",
              reasoning_effort=EFFORT,
              max_completion_tokens=MAX_OUTPUT_TOKENS,
          ),
          call_timeout,
      )
    except asyncio.TimeoutError:
      if force_turn:
        # Fix B: the last-chance turn ran out of time, so the budget is
        # gone. End honestly instead of looping on zero-second timeouts.
        forced_write_turn = False
        return await _end_at_time_limit(session, files, dirs, baseline)
      continue
    except openai.APIError as exc:
      if await recover(session, messages, exc, waits, WRAP_UP_SEC):
        continue
      raise
    waits = iter(RETRY_WAITS)
    forced_write_turn = False  # the granted turn has now happened
    if reply.usage:
      details = getattr(reply.usage, "prompt_tokens_details", None)
      await session.usage(
          MODEL,
          reply.usage.prompt_tokens,
          reply.usage.completion_tokens,
          getattr(details, "cached_tokens", 0) or 0,
      )
    message, cut = (
        reply.choices[0].message,
        reply.choices[0].finish_reason == "length",
    )
    text = head + (message.content or "")
    # Send the message back as the endpoint returned it: Gemini refuses a tool
    # call that comes back without its thought signature, which is one of the
    # endpoint's own fields.
    turn = message.model_dump(exclude_none=True)
    if wrap_up or not message.tool_calls:
      used_tool = any(m.get("role") == "tool" for m in messages)
      if not message.tool_calls and message.content and not wrap_up:
        if looks_like_tool_error(text):
          # §2: an error echoed as text is not a summary; retry the call.
          err = text.strip()[:200]
          err_streak = err_streak + 1 if err == last_err else 1
          last_err = err
          if err_streak >= MAX_ERR_RETRIES or nudges >= MAX_NUDGES:
            gate, detail = await deliverable_gate(
                session, files, dirs, baseline
            )
            if gate == "ok":
              session.final_message = (
                  "The run ended with a deliverable on disk, but the"
                  " model's last reply was a tool error, not a summary"
                  f" ({err})."
              )
            elif gate == "unknown":
              session.final_message = (
                  "The run ended after repeated tool errors; the"
                  " deliverable check could not run, so nothing was"
                  f" verified ({err})."
              )
            else:
              session.final_message = (
                  "The run ended without a deliverable on disk: the model"
                  " kept returning a tool error instead of calling a tool"
                  f" ({err})."
              )
            return session.final_message
          messages.append(turn)
          messages.append({
              "role": "user",
              "content": (
                  "That was an error message, not a summary. The tool call"
                  f" failed: {err}. Send the call again with a valid JSON"
                  " object for the arguments. If the same call keeps"
                  " failing, simplify it — first run a trivial command such"
                  " as bash `echo ok` to confirm the loop works, then retry"
                  " the real call."
              ),
          })
          nudges, head = nudges + 1, text
          continue
        if looks_fabricated(text, used_tool):
          # §3: a fake tool-call transcript in text; sharp nudge. Counts
          # under the MAX_NUDGES budget, so a model that keeps fabricating
          # falls through to the accept decision, where the gate blocks it.
          if nudges < MAX_NUDGES:
            messages.append(turn)
            messages.append({
                "role": "user",
                "content": (
                    "Your reply shows tool calls as text. Text does nothing"
                    " — only real tool calls run anything. Call the tools"
                    " now: start with bash `ls` to see the workspace, then"
                    " do each step with a real tool call and check the tool"
                    " result before claiming anything."
                ),
            })
            nudges, head = nudges + 1, text
            continue
      if wrap_up or ((message.content and not cut) and (used_tool or nudges == MAX_NUDGES or forced_write_offered)):
        # §1: never accept a plain-text reply as done until the deliverable
        # is on disk. §4: only an accepted reply becomes the final message,
        # so a hallucinated summary can never be what taskbridge sends.
        # Fix B: once the last-chance write has been offered, a text reply
        # is gate-checked at once instead of burning generic nudges — the
        # run is already at the end of its budget.
        gate, detail = await deliverable_gate(session, files, dirs, baseline)
        if gate == "missing":
          if wrap_up or gate_nudges >= MAX_GATE_NUDGES:
            if not forced_write_offered:
              # Fix B: one last chance to write a minimal best-effort
              # deliverable instead of ending empty (no file is a certain
              # 0; a partial file can score above 0).
              forced_write_offered = True
              forced_write_turn = True
              if message.content:
                messages.append(turn)
              messages.append({
                  "role": "user",
                  "content": _forced_write_text(detail, files),
              })
              continue
            session.final_message = (
                "The run ended without a deliverable on disk. " + detail
            )
            return session.final_message
          gate_nudges += 1
          if message.content:
            messages.append(turn)
          messages.append({
              "role": "user",
              "content": _gate_nudge_text(
                  detail, gate_nudges, MAX_GATE_NUDGES - gate_nudges
              ),
          })
          # NOTE: nudges is deliberately not incremented here. The accept
          # condition tests `nudges == MAX_NUDGES`; incrementing past it
          # would strand the run on generic nudges until the time limit.
          continue
        if looks_like_tool_error(text):
          # Never accept an error as the final summary, even when a
          # deliverable exists (§2).
          session.final_message = (
              "The run ended with a deliverable on disk, but the model's"
              " last reply was a tool error, not a summary"
              f" ({text.strip()[:200]})."
          )
          return session.final_message
        if gate == "ok" and forced_write_offered:
          # Fix B: the deliverable only exists because of the last-chance
          # write. Say plainly that it is best-effort instead of letting
          # the model's summary present it as a complete delivery.
          session.final_message = FORCED_WRITE_NOTE + text
        else:
          session.final_message = text
        return session.final_message
      nudges, head = nudges + 1, text
      if message.content:  # cut off at the output limit
        messages.append(turn)
      messages.append({
          "role": "user",
          "content": (
              "Your reply was cut off; continue where it stopped."
              if cut
              else ("You have not called any tool yet. Use a tool to do the work and check the result before giving your final summary." if not used_tool else "Continue the task, and finish with your summary.")
          ),
      })
      continue
    nudges, head = 0, ""
    messages.append(turn)
    for call in turn["tool_calls"]:
      await session.log(
          f"{call['function']['name']} {call['function']['arguments'][:200]}"
      )
      content = await run_tool(session, call["function"])
      messages.append(
          {"role": "tool", "tool_call_id": call["id"], "content": content}
      )
    if left is not None:
      messages[-1][
          "content"
      ] += f"\n[{int(session.time_left() // 60)} minutes left]"


if __name__ == "__main__":
  taskbridge.run(solve)
