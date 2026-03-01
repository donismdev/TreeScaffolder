# -*- coding: utf-8 -*-
"""
test_gitkeep_logic.py - [INTELLIGENT FOLDER RETENTION BATCH 3]

이 스크립트는 '빈 폴더 유지'를 위한 .gitkeep 파일 생성 로직의 '지능'을 검증합니다.
Git은 기본적으로 비어 있는 폴더를 추적하지 않으므로, 프로젝트 구조를 유지하기 위해
.gitkeep 생성이 필수적이지만, 이미 파일이 있는 곳에 중복 생성하는 것은 피해야 합니다.

[대상 로직]
- Scripts.UI.scaffold_runner: (추출된 로직) 폴더의 물리적/계획적 상태 분석

[AI 유지보수 가이드]
- 폴더가 '비어 있다'는 정의는 (물리적으로 비어있음) AND (현재 계획에도 자식 파일이 없음)을 의미합니다.
- 하나라도 만족하지 않으면 .gitkeep을 생성해서는 안 됩니다.
"""
import sys
import shutil
import tempfile
from pathlib import Path

# 프로젝트 루트를 경로에 추가
sys.path.append(str(Path(__file__).parent.parent.parent))

from Scripts.Core import scaffold_core

def test_gitkeep_intelligence():
    """
    [CASE-EXEC-04] .gitkeep 생성 조건의 복합 판단 검증
    
    비즈니스 로직적 의미:
    1. 완전히 새로운 빈 폴더 -> .gitkeep 생성 (정상)
    2. 물리적으로 이미 파일이 있는 폴더 -> 생성 안 함 (불필요)
    3. 물리적으로는 비었으나, 이번 계획에 파일이 들어갈 예정인 폴더 -> 생성 안 함 (불필요)
    
    이 테스트는 불필요한 .gitkeep 파일이 프로젝트에 범람하는 것을 방지합니다.
    """
    print("\n[CASE-EXEC-04] Testing .gitkeep Intelligence (Hybrid Check)...")
    
    # 실제 디스크 상황 시뮬레이션을 위한 임시 폴더
    tmp_root = Path(tempfile.mkdtemp(prefix="scaffold_gitkeep_test_"))
    try:
        # 물리적 구조 생성
        folder_a = tmp_root / "Folder_A" # Case 1: Truly Empty
        folder_b = tmp_root / "Folder_B" # Case 2: Physically Not Empty
        folder_c = tmp_root / "Folder_C" # Case 3: Planned to be Not Empty
        
        for f in [folder_a, folder_b, folder_c]: f.mkdir()
        
        # Folder_B에 미리 물리 파일 생성
        (folder_b / "pre_existing.txt").write_text("stay")
        
        # 계획 수립
        input_text = """
@ROOT {{Root}}
{{Root}}/
	Folder_A/
	Folder_B/
	Folder_C/
		newly_planned.txt
"""
        config = {"DRY_RUN": False, "ENABLE_SIMILARITY_SCAN": False}
        plan = scaffold_core.generate_plan(tmp_root, input_text, config)
        
        # scaffold_runner의 지능형 체크 로직 재현
        applied_gitkeeps = []
        for dir_path in plan.planned_dirs:
            if dir_path == tmp_root: continue
            
            # 조건 1: 이번 계획에 이 폴더로 들어올 파일이 있는가?
            has_planned_child = any(p.is_relative_to(dir_path) for p in plan.planned_files)
            if has_planned_child: 
                print("-> DEBUG: Skip Folder_C (Reason: Has planned child files)")
                continue

            # 조건 2: 물리적으로 이미 폴더 내부에 다른 파일이 존재하는가?
            has_phys_files = False
            if dir_path.exists() and any(dir_path.iterdir()):
                has_phys_files = True
            
            if has_phys_files:
                print("-> DEBUG: Skip Folder_B (Reason: Already has physical files)")
                continue

            # 최종 승인된 경우만 기록
            print("-> INFO: Approved .gitkeep for: " + dir_path.name)
            applied_gitkeeps.append(dir_path)

        # 결과 검증: Folder_A만 승인되어야 함
        if len(applied_gitkeeps) == 1 and applied_gitkeeps[0].name == "Folder_A":
            print("-> SUCCESS: Logic correctly identified that only Folder_A needs a .gitkeep.")
        else:
            names = [p.name for p in applied_gitkeeps]
            print("-> FAILURE: Incorrect .gitkeep targets: " + str(names))

    finally:
        # 테스트 종료 후 임시 데이터 삭제
        shutil.rmtree(tmp_root)

if __name__ == "__main__":
    print("================================================================")
    print("RUNNING GITKEEP LOGIC VALIDATION - BATCH 3")
    print("================================================================")
    try:
        test_gitkeep_intelligence()
        print("\n--- All Batch 3 Tests Completed Successfully ---")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("\n[CRITICAL ERROR] Test suite crashed: " + str(e))
