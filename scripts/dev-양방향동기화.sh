#!/bin/zsh
# 예전 폴더 복사(rsync) 방식은 쓰지 않습니다.
# Dev 미러링은 깃 기준입니다. → dev-깃동기화.sh
exec /bin/zsh "$HOME/Dev/mywork/scripts/dev-깃동기화.sh" "$@"
