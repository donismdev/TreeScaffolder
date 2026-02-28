# -*- coding: utf-8 -*-
"""
folder_selection_validator.py - 극강 안전 버전 (v2.7)
프로젝트 전체 덮어쓰기 툴 전용 | Windows 전용 최적화
⚠️ Windows 전용 - 경로 우회 원천 차단 및 공용 폴더 보호 최우선
"""

import json
import os
import sys
from pathlib import Path
from typing import Set, List, Tuple, Union

def _check_is_relative_to(child: Path, parent: Path) -> bool:
    """Python 3.9 미만 호환 상대 경로 확인 헬퍼."""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False

# ==============================================================================
# ⚠️ CRITICAL SAFETY DATA - DO NOT REMOVE (이 데이터와 로직을 절대 삭제하지 마십시오)
# 이 섹션의 하드코딩된 경로는 외부 설정 파일(folder_safety_rules.json)이 유실되거나 
# 훼손되었을 때 프로젝트 전체를 보호하기 위한 '최후의 방어선'입니다. 
# 설정 파일이 존재할 경우 이 데이터와 '병합'되어 2중으로 검사됩니다.
# ==============================================================================
DEFAULT_FORBIDDEN_ENV = [
    "SystemRoot", "windir", "ProgramFiles", "ProgramFiles(x86)",
    "ProgramData", "Public", "APPDATA", "LOCALAPPDATA"
]
DEFAULT_ALLOWED_BASES = [
    "Desktop", "바탕 화면", "바탕화면", "Documents", "문서",
    "Projects", "프로젝트", "MyProjects", "Code", "개발", "Dev", 
    "workspace", "작업폴더", "AI-Projects", "개발프로젝트"
]
DEFAULT_DANGEROUS_ZONES = [
    "Downloads", "다운로드", "Pictures", "사진", "Videos", "비디오", "동영상",
    "Music", "음악", "Dropbox", "iCloudDrive"
]
# ==============================================================================

