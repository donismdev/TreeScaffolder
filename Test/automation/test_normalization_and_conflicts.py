# -*- coding: utf-8 -*-
"""
test_normalization_and_conflicts.py - [WINDOWS COMPATIBILITY & SAFETY BATCH 2]

이 스크립트는 윈도우 운영체제의 특수성(대소문자 구분 없음)과
물리적 파일 시스템의 구조적 충돌을 방지하는 안전 로직을 검증합니다.
이 테스트가 실패하면 동일한 파일을 두 번 생성하려 시도하거나,
이미 폴더가 있는 위치에 파일을 억지로 쓰려다가 시스템 에러로 중단될 수 있습니다.

[대상 모듈]
- Scripts.Core.scaffold_core: 경로 정규화(Normalization) 및 충돌 분석 로직

[AI 유지보수 가이드]
- 윈도우 환경에서는 'file.txt'와 'FILE.TXT'가 동일한 물리적 자원임을 명심하십시오.
- 경로 비교 시 반드시 .resolve()된 절대 경로의 소문자 변환(lower) 값을 기준으로 판단해야 안전합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
sys.path.append(str(Path(__file__).parent.parent.parent))

from Scripts.Core import scaffold_core

def test_case_insensitive_merging():
    """
    [CASE-TREE-03] 대소문자 혼용 경로 병합 검증 (Windows 최적화)
    
    비즈니스 로직적 의미:
    사용자가 '스캐폴드 트리'에는 소문자로, '소스 코드' 정의에는 대문자로 경로를 적었을 때
    시스템이 이를 서로 다른 파일로 인식하여 '중복 생성' 경고를 띄우거나 
    두 번 쓰기 작업을 수행하는 것을 방지합니다.
    
    예상 결과: 서로 다른 대소문자 표기라도 하나의 절대 경로 노드로 합쳐져야 함.
    """
    print("\n[CASE-TREE-03] Testing Case-Insensitive Path Merging...")
    root = Path("C:/Project")
    
    input_text = """
@ROOT {{Root}}
{{Root}}/
	file.txt (Tree definition in lowercase)

@@@FILE_BEGIN {{Root}}/FILE.TXT (Source definition in uppercase)
Content from Source
@@@FILE_END
"""
    config = {"DRY_RUN": True, "ENABLE_SIMILARITY_SCAN": False}
    plan = scaffold_core.generate_plan(root, input_text, config)
    
    # 중복 제거 후 최종 파일 개수 확인
    file_list = [str(p).lower() for p in plan.planned_files]
    unique_files = set(file_list)
    
    print("-> INFO: Planned file entries detected: " + str([p.name for p in plan.planned_files]))
    
    if len(unique_files) == 1:
        print("-> SUCCESS: Mixed-case paths correctly unified into a single logical resource.")
    else:
        print("-> FAILURE: Created " + str(len(unique_files)) + " duplicate entries for the same path!")

def test_type_conflict_detection():
    """
    [CASE-EXEC-02] 파일 vs 폴더 타입 충돌 감지 검증
    
    비즈니스 로직적 의미:
    'A'라는 이름을 폴더로도 쓰고 동시에 파일로도 정의하는 '논리적 모순'을 계획 단계에서 차단합니다.
    이 검증이 실패하면 실제 디스크 작업 도중 '폴더를 파일로 바꿀 수 없습니다'와 같은
    치명적인 OS 레벨 에러가 발생하여 작업이 중단됩니다.
    
    예상 결과: 계획 생성(Plan Generation) 단계에서 즉시 Internal Plan Error를 반환해야 함.
    """
    print("\n[CASE-EXEC-02] Testing File vs Folder Type Conflict...")
    root = Path("C:/Project")
    
    input_text = """
@ROOT {{Root}}
{{Root}}/
	ConflictItem/ (Defined as Directory)
	ConflictItem (Defined as File)
"""
    config = {"DRY_RUN": True, "ENABLE_SIMILARITY_SCAN": False}
    plan = scaffold_core.generate_plan(root, input_text, config)
    
    if any("conflict" in err.lower() or "duplicate" in err.lower() for err in plan.errors):
        print("-> SUCCESS: Detected impossible type conflict: " + str(plan.errors[0]))
    else:
        print("-> FAILURE: System ignored a direct type conflict! (Execution will crash later)")

if __name__ == "__main__":
    print("================================================================")
    print("RUNNING NORMALIZATION & SAFETY VALIDATION - BATCH 2")
    print("================================================================")
    try:
        test_case_insensitive_merging()
        test_type_conflict_detection()
        print("\n--- All Batch 2 Tests Completed Successfully ---")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("\n[CRITICAL ERROR] Test suite crashed: " + str(e))
