#!/usr/bin/env bash
set -Eeuo pipefail

REPOSITORY="appolon1908-hue/klyrow.com"
REPOSITORY_HTTPS="https://github.com/${REPOSITORY}.git"
REPOSITORY_SSH="git@github.com:${REPOSITORY}.git"
BRANCH="feat/klyrow-auth-theme-ui"
REQUIRED_ANCESTOR="a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e"
WORKSPACE="${KLYROW_CODEX_WORKSPACE:-/srv/codex-workspaces/klyrow.com}"
TASK_FILE="CODEX_MIDDLEWARE_SERVER_TASK.md"

log() {
  printf '%s\n' "$*"
}

fail() {
  printf 'ERROR=%s\n' "$*" >&2
  exit 1
}

command -v git >/dev/null 2>&1 || fail "git_not_installed"
command -v gh >/dev/null 2>&1 || fail "github_cli_not_installed"
command -v codex >/dev/null 2>&1 || fail "codex_cli_not_installed"

HOST_IPS="$(hostname -I 2>/dev/null || true)"
case " ${HOST_IPS} " in
  *" 65.109.65.169 "*|*" 10.40.0.1 "*) ;;
  *)
    fail "not_codestra_middleware_host HOSTNAME=$(hostname) HOST_IPS=${HOST_IPS:-unknown}"
    ;;
esac

log "HOSTNAME=$(hostname)"
log "HOST_IPS=${HOST_IPS:-unknown}"
log "CODEX_VERSION=$(codex --version 2>/dev/null || printf unknown)"

gh auth status --hostname github.com >/dev/null 2>&1 || fail "github_cli_not_authenticated"

case "$WORKSPACE" in
  /opt/klyrow|/opt/klyrow/*|/opt/codestra/compose|/opt/codestra/compose/*|/root/codestra-production-completion|/root/codestra-production-completion/*)
    fail "refusing_live_or_production_workspace WORKSPACE=$WORKSPACE"
    ;;
esac

mkdir -p "$(dirname "$WORKSPACE")"

if [[ ! -d "$WORKSPACE/.git" ]]; then
  if [[ -e "$WORKSPACE" ]] && [[ -n "$(find "$WORKSPACE" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
    fail "workspace_exists_but_is_not_git_repository WORKSPACE=$WORKSPACE"
  fi
  git clone "$REPOSITORY_HTTPS" "$WORKSPACE"
fi

cd "$WORKSPACE"

REMOTE="$(git remote get-url origin 2>/dev/null || true)"
case "$REMOTE" in
  "$REPOSITORY_HTTPS"|"$REPOSITORY_SSH"|"https://github.com/${REPOSITORY}"|"git://github.com/${REPOSITORY}.git") ;;
  *) fail "unexpected_repository_remote REMOTE=${REMOTE:-missing}" ;;
esac

if ! git diff --quiet || ! git diff --cached --quiet || [[ -n "$(git ls-files --others --exclude-standard)" ]]; then
  fail "working_tree_not_clean WORKSPACE=$WORKSPACE"
fi

git fetch --prune origin

if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git switch "$BRANCH"
else
  git show-ref --verify --quiet "refs/remotes/origin/$BRANCH" || fail "remote_branch_missing BRANCH=$BRANCH"
  git switch --track -c "$BRANCH" "origin/$BRANCH"
fi

git pull --ff-only origin "$BRANCH"

git merge-base --is-ancestor "$REQUIRED_ANCESTOR" HEAD || \
  fail "required_planning_ancestor_missing REQUIRED_ANCESTOR=$REQUIRED_ANCESTOR HEAD=$(git rev-parse HEAD)"

[[ -f "$TASK_FILE" ]] || fail "task_file_missing TASK_FILE=$TASK_FILE"

CURRENT_DIRECTORY="$(pwd)"
CURRENT_BRANCH="$(git branch --show-current)"
CURRENT_HEAD="$(git rev-parse HEAD)"

[[ "$CURRENT_BRANCH" == "$BRANCH" ]] || fail "wrong_branch CURRENT_BRANCH=$CURRENT_BRANCH"

log "CURRENT_DIRECTORY=$CURRENT_DIRECTORY"
log "REPOSITORY_REMOTE=$REMOTE"
log "CURRENT_BRANCH=$CURRENT_BRANCH"
log "STARTING_HEAD_SHA=$CURRENT_HEAD"
log "PLANNING_ANCESTOR_PRESENT=YES"
log "GIT_STATUS=$(git status --short | tr '\n' ';')"
log "TASK_FILE=$CURRENT_DIRECTORY/$TASK_FILE"
log "PRODUCTION_DEPLOYMENT=PROHIBITED"
log "LIVE_SERVICE_MUTATION=PROHIBITED"

TASK_CONTENT="$(cat "$TASK_FILE")"

# Use the installed Codex CLI without silently escalating its permissions.
# The host's existing Codex configuration controls approval and sandbox policy.
if codex --help 2>&1 | grep -qE '(^|[[:space:]])exec([[:space:]]|$)'; then
  exec codex exec "$TASK_CONTENT"
else
  exec codex "$TASK_CONTENT"
fi
