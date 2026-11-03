# 맥북프로 작동기. 상태 보고와 모드 명령만 한다.

import sys
from pathlib import Path

루트 = Path(__file__).resolve().parents[2]
if str(루트) not in sys.path:
    sys.path.insert(0, str(루트))

from agents.공통 import 루프


if __name__ == "__main__":
    루프("맥북프로")
