# 맥북에서 띄우는 관제 화면. 표준 라이브러리만 쓴다. 주소와 경로는 설정 파일에서만 읽는다.

import json
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

루트 = Path(__file__).resolve().parents[1]
if str(루트) not in sys.path:
    sys.path.insert(0, str(루트))

from config.불러오기 import (
    깊게,
    설정읽기,
    작업경로,
    파일모듈,
    포트번호,
    프로그램경로,
    프로젝트루트,
)

모드 = 파일모듈(프로젝트루트() / "workflows/mode-switch/모드.py", "모드전환")
대리 = 파일모듈(프로젝트루트() / "workflows/proxy-media/대리영상.py", "대리영상")
변환 = 파일모듈(프로젝트루트() / "workflows/path-convert/경로변환.py", "경로변환")
보관 = 파일모듈(프로젝트루트() / "workflows/lightroom-archive/목록철보관.py", "목록철보관")
음향 = 파일모듈(프로젝트루트() / "workflows/audio-preview/미리듣기.py", "미리듣기")

잠금 = threading.Lock()
보고들 = {}
명령들 = []
다음번호 = 1
작업현황 = {"대리": {}, "음향": {}}
연결캐시 = {}
연결시각 = 0.0

기기순서 = (
    ("맥북프로", "맥북프로"),
    ("맥미니", "맥미니"),
    ("아이맥", "아이맥"),
    ("윈도우", "윈도우 컴퓨터"),
    ("나스", "나스"),
    ("오라클클라우드", "오라클 클라우드"),
)
담당 = {
    "프로프리젠터": "맥북프로",
    "브이믹스": "윈도우",
    "파이널컷": "맥북프로",
    "다빈치리졸브": "맥북프로",
    "라이트룸": "맥북프로",
}
표시이름 = {
    "프로프리젠터": "프로프리젠터",
    "브이믹스": "브이믹스",
    "파이널컷": "파이널 컷",
    "다빈치리졸브": "다빈치 리졸브",
    "라이트룸": "라이트룸",
}
작동기기 = {"맥북프로", "맥미니", "아이맥", "윈도우"}


def 용량문구(바이트):
    기가 = float(바이트) / (1024 ** 3)
    return f"{기가:.1f}기가바이트"
