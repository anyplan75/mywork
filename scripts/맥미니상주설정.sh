#!/bin/zsh
# 맥미니에서 한 번만 실행합니다.
# 뚜껑이 없는 상주 작업용으로 잠자기와 원격 로그인을 맞춥니다.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PUBKEY_FILE="$SCRIPT_DIR/맥미니공개키.txt"

echo "1) 원격 로그인(SSH) 켜기"
sudo systemsetup -setremotelogin on || true

echo "2) 잠자기 끄기(상주용)"
sudo pmset -a sleep 0 displaysleep 10 disksleep 0 hibernatemode 0 autopoweroff 0 standby 0 tcpkeepalive 1 womp 1

echo "3) 맥북 공개키 등록"
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
touch "$HOME/.ssh/authorized_keys"
chmod 600 "$HOME/.ssh/authorized_keys"
if [[ -f "$PUBKEY_FILE" ]]; then
  KEY="$(tr -d '\n' < "$PUBKEY_FILE")"
  if ! grep -qxF "$KEY" "$HOME/.ssh/authorized_keys"; then
    echo "$KEY" >> "$HOME/.ssh/authorized_keys"
    echo "공개키를 넣었습니다."
  else
    echo "공개키는 이미 있습니다."
  fi
else
  echo "같은 폴더에 맥미니공개키.txt 가 없습니다. 맥북에서 그 파일을 복사한 뒤 다시 실행하세요."
fi

echo "4) 현재 전원 설정"
pmset -g custom

echo "끝. Cursor를 맥미니에 설치하고 Dev 폴더를 맞추면, 맥북 뚜껑을 닫아도 상주 작업이 이어집니다."
