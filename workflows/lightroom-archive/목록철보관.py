# 라이트룸이 꺼지면 목록철을 압축해 보관 폴더로 복사한다.

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from config.불러오기 import 깊게, 작업경로


def _파일():
    return Path(__file__).resolve().parent / "최근.json"


def 읽기():
    경로 = _파일()
    if not 경로.is_file():
        return {"일시": "", "이유": ""}
    try:
        자료 = json.loads(경로.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"일시": "", "이유": ""}
    return {"일시": 자료.get("일시") or "", "이유": 자료.get("이유") or ""}


def _저장(일시, 이유):
    자료 = {"일시": 일시 or "", "이유": 이유 or ""}
    _파일().write_text(json.dumps(자료, ensure_ascii=False), encoding="utf-8")
    return 자료


def _이유(설정):
    이유 = []
    if not 작업경로(설정, "사진목록철"):
        이유.append("보관 폴더 경로가 아직 없습니다")
    if not 깊게(설정, "라이트룸목록철원본"):
        이유.append("목록철 원본이 아직 없습니다")
    if not 이유:
        return ""
    return ". ".join(이유) + ". 보관은 건너뜁니다."


def 상태(설정):
    기록 = 읽기()
    if 기록.get("일시"):
        return 기록
    현재이유 = _이유(설정)
    if 현재이유:
        if 기록.get("이유") != 현재이유:
            return _저장("", 현재이유)
        return {"일시": "", "이유": 현재이유}
    if 기록.get("이유"):
        return 기록
    return {"일시": "", "이유": "아직 없음"}


def 반응(설정, 방금꺼짐):
    막힌이유 = _이유(설정)
    if not 방금꺼짐:
        return 상태(설정)
    if 막힌이유:
        return _저장("", 막힌이유)
    원본 = Path(깊게(설정, "라이트룸목록철원본"))
    대상폴더 = Path(작업경로(설정, "사진목록철"))
    if not 원본.exists():
        return _저장("", "목록철 원본 파일을 찾지 못해 건너뜁니다")
    대상폴더.mkdir(parents=True, exist_ok=True)
    시각 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    이름 = "목록철-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".zip"
    임시 = 대상폴더 / 이름
    try:
        with zipfile.ZipFile(임시, "w", compression=zipfile.ZIP_DEFLATED) as 압축:
            if 원본.is_dir():
                for 파일 in 원본.rglob("*"):
                    if 파일.is_file():
                        압축.write(파일, 파일.relative_to(원본.parent))
            else:
                압축.write(원본, 원본.name)
                곁 = 원본.with_suffix(".lrdata")
                if 곁.is_dir():
                    for 파일 in 곁.rglob("*"):
                        if 파일.is_file():
                            압축.write(파일, 파일.relative_to(원본.parent))
    except OSError:
        if 임시.exists():
            임시.unlink()
        return _저장("", "목록철을 압축하지 못했습니다")
    if shutil.disk_usage(대상폴더).free < 임시.stat().st_size:
        임시.unlink()
        return _저장("", "보관 폴더 공간이 부족합니다")
    return _저장(시각, "목록철을 보관했습니다")
