# PLE Agent Harness — Google Physical-Engineering's Last Exam

Kaggle competition: [Physical-Engineering's Last Exam](https://www.kaggle.com/competitions/physical-engineerings-last-exam)
($400,000 prize pool; deadline 5 Jan 2027 23:59 UTC).

## Layout

- `kit/` — official PLE kit (`google-research/ple`, Apache 2.0): evaluation harness,
  dev-set tooling, and `sample_submissions/`.
- `serve.py` / `taskbridge.py` — our agent harness (WebSocket server speaking the
  kit's JSON protocol).
- `submission.yaml` — submission manifest (validated with `uv run python -m kit check`).
- `requirements.txt` — harness dependencies.

## Development

This repo is developed inside a GitHub Codespace (4-core/16 GB) with
Docker-in-Docker (see `.devcontainer/devcontainer.json`), because the kit's
build step needs a real Docker daemon.

```bash
# inside the codespace
uv run python -m kit check
```

## Status

- **Phase 0 (done, 23 Nov 2026):** kit + dev dataset downloaded locally; `kit check`
  passes submission.yaml/files, build blocked (no Docker in the local VM).
- **Phase 1 (in progress):** harness v0 on Codespaces — verify Docker-in-Docker,
  pass `kit check` build, run 2–3 dev tasks end-to-end.

## Notes

- The dev dataset (gated Hugging Face `google/physical-engineerings-last-exam`)
  is **not** committed here; download it inside the codespace when needed.
- No API keys or credentials are stored in this repo. The dev model is supplied
  separately at runtime (free-tier key), never committed.
