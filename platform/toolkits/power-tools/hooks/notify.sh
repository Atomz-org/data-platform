#!/usr/bin/env bash
# Stop / Notification hook — tell the human, who is not watching the terminal.
#
# The point of a long agent turn is that you go and do something else. This is
# what brings you back: a desktop notification, a short spoken line, and an
# append-only log so a session left running overnight is still readable.
#
# Off switches, because taste varies and open-plan offices exist:
#   PF_NOTIFY=0        no notifications at all
#   PF_NOTIFY_VOICE=0  desktop only, stay silent
#   PF_NOTIFY_LOG      log path (default ~/.claude/pf-task-log.txt)
#
# Always exits 0. On a Stop hook a non-zero exit means "do not stop", which
# would turn a notifier into an infinite loop.
set -uo pipefail

[ "${PF_NOTIFY:-1}" = "0" ] && exit 0

kind="${1:-stop}"
payload="$(cat 2>/dev/null || true)"
log="${PF_NOTIFY_LOG:-$HOME/.claude/pf-task-log.txt}"

field() { printf '%s' "$payload" | jq -r "$1 // empty" 2>/dev/null; }

cwd="$(field '.cwd')"
where="$(basename "${cwd:-$PWD}")"

case "$kind" in
  permission)
    title="Claude Code · needs you"
    body="$(field '.message')"
    body="${body:-Waiting for approval in ${where}}"
    spoken="I need your confirmation"
    ;;
  *)
    title="Claude Code · done"
    last="$(field '.last_assistant_message')"
    # One line, trimmed. The notification is a summons, not a transcript.
    body="$(printf '%s' "${last:-Task finished}" | tr '\n' ' ' | cut -c1-140)"
    spoken="Task completed"
    ;;
esac

mkdir -p "$(dirname "$log")" 2>/dev/null
printf '%s  [%s]  %s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$kind" "$where" "$body" >> "$log" 2>/dev/null

# macOS only. Elsewhere the log above is the whole feature.
if [ "$(uname)" = "Darwin" ]; then
  if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"${body//\"/\\\"}\" with title \"${title}\" subtitle \"${where}\"" >/dev/null 2>&1 || true
  fi
  if [ "${PF_NOTIFY_VOICE:-1}" != "0" ] && command -v say >/dev/null 2>&1; then
    # Backgrounded: `say` blocks for as long as it speaks, and a Stop hook that
    # blocks is a Stop hook that delays the next prompt.
    ( say "$spoken" >/dev/null 2>&1 & ) || true
  fi
fi

exit 0
