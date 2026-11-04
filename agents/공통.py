# 기기 작동기의 상태 보고와 모드 명령. 주소는 설정 파일에서만 읽는다.

import json
import os
import shutil
import signal
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from config.불러오기 import (
    관제기준,
    설정읽기,
    파일모듈,
    프로그램경로,
    프로젝트루트,
)


프로그램키 = ("프로프리젠터", "브이믹스", "파이널컷", "다빈치리졸브", "라이트룸")
