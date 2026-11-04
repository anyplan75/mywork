# 예배·행사와 평상시 작업 사이를 바꾼다. 대리 영상 일시 정지도 여기에 둔다.

import json

from config.불러오기 import 프로젝트루트


def _파일():
    return 프로젝트루트() / "workflows" / "mode-switch" / "상태.json"


def 읽기():
    경로 = _파일()
    if not 경로.is_file():
        return {"모드": "감시대기", "대리영상일시정지": False}
    try:
        자료 = json.loads(경로.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"모드": "감시대기", "대리영상일시정지": False}
    return {
        "모드": 자료.get("모드") or "감시대기",
        "대리영상일시정지": bool(자료.get("대리영상일시정지")),
    }


def 적용(종류):
    if 종류 == "예배":
        자료 = {"모드": "예배·행사", "대리영상일시정지": True}
    else:
        자료 = {"모드": "감시대기", "대리영상일시정지": False}
    경로 = _파일()
    경로.write_text(json.dumps(자료, ensure_ascii=False), encoding="utf-8")
    return 자료


def 일시정지():
    return bool(읽기().get("대리영상일시정지"))
