# -*- coding: utf-8 -*-
"""
test_v2_and_tree.py - [CORE LOGIC VALIDATION BATCH 1]

이 스크립트는 TreeScaffolder의 가장 심장부인 'V2 파서'와 '트리 해석 엔진'의 강건함을 검증합니다.
이 테스트가 실패한다는 것은 전체 시스템의 '데이터 해석 무결성'이 깨졌음을 의미하며,
최악의 경우 엉뚱한 경로에 파일이 생성되거나 소스 코드가 유실되는 결과를 초래할 수 있습니다.

[대상 모듈]
- Scripts.Core.v2_parser: Multipatch 블록(@FILE_BEGIN 등) 추출 로직
- Scripts.Core.scaffold_core: 인덴트 기반 트리 구조 분석 및 계획 수립

[AI 유지보수 가이드]
- 이 파일의 로직을 리팩토링할 때는 반드시 'Python-style Indentation Rule'을 엄격히 준수해야 합니다.
- 0.8 버전에서 발견된 'Indentation Jump' 버그가 재발하지 않도록 검증 루틴을 제거하지 마십시오.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가 (Scripts 폴더 접근용)
sys.path.append(str(Path(__file__).parent.parent.parent))

from Scripts.Core import scaffold_core, v2_parser

def test_v2_tag_mismatch():
    """
    [CASE-V2-01] 태그 불일치 및 미종료 블록 검증
    
    비즈니스 로직적 의미:
    LLM(ChatGPT 등)이 답변 도중 끊기거나, 사용자가 실수로 뒷부분을 누락하고 붙여넣었을 때
    시스템이 깨진 데이터를 정상으로 오해하여 파일을 오염시키는 것을 방지합니다.
    
    예상 결과: V2ParserError를 발생시켜 실행 자체를 안전하게 중단해야 함.
    """
    print("\n[CASE-V2-01] Testing Tag Mismatch (Unclosed Block)...")
    broken_v2 = """
@@@FILE_BEGIN {{Root}}/test.txt
This block has no end tag.
"""
    try:
        results = v2_parser.parse_v2_format(broken_v2)
        print("-> FAILURE: System accepted a broken block! This could lead to data corruption.")
    except v2_parser.V2ParserError as e:
        print("-> SUCCESS: Caught expected error: " + str(e))

def test_v2_duplicate_definitions():
    """
    [CASE-V2-02] 동일 파일 중복 정의 우선순위 검증
    
    비즈니스 로직적 의미:
    소스 코드 에디터 내에 동일한 파일 경로가 여러 번 등장할 경우, '마지막에 정의된 내용'이
    최종 결과물이 되어야 합니다. 이는 사용자가 코드를 수정하며 아래에 새 버전을 덧붙이는
    일반적인 습성을 지원하기 위함입니다.
    
    AI 주의사항: 딕셔너리 업데이트 순서가 뒤집히면 이전 버전이 최종본이 되는 대참사가 발생합니다.
    """
    print("\n[CASE-V2-02] Testing Duplicate Definitions (Last One Wins)...")
    dup_v2 = """
@@@FILE_BEGIN {{Root}}/dup.txt
First Content (Old Version)
@@@FILE_END

@@@FILE_BEGIN {{Root}}/dup.txt
Second Content (New Version - Should Win)
@@@FILE_END
"""
    results = v2_parser.parse_v2_format(dup_v2)
    print("-> INFO: Parser returned " + str(len(results)) + " blocks.")
    
    root = Path("C:/FakeRoot")
    config = {"DRY_RUN": True, "ENABLE_SIMILARITY_SCAN": False}
    plan = scaffold_core.generate_plan(root, dup_v2, config)
    
    final_content = plan.file_contents.get(root / "dup.txt")
    if final_content == "Second Content (New Version - Should Win)":
        print("-> SUCCESS: Last definition correctly prioritized in plan.")
    else:
        print("-> FAILURE: Wrong version survived: " + str(final_content))

def test_extreme_indentation():
    """
    [CASE-TREE-01] 들여쓰기 단계 점프(Indentation Jump) 차단 검증
    
    비즈니스 로직적 의미:
    루트(0단계) 바로 다음에 갑자기 3단계 들여쓰기가 나오는 식의 '비상식적 구조'를 감지합니다.
    이 테스트는 0.8 버전의 치명적 결함(비상식적 구조를 허용하여 엉뚱한 부모 아래 배치함)을 
    해결했는지 확인하는 핵심 안전장치입니다.
    
    재앙 시나리오: 이 검증이 없으면 폴더 구조가 뒤죽박죽되어 프로젝트 컴파일 자체가 불가능해집니다.
    """
    print("\n[CASE-TREE-01] Testing Extreme Indentation Jump...")
    weird_tree = """
@ROOT {{Root}}
{{Root}}/
			DeepChild.txt (Jumped from Depth 0 to Depth 3!)
"""
    root = Path("C:/FakeRoot")
    config = {"DRY_RUN": True, "ENABLE_SIMILARITY_SCAN": False}
    plan = scaffold_core.generate_plan(root, weird_tree, config)
    
    if plan.errors:
        print("-> SUCCESS: Caught illegal indentation jump: " + str(plan.errors[0]))
    else:
        print("-> FAILURE: System accepted an impossible tree structure! (Logic Regression)")

if __name__ == "__main__":
    print("================================================================")
    print("RUNNING CORE LOGIC VALIDATION - BATCH 1")
    print("================================================================")
    try:
        test_v2_tag_mismatch()
        test_v2_duplicate_definitions()
        test_extreme_indentation()
        print("\n--- All Batch 1 Tests Completed Successfully ---")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("\n[CRITICAL ERROR] Test suite crashed: " + str(e))
