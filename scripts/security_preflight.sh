#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

fail() {
  printf 'SECURITY PREFLIGHT FAILED: %s\n' "$1" >&2
  exit 1
}

warn() {
  printf 'SECURITY PREFLIGHT WARNING: %s\n' "$1" >&2
}

# Category A: path-based rules — always block regardless of location.
PATH_RULE_RE='(^|/)(\.env|\.env\..*|\.venv_config)$|(^|/)experiment_data/|(^|/)backend/experiment_data/|(^|/)app/data/|(^|/)app/test_downloads/|(^|/)ai_research_agent_data_package_[^/]+/|(^|/)release/|(^|/)user_data/|(^|/)private_data/|(^|/)local_data/|(^|/)papers?/|vector_index|parsed_chemicals|:Zone\.Identifier$'
# Category B: extension-based rules — block UNLESS under tests/test_data/
# (explicit synthetic-fixture allowlist per AGENTS.md User Data & Privacy Policy).
EXT_RULE_RE='\.pdf$|\.docx$|\.xlsx$|\.csv$|\.cif$|\.ckpt$|\.pt$|\.pth$'

audit_paths() {
  # $1 = label ("tracked"|"staged"), $2 = newline-separated paths.
  local label="$1" paths="$2" hits
  [[ -z "$paths" ]] && return 0
  # Path-based hits (any location).
  local path_hits ext_hits
  path_hits="$(printf '%s\n' "$paths" | rg "$PATH_RULE_RE" || true)"
  # Extension-based hits, excluding the tests/test_data/ synthetic allowlist.
  ext_hits="$(printf '%s\n' "$paths" | rg -v '^tests/test_data/' | rg "$EXT_RULE_RE" || true)"
  hits="$(printf '%s\n%s\n' "$path_hits" "$ext_hits" | awk 'NF' | sort -u)"
  if [[ -n "$hits" ]]; then
    printf '%s\n' "$hits" >&2
    fail "blocked data/model/cache paths are $label"
  fi
}

echo "== Security preflight: tracked file path audit =="
audit_paths tracked "$(git ls-files)"

echo "== Security preflight: staged file path audit =="
audit_paths staged "$(git diff --cached --name-only --diff-filter=ACMRTUXB)"

echo "== Security preflight: tracked secret pattern audit =="

if git rev-parse --verify HEAD >/dev/null 2>&1; then
  if git grep -n -I -P '(sk-(?!dummy|your|test)[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{20,}|OPENROUTER_API_KEY=\S+|GOOGLE_API_KEY=AIza|OPENAI_API_KEY=sk-(?!dummy|your|test))' HEAD -- . ':!frontend/node_modules' ':!frontend/dist' ':!scripts/security_preflight.sh'; then
    fail "possible real secret pattern found in tracked files"
  fi
else
  warn "HEAD does not exist yet; skipping committed-file secret scan."
fi

echo "== Security preflight: staged secret pattern audit =="

if git diff --cached -U0 -- . ':(exclude)frontend/node_modules' ':(exclude)frontend/dist' ':(exclude)scripts/security_preflight.sh' |
  rg -n -P '(sk-(?!dummy|your|test)[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{20,}|OPENROUTER_API_KEY=\S+|GOOGLE_API_KEY=AIza|OPENAI_API_KEY=sk-(?!dummy|your|test))'; then
  fail "possible real secret pattern found in staged files"
fi

echo "== Security preflight: local secret presence check =="

if [[ -f .env ]]; then
  warn ".env exists locally. This is expected for development but must remain ignored and untracked."
fi

echo "== Security preflight: rule-scoped staged audit (User Data & Privacy Policy) =="

# Rule set derived from AGENTS.md 'User Data & Privacy Policy'.
# Prints which specific rule fired and which file triggered it.
rule_violation=0
staged_files="$(git diff --cached --name-only --diff-filter=ACMRTUXB || true)"

if [[ -n "$staged_files" ]]; then
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    case "$f" in
      local_data/*|*/local_data/*)
        printf 'RULE local_data: %s\n' "$f" >&2; rule_violation=1 ;;
    esac
    case "$f" in
      *.env|.env|.env.*|*/.env|*/.env.*)
        printf 'RULE env-file: %s\n' "$f" >&2; rule_violation=1 ;;
    esac
    # Binary/data extensions with tests/test_data/ allowlist.
    case "$f" in
      *.pdf|*.cif|*.ckpt|*.pt|*.pth)
        case "$f" in
          tests/test_data/*)
            : # allowed synthetic fixture
            ;;
          *)
            printf 'RULE data-extension (%s outside tests/test_data/): %s\n' "${f##*.}" "$f" >&2
            rule_violation=1
            ;;
        esac
        ;;
    esac
  done <<< "$staged_files"

  # Rule: real-looking secret patterns in staged diff content.
  staged_diff="$(git diff --cached -U0 -- . ':(exclude)frontend/node_modules' ':(exclude)frontend/dist' ':(exclude)scripts/security_preflight.sh' || true)"
  if [[ -n "$staged_diff" ]]; then
    # Placeholder tokens we intentionally ignore.
    placeholder_re='(sk-(dummy|your|test|xxx|placeholder)|your-key-here|<[^>]+>|CHANGEME|REPLACE_ME)'
    # Real-looking secret regexes. Restrict OPENAI/OPENROUTER/GEMINI to
    # value shapes that begin with a plausible key character to avoid
    # matching empty assignments like OPENAI_API_KEY= or OPENAI_API_KEY="".
    hits="$(
      printf '%s\n' "$staged_diff" |
      grep -E -n '(^|[^A-Za-z0-9])sk-[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_-]{30,}|OPENROUTER_API_KEY=[A-Za-z0-9][^[:space:]"'\'']{15,}|OPENAI_API_KEY=[A-Za-z0-9][^[:space:]"'\'']{15,}|GEMINI_API_KEY=[A-Za-z0-9][^[:space:]"'\'']{15,}|GOOGLE_API_KEY=AIza[A-Za-z0-9_-]{20,}' |
      grep -Ev "$placeholder_re" || true
    )"
    if [[ -n "$hits" ]]; then
      printf 'RULE secret-pattern: staged diff contains real-looking secret(s):\n%s\n' "$hits" >&2
      rule_violation=1
    fi
  fi
fi

if [[ "$rule_violation" -ne 0 ]]; then
  fail "one or more User Data & Privacy Policy rules were violated (see above)"
fi

echo "Security preflight passed."
