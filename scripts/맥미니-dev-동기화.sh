#!/bin/zsh
# 맥미니에서 돌립니다. 맥북 Dev 와 서로 맞춥니다.
# 맥북이 꺼져 있으면 이번 회차는 건너뜁니다.

set -u

KEY="$HOME/.ssh/id_ed25519_tailscale"
# 맥미니에 맥북용 공개키만 있고 비밀열쇠가 없을 수 있어, 맥북 공개키로 들어간 뒤
# 맥미니에도 같은 이름 열쇠를 두거나, 맥북 호스트로 접속합니다.
LOCAL_DEV="$HOME/Dev"
REMOTE_HOST="juns-macbookpro.tail894959.ts.net"
REMOTE_USER="anyplan"
REMOTE_DEV="Dev"
LOG_DIR="$HOME/Library/Logs/DevSync"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/sync.log"
stamp() { date '+%Y-%m-%d %H:%M:%S'; }

# 맥미니에 맥북으로 가는 열쇠가 없으면, 맥북이 밀어 준 동기화만 믿고 끝냅니다.
if [[ ! -f "$KEY" ]]; then
  echo "$(stamp) 맥미니에 맥북행 열쇠 없음. 맥북 쪽 자동 맞춤만 사용." >> "$LOG"
  exit 0
fi

SSH=(ssh -o BatchMode=yes -o IdentitiesOnly=yes -i "$KEY" -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new)
RSH="ssh -o BatchMode=yes -o IdentitiesOnly=yes -i $KEY -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new"

if ! "${SSH[@]}" "$REMOTE_USER@$REMOTE_HOST" 'test -d "$HOME/Dev"' >/dev/null 2>&1; then
  echo "$(stamp) 맥북 연결 안 됨. 이번 회차 건너뜀." >> "$LOG"
  exit 0
fi

EXCLUDES=(
  --exclude '.DS_Store'
  --exclude '._*'
  --exclude '__pycache__'
  --exclude '.turbo'
  --exclude 'DerivedData'
  --exclude '.gradle/caches'
)

echo "$(stamp) 맥미니 -> 맥북 시작" >> "$LOG"
rsync -a --update "${EXCLUDES[@]}" -e "$RSH" "$LOCAL_DEV/" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DEV/" >> "$LOG" 2>&1
echo "$(stamp) 맥미니 -> 맥북 끝($?)" >> "$LOG"

echo "$(stamp) 맥북 -> 맥미니 시작" >> "$LOG"
rsync -a --update "${EXCLUDES[@]}" -e "$RSH" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DEV/" "$LOCAL_DEV/" >> "$LOG" 2>&1
echo "$(stamp) 맥북 -> 맥미니 끝($?)" >> "$LOG"

exit 0
