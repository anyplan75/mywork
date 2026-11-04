#!/bin/zsh
# 맥미니에서 실행합니다. 모든 프로젝트 워커가 맥미니를 쓰려면 아래 권한이 켜져 있어야 합니다.
# 암호를 저장하지 않습니다. 화면에서 직접 허용만 해 주세요.
set -euo pipefail

echo "1) 로그인 키체인 잠금 시간 늘리기"
security set-keychain-settings -u -t 86400 "$HOME/Library/Keychains/login.keychain-db" 2>/dev/null \
  || security set-keychain-settings -u -t 86400 login.keychain 2>/dev/null \
  || true
# SSH로만 들어와 잠긴 경우, 아래가 암호를 한 번 물을 수 있습니다.
security unlock-keychain "$HOME/Library/Keychains/login.keychain-db" 2>/dev/null \
  || security unlock-keychain login.keychain 2>/dev/null \
  || echo "키체인 잠금 해제는 맥미니 화면에서 로그인되어 있으면 보통 자동입니다."

echo "2) 시스템 설정 권한 화면 열기 (각각 Cursor / Cursor Computer Use / agent 를 허용)"
# 전체 디스크 접근
open "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles" 2>/dev/null || true
sleep 1
# 손쉬운 사용(Accessibility)
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility" 2>/dev/null || true
sleep 1
# 화면 기록
open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture" 2>/dev/null || true
sleep 1
# 자동화(AppleEvents)
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Automation" 2>/dev/null || true
sleep 1
# 개발자 도구 / 백그라운드
open "x-apple.systempreferences:com.apple.LoginItems-Settings.extension" 2>/dev/null \
  || open "x-apple.systempreferences:com.apple.LoginItems-Settings" 2>/dev/null \
  || true

echo "3) 전원(이미 sleep=0 이면 그대로)"
pmset -g | egrep 'sleep|disksleep|hibernatemode|displaysleep' || true

echo
echo "허용할 앱(보이면 모두 켜기):"
echo "  - Cursor"
echo "  - Cursor Computer Use (또는 Cursor Agent Helper)"
echo "  - agent / node (목록에 있으면)"
echo "로그인 항목 → 앱이 백그라운드에서 수행하도록 허용 → agent 스위치 모두 켜기"
echo
echo "그다음: zsh /Users/anyplan/Dev/mywork/scripts/맥미니워커설정.sh"
