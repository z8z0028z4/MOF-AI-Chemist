# Secrets And API Key Flow / Secrets 與 API Key 流程

Status: baseline policy and scan result
Date: 2026-05-29

This document records the current secret-handling posture for a public repository. It does not reveal local key values.

## Policy

- Never commit personal API keys.
- `.env` and `.venv_config` are local machine files.
- Frontend Settings may collect user API keys, but backend must store them only in ignored local files or another explicit local secret store.
- Demo mode must not require real API keys.
- Tests must not read real `.env` unless marked `external`.
- OpenRouter key handling must follow the same pattern as OpenAI/Google keys before provider implementation begins.

## Current Ignore Rules

Current `.gitignore` ignores:

- `.env`
- `.env.local`
- `.env.*.local`
- `.venv_config`
- virtual environments
- build outputs and caches

Tracked settings file:

- `settings.json`

The tracked settings file contains model/config preferences, not API keys. Treat it as non-secret config only. Do not add key fields to tracked settings files.

## Current Local Scan

Commands run:

```bash
git ls-files | rg '(^|/)\\.env$|settings\\.json|\\.venv_config'
git check-ignore -v .env .venv_config
rg --hidden 'sk-...|OPENAI_API_KEY|GOOGLE_API_KEY|OPENROUTER|api_key|Bearer ...'
```

Results:

- `.env` is ignored by `.gitignore`.
- `.venv_config` is ignored by `.gitignore`.
- `.env` exists locally and contains provider key variables, but it is ignored and was not printed in this report.
- `settings.json` is tracked; its contents are model/settings preferences only.
- No committed personal `sk-...` style OpenAI key was found in tracked source by the scan.
- README examples use placeholder values such as `sk-your-openai-api-key-here`.

## Existing Backend Flow

Current Settings API routes:

- `POST /api/v1/settings/api-keys/openai`
- `POST /api/v1/settings/api-keys/google`
- `GET /api/v1/settings/env-status`
- `POST /api/v1/settings/env-file/create-dummy`

Current behavior:

- Backend validates the key with provider API before writing it.
- Backend writes accepted keys into `.env` through `env_manager`.
- Backend reloads config and reinitializes the LLM client.
- Dummy keys can be created for startup.

Risks:

- Key validation requires network and provider availability.
- `.env` is local but still visible to local processes and humans with filesystem access.
- OpenRouter is not implemented yet, so key flow must be added deliberately rather than copied ad hoc.

## Required OpenRouter Key Flow

Before OpenRouter implementation:

1. Add explicit `OPENROUTER_API_KEY` handling to config/env manager.
2. Add Settings API request model and route only after provider contract tests exist.
3. Validate key with a narrow, low-cost request or account/status endpoint if OpenRouter supports one.
4. Write accepted key only to ignored `.env`.
5. Do not write OpenRouter keys to `settings.json`, frontend source, localStorage, or test fixtures.
6. Add tests for dummy/missing key behavior without reading a real `.env`.
7. Add one `external` smoke test that requires `OPENROUTER_API_KEY`.

## Demo Mode Rule

Demo mode must report demo readiness without a real key. It may show where keys are entered, but it must not create, fake, or persist provider credentials.

## Agent Checklist

Before committing or pushing:

```bash
git status --short
git ls-files | rg '(^|/)\\.env$|\\.venv_config$'
rg --hidden --glob '!.git/**' --glob '!frontend/node_modules/**' --glob '!frontend/dist/**' 'sk-[A-Za-z0-9_-]{20,}|Bearer [A-Za-z0-9._-]{20,}|OPENROUTER_API_KEY'
```

If any real key appears in a tracked file, stop and remove it before continuing.