def _load_rules() -> dict:
    """설정 파일에서 폴더 안전 규칙을 로드합니다."""
    try:
        base_dir = Path(__file__).parent.parent.parent
        rules_path = base_dir / "Resources" / "folder_safety_rules.json"
        if rules_path.exists():
            with open(rules_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return {}

def get_forbidden_system_paths() -> Set[Path]:
    """시스템 보호 경로 목록을 반환합니다 (코드 기본값 + 설정 파일 병합)."""
    rules = _load_rules()
    
    # Merge hardcoded defaults with external rules
    env_vars = set(DEFAULT_FORBIDDEN_ENV)
    if "forbidden_env_vars" in rules:
        env_vars.update(rules["forbidden_env_vars"])
    
    forbidden: Set[Path] = set()
    for env_var in env_vars:
        if path_str := os.environ.get(env_var):
            p = Path(path_str)
            if p.exists():
                forbidden.add(p.resolve())
    
    system_drive = os.environ.get("SystemDrive", "C:")
    users_path = Path(system_drive) / "Users"
    if users_path.exists():
        for sub in ["Default", "Public"]:
            p = users_path / sub
            if p.exists():
                forbidden.add(p.resolve())
    return forbidden

def get_allowed_project_bases() -> Set[Path]:
    """허용되는 프로젝트 상위 폴더 목록 (코드 기본값 + 설정 파일 병합)."""
    rules = _load_rules()
    
    # Merge hardcoded defaults with external rules
    base_names = set(DEFAULT_ALLOWED_BASES)
    if "allowed_base_names" in rules:
        for cat in rules["allowed_base_names"].values():
            base_names.update(cat)

    home = Path.home().resolve()
    allowed: Set[Path] = set()
    for name in base_names:
        allowed.add(home / name)
    return allowed

def get_dangerous_zones() -> Set[Path]:
    """위험 구역 목록 (코드 기본값 + 설정 파일 병합 + OneDrive 자동 감지)."""
    rules = _load_rules()
    
    # Merge hardcoded defaults with external rules
    zone_names = set(DEFAULT_DANGEROUS_ZONES)
    if "dangerous_zones" in rules:
        for cat in rules["dangerous_zones"].values():
            zone_names.update(cat)

    home = Path.home().resolve()
    dangerous: Set[Path] = set()
    for name in zone_names:
        dangerous.add(home / name)

    # OneDrive 변종 검색 유지
    try:
        if home.exists():
            for item in home.iterdir():
                if item.is_dir() and "onedrive" in item.name.lower():
                    dangerous.add(item.resolve())
    except:
        pass
        
    return dangerous

def get_folder_info(path: Path) -> Tuple[bool, int]:
    """빈 폴더 여부 확인 (최대 20개까지만 정직하게 카운트)."""
    try:
        count = 0
        for _ in path.iterdir():
            count += 1
            if count > 20: # 21개째가 발견되면 중단
                break
        return count == 0, min(count, 20)
    except:
        return False, -1

def validate_folder(path_to_check: Union[str, Path]) -> dict:
    result = {
        "ok": False,
        "errors": [],
        "warnings": [],
        "resolved_path": None,
        "blocked_reason": None,
        "is_empty": None,
        "item_count": 0,
    }

    if not path_to_check:
        result["errors"].append("경로가 비어있습니다.")
        result["blocked_reason"] = "EMPTY_PATH"
        return result

    # 1. 경로 정규화 (절대 경로 확보)
    try:
        input_p = Path(path_to_check)
        if input_p.is_symlink():
            result["warnings"].append("심볼릭 링크가 감지되었습니다. 실제 대상 경로로 처리됩니다.")
        
        resolved_path = input_p.resolve()
        result["resolved_path"] = str(resolved_path)
    except Exception as e:
        result["errors"].append(f"경로 해석 실패: {e}")
        result["blocked_reason"] = "RESOLUTION_ERROR"
        return result

    if not resolved_path.exists():
        result["errors"].append("존재하지 않는 폴더입니다.")
        result["blocked_reason"] = "DOES_NOT_EXIST"
        return result
    if not resolved_path.is_dir():
        result["errors"].append("디렉토리가 아닙니다.")
        result["blocked_reason"] = "NOT_A_DIRECTORY"
        return result

    # 2. 실질적 쓰기 권한 체크
    if not os.access(str(resolved_path), os.W_OK):
        result["errors"].append("해당 폴더에 쓰기 권한이 없습니다.")
        result["blocked_reason"] = "READ_ONLY_DIRECTORY"
        return result

    # 3. 드라이브/네트워크 루트 차단
    if resolved_path.anchor == str(resolved_path):
        result["errors"].append("드라이브 또는 네트워크 루트는 프로젝트 경로로 사용할 수 없습니다.")
        result["blocked_reason"] = "IS_DRIVE_ROOT"
        return result

    home = Path.home().resolve()
    allowed_bases = get_allowed_project_bases()
    forbidden_system = get_forbidden_system_paths()
    dangerous_zones = get_dangerous_zones()

    # 4. 홈 디렉토리 및 공용 폴더 '루트' 철저 차단 (v2.7 핵심 부활)
    if resolved_path == home:
        result["errors"].append("사용자 홈 디렉토리 자체는 프로젝트 루트로 사용할 수 없습니다.")
        result["blocked_reason"] = "IS_HOME_ROOT"
        return result

    # [중요] 이름 기반 차단과 경로 기반 차단을 모두 사용하여 회귀 버그 방지
    base_names_to_block = {"desktop", "바탕 화면", "바탕화면", "documents", "문서"}
    is_base_root = (resolved_path.name.lower() in base_names_to_block) or \
                   any(resolved_path == base for base in allowed_bases)
    
    if is_base_root:
        result["errors"].append(
            f"공용 폴더 자체('{resolved_path.name}')를 프로젝트 루트로 잡는 것은 매우 위험합니다.\n"
            "반드시 그 안에 '전용 하위 폴더'를 새로 만들어 선택하세요."
        )
        result["blocked_reason"] = "IS_BASE_ROOT"
        return result

    # 5. 위험 구역 차단 (Downloads, OneDrive 등)
    for danger in dangerous_zones:
        # 물리적으로 존재하지 않는 위험구역 후보는 건너뜀
        if not danger.exists(): continue
        
        if resolved_path == danger or _check_is_relative_to(resolved_path, danger):
            result["errors"].append(f"개인 자료 및 동기화 구역('{danger.name}')은 보호를 위해 차단되었습니다.")
            result["blocked_reason"] = "INSIDE_DANGEROUS_FOLDER"
            return result

    # 6. 시스템 보호 폴더 차단
    for forbidden in forbidden_system:
        if resolved_path == forbidden or _check_is_relative_to(resolved_path, forbidden):
            result["errors"].append(f"시스템 보호 폴더입니다: {forbidden}")
            result["blocked_reason"] = "INSIDE_SYSTEM_DIR"
            return result

    # 7. 안전 베이스 체크 (홈 하위에 있다면 반드시 허용된 폴더 내부여야 함)
    if _check_is_relative_to(resolved_path, home):
        if not any(_check_is_relative_to(resolved_path, base) for base in allowed_bases):
            result["errors"].append(
                "홈 디렉토리 아래에서는 바탕화면, 문서, Projects 등 허용된 폴더 '내부'에만 프로젝트를 둘 수 있습니다."
            )
            result["blocked_reason"] = "NOT_IN_ALLOWED_BASE"
            return result
    else:
        # 외부 드라이브는 기본 허용하되 경고 표시
        result["warnings"].append("시스템 드라이브 외부 경로를 감지했습니다. 올바른 프로젝트 폴더인지 확인하세요.")

    # 8. 부가 체크: 숨김 폴더 경고 및 빈 폴더 검사
    if any(part.startswith('.') or part.startswith('$') for part in resolved_path.parts if part not in {".", ".."}):
        result["warnings"].append("주의: 경로에 숨김 폴더나 시스템 예약 항목(.git 등)이 포함되어 있습니다.")

    is_empty, count = get_folder_info(resolved_path)
    result["is_empty"] = is_empty
    result["item_count"] = count
    if not is_empty:
        count_str = "20개 이상" if count > 20 else f"{count}개"
        result["warnings"].append(f"⚠️ 폴더가 비어있지 않습니다 ({count_str} 항목). 기존 파일이 덮어써질 수 있습니다.")

    result["ok"] = True
    return result

def main():
    if len(sys.argv) < 2:
        result = {
            "ok": False,
            "errors": ["사용법: python folder_selection_validator.py <경로>"],
            "warnings": [],
            "resolved_path": None,
            "blocked_reason": "NO_PATH_PROVIDED",
            "is_empty": None,
            "item_count": 0
        }
    else:
        result = validate_folder(sys.argv[1])

    # Output JSON using UTF-8 explicitly to avoid CP949 issues on Windows
    json_output = json.dumps(result, separators=(',', ':'), ensure_ascii=False)
    sys.stdout.buffer.write(json_output.encode('utf-8'))
    sys.stdout.buffer.flush()

if __name__ == "__main__":
    main()
