#!/bin/zsh
# 맥미니에서 실행합니다.
# 모든 Dev 프로젝트가 맥미니 CPU·디스크·화면·키체인을 쓰도록 워커를 상주로 붙입니다.
set -euo pipefail

LA="$HOME/Library/LaunchAgents"
LOG="$HOME/Library/Logs/CursorWorkers"
AGENT="${HOME}/.local/bin/agent"
CURSOR_AGENT="$HOME/Library/Application Support/Cursor/User/globalStorage/anysphere.cursor-agent-worker/agent-cli/.local/bin/cursor-agent"
if [[ -e "$CURSOR_AGENT" ]]; then
  AGENT="$CURSOR_AGENT"
fi
UIDN="$(id -u)"
DEV="$HOME/Dev"

# 빌드·노드·홈브루·자바까지 워커가 바로 쓰게 PATH를 넓힙니다.
PATH_VAL="$HOME/.local/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
PATH_VAL="$PATH_VAL:/Applications/Xcode.app/Contents/Developer/usr/bin"
PATH_VAL="$PATH_VAL:/Library/Developer/CommandLineTools/usr/bin"
if [[ -d "/Applications/Android Studio.app/Contents/jbr/Contents/Home/bin" ]]; then
  PATH_VAL="$PATH_VAL:/Applications/Android Studio.app/Contents/jbr/Contents/Home/bin"
fi

echo "쓰는 agent: $AGENT"
mkdir -p "$LA" "$LOG" \
  "$HOME/.local/share/cursor-agent-workers/"{all,gps,ronin,dev,modl,interpret,fishing,photo,rta,church,mywork}

if [[ ! -e "$AGENT" ]]; then
  echo "agent CLI 가 없습니다. Cursor를 한 번 실행한 뒤 다시 시도하세요."
  exit 1
fi

# 키체인이 잠기면 서명·네트워크 인증이 막힙니다. 잠금 시간만 늘립니다(암호는 저장하지 않음).
security set-keychain-settings -u -t 86400 "$HOME/Library/Keychains/login.keychain-db" 2>/dev/null \
  || security set-keychain-settings -u -t 86400 login.keychain 2>/dev/null \
  || true

write_worker() {
  local key="$1"
  local name="$2"
  shift 2
  # 남은 인자 = worker-dir 목록 (여러 개면 한 워커가 여러 프로젝트 폴더를 품음)
  local dirs=("$@")
  local label="com.anyplan.cursor-worker.$key"
  local args=""
  args+="    <string>$AGENT</string>\n"
  args+="    <string>worker</string>\n"
  args+="    <string>start</string>\n"
  local d
  for d in "${dirs[@]}"; do
    args+="    <string>--worker-dir</string>\n"
    args+="    <string>$d</string>\n"
  done
  args+="    <string>--name</string>\n"
  args+="    <string>$name</string>\n"
  args+="    <string>--data-dir</string>\n"
  args+="    <string>$HOME/.local/share/cursor-agent-workers/$key</string>\n"
  args+="    <string>--idle-release-timeout</string>\n"
  args+="    <string>0</string>\n"
  # 화면 조작·데스크톱 공유: 맥미니 리소스를 에이전트가 직접 쓰게 합니다.
  args+="    <string>--computer-use</string>\n"
  args+="    <string>--share-desktop</string>\n"
  args+="    <string>view_and_control</string>\n"

  cat > "$LA/$label.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key><array>
$(printf "%b" "$args")
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>ProcessType</key><string>Interactive</string>
  <key>Nice</key><integer>-5</integer>
  <key>LowPriorityIO</key><false/>
  <key>SoftResourceLimits</key><dict>
    <key>NumberOfFiles</key><integer>8192</integer>
    <key>NumberOfProcesses</key><integer>2048</integer>
  </dict>
  <key>EnvironmentVariables</key><dict>
    <key>PATH</key><string>$PATH_VAL</string>
    <key>HOME</key><string>$HOME</string>
    <key>LANG</key><string>ko_KR.UTF-8</string>
    <key>CURSOR_WORKER_IDLE_RELEASE_TIMEOUT</key><string>0</string>
  </dict>
  <key>StandardOutPath</key><string>$LOG/$key.out.log</string>
  <key>StandardErrorPath</key><string>$LOG/$key.err.log</string>
</dict></plist>
EOF
  plutil -lint "$LA/$label.plist" >/dev/null
}

