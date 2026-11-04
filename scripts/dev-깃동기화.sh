#!/bin/zsh
# Dev 프로젝트는 깃(깃허브) 기준으로만 맞춥니다.
# 폴더 전체를 복사하지 않습니다. 커밋되지 않은 내용은 건드리지 않습니다.
# 깨끗한 저장소만 원격에서 받고, 앞서 있으면 원격으로 보냅니다.

set -u

LOG_DIR="$HOME/Library/Logs/DevSync"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/git-sync.log"
DEV="$HOME/Dev"
stamp() { date '+%Y-%m-%d %H:%M:%S'; }

echo "$(stamp) 깃 맞춤 시작 ($(hostname -s))" >> "$LOG"

sync_one() {
  local dir="$1"
  local name="${dir:t}"
  [[ -e "$dir/.git" ]] || return 0

  if ! git -C "$dir" remote get-url origin >/dev/null 2>&1; then
    echo "$(stamp) $name: origin 없음, 건너뜀" >> "$LOG"
    return 0
  fi

  # 커밋 없는 저장소는 건너뜀
  if ! git -C "$dir" rev-parse HEAD >/dev/null 2>&1; then
    echo "$(stamp) $name: 커밋 없음, 건너뜀" >> "$LOG"
    return 0
  fi

  git -C "$dir" fetch --prune origin >> "$LOG" 2>&1 || {
    echo "$(stamp) $name: fetch 실패" >> "$LOG"
    return 0
  }

  local dirty
  dirty=$(git -C "$dir" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$dirty" != "0" ]]; then
    echo "$(stamp) $name: 로컬 변경 있음, pull/push 안 함" >> "$LOG"
    return 0
  fi

  local branch
  branch=$(git -C "$dir" rev-parse --abbrev-ref HEAD 2>/dev/null) || return 0
  if [[ "$branch" == "HEAD" ]]; then
    echo "$(stamp) $name: detached HEAD, 건너뜀" >> "$LOG"
    return 0
  fi

  if git -C "$dir" rev-parse --verify "origin/$branch" >/dev/null 2>&1; then
    if git -C "$dir" pull --ff-only origin "$branch" >> "$LOG" 2>&1; then
      echo "$(stamp) $name: pull 완료 ($branch)" >> "$LOG"
    else
      echo "$(stamp) $name: pull 실패(빨리 감기만 허용)" >> "$LOG"
    fi
  else
    echo "$(stamp) $name: origin/$branch 없음" >> "$LOG"
  fi

  # 로컬이 앞서 있으면 보냄
  local ahead
  ahead=$(git -C "$dir" rev-list --count "origin/$branch..HEAD" 2>/dev/null || echo 0)
  if [[ "$ahead" != "0" && "$ahead" != "" ]]; then
    if git -C "$dir" push origin "$branch" >> "$LOG" 2>&1; then
      echo "$(stamp) $name: push 완료 ($branch, +$ahead)" >> "$LOG"
    else
      echo "$(stamp) $name: push 실패" >> "$LOG"
    fi
  fi
}

for dir in "$DEV"/*(N/); do
  sync_one "$dir"
done

echo "$(stamp) 깃 맞춤 끝" >> "$LOG"
exit 0
