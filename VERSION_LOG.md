# TreeScaffolder Version Log

## [v0.8.0] - 2026-03-01
### Added
- **Strict Indentation Validation**: 트리 해석 시 부모 노드보다 2단계 이상 깊은 들여쓰기를 감지하고 차단하는 안전장치 추가 (논리 무결성 강화).
- **Intelligent .gitkeep Logic**: 물리적 파일 존재 여부와 계획된 파일 여부를 모두 따져 비어있는 폴더에만 스마트하게 `.gitkeep` 생성.
- **Enhanced Execution Log**: 
    - 로그 상/하단 핵심 요약 중복 배치 (UX 가독성 개선).
    - `Actually Applied Detail Overview` 섹션 추가 (상세 동작 리스트).
    - 로그 내 모든 설명 섹션에 한/영 다국어 지원 적용.
- **UI Stability**: 에디터 붙여넣기 용량 제한(3MB) 도입으로 대용량 데이터 입력 시 프리징 방지.
- **Folder Check Enhancement**: '폴더 체크' 시 일반 파일과 `.gitkeep` 파일을 구분하여 상세 카운트 제공.

### Changed
- **Project Restructuring**: 
    - `Dev/`: 샘플 데이터 및 개발 리소스 통합 관리.
    - `Test/automation/`: 코어 로직 검증용 자동화 스크립트 고도화 (상세 주석 포함).
- **Log Logic**: 성공/실패 메시지 출력 시점을 로그 저장 직전으로 조정하여 로그 파일의 완결성 확보.

---

## [v0.5.0] - [Internal Alpha]
- **V2 Multipatch Format**: `@@@FILE_BEGIN` 형식을 통한 소스 코드 추출 엔진 도입.
- **Core Engine**: 트리 구조와 소스 코드를 병합하여 실행 계획(Plan)을 수립하는 알고리즘 구축.
- **Multi-language**: 한국어 및 영어 정식 지원 시작.

---

## [v0.1.0] - [Initial Concept]
- 기본 Tkinter GUI 레이아웃 설계.
- 텍스트 기반 폴더/파일 생성 프로토타입 구현.