cat > "$LA/com.anyplan.nosleep.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.anyplan.nosleep</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/caffeinate</string><string>-dimsu</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ProcessType</key><string>Interactive</string>
  <key>StandardOutPath</key><string>$LOG/nosleep.out.log</string>
  <key>StandardErrorPath</key><string>$LOG/nosleep.err.log</string>
</dict></plist>
EOF

# 전체 Dev를 한 워커가 품어, 어떤 프로젝트든 맥미니에서 돌릴 수 있게 합니다.
write_worker all "전체Dev @ JUN's Macmini" \
  "$DEV" \
  "$DEV/gps_trace" \
  "$DEV/Ronin_Controller" \
  "$DEV/church-modl-tf" \
  "$DEV/church" \
  "$DEV/live-interpret" \
  "$DEV/fishing_hint" \
  "$DEV/photo_hint" \
  "$DEV/RTA Station" \
  "$DEV/mywork"

# 프로젝트별 이름표(기기 선택에서 찾기 쉽게)
write_worker gps "gps_trace @ JUN's Macmini" "$DEV/gps_trace"
write_worker ronin "Ronin_Controller @ JUN's Macmini" "$DEV/Ronin_Controller"
write_worker dev "Dev @ JUN's Macmini" "$DEV"
write_worker modl "모들 @ JUN's Macmini" "$DEV/church-modl-tf" "$DEV/church"
write_worker interpret "live-interpret @ JUN's Macmini" "$DEV/live-interpret"
write_worker fishing "fishing_hint @ JUN's Macmini" "$DEV/fishing_hint"
write_worker photo "photo_hint @ JUN's Macmini" "$DEV/photo_hint"
write_worker rta "RTA Station @ JUN's Macmini" "$DEV/RTA Station"
write_worker church "church @ JUN's Macmini" "$DEV/church"
write_worker mywork "mywork @ JUN's Macmini" "$DEV/mywork"

for label in com.anyplan.nosleep \
  com.anyplan.cursor-worker.all \
  com.anyplan.cursor-worker.gps \
  com.anyplan.cursor-worker.ronin \
  com.anyplan.cursor-worker.dev \
  com.anyplan.cursor-worker.modl \
  com.anyplan.cursor-worker.interpret \
  com.anyplan.cursor-worker.fishing \
  com.anyplan.cursor-worker.photo \
  com.anyplan.cursor-worker.rta \
  com.anyplan.cursor-worker.church \
  com.anyplan.cursor-worker.mywork; do
  launchctl bootout "gui/$UIDN/$label" 2>/dev/null || true
  launchctl bootstrap "gui/$UIDN" "$LA/$label.plist" || launchctl load -w "$LA/$label.plist"
  launchctl kickstart -k "gui/$UIDN/$label" 2>/dev/null || true
done

sleep 8
echo '==== launchctl ===='
launchctl list | egrep 'anyplan' || true
echo '==== procs ===='
pgrep -lf 'worker start|caffeinate -dimsu' | sed -E 's/(--api-key|--auth-token)[= ][^ ]+/\1 ***/g' | head -50
echo '==== logs ===='
for f in "$LOG"/{all,gps,ronin,dev,modl,interpret,fishing,photo,rta,church,mywork}.out.log; do
  [ -f "$f" ] || continue
  echo "-- $(basename "$f")"
  tail -n 5 "$f"
done
echo "끝. 가능하면 「전체Dev @ JUN's Macmini」 또는 프로젝트명 @ JUN's Macmini 를 고르세요."
