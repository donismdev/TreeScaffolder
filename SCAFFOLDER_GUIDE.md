# 🌲 Tree Scaffolder 기술 설명서

이 문서는 "Tree Scaffolder" 도구의 내부 동작, 데이터 흐름, 핵심 로직을 상세히 설명하여 향후 유지보수 및 기능 추가 시 참조할 수 있도록 작성되었습니다.

---

## 1. 핵심 목적

텍스트로 정의된 트리 구조와 파일 내용을 기반으로, 지정된 경로에 디렉토리와 파일을 생성(스캐폴딩)하는 개발자용 생산성 도구입니다.

---

## 2. 구성 요소 (핵심 스크립트)

-   `gui_app.py`
    -   **역할**: 메인 GUI 애플리케이션 (Tkinter 기반).
    -   **주요 기능**: 사용자 입력(트리, 소스 코드) 처리, 루트 폴더 선택, `scaffold_core` 호출, 결과(Diff) 시각화, 실제 파일 생성 실행, 덮어쓰기 전 경고창 표시.

-   `scaffold_core.py`
    -   **역할**: 스캐폴딩 계획을 생성하는 **핵심 로직**.
    -   **주요 기능**: 입력된 텍스트를 파싱하여 `NodeItem` 리스트 생성, `v2_parser`를 호출하여 파일 내용 추출, 파일 시스템을 분석하여 생성/변경/충돌 상태를 담은 `Plan` 객체 생성.
    -   **특징**: **파일 시스템에 직접 쓰기 작업을 수행하지 않습니다 (NO I/O).** 오직 계획만 수립합니다.

-   `v2_parser.py`
    -   **역할**: 파일 내용 정의를 위한 **V2 포맷 파서**.
    -   **주요 기능**: `@@@FILE_BEGIN`과 `@@@FILE_END` 구문을 분석하여 파일 경로와 내용을 추출합니다.

-   `scaffold_from_tree.py`
    -   **역할**: GUI 없이 독립적으로 실행 가능한 **CLI 버전**.
    -   **주요 기능**: 스크립트 내 `TREE_TEXT` 변수를 읽어 `scaffold_core`를 호출하고 파일 시스템에 즉시 적용합니다.

-   `file_classifier.py` / `file_type_icons.json`
    -   **역할**: GUI의 트리 뷰에 표시될 파일/폴더 아이콘을 결정합니다.

-   `folder_selection_validator.py`
    -   **역할**: GUI에서 선택한 루트 폴더가 시스템 폴더 등 위험한 경로가 아닌지 검증하는 외부 스크립트입니다.

---

## 3. 입력 포맷

두 가지 종류의 텍스트 입력이 조합되어 하나의 계획을 만듭니다.

### 3.1. 스캐폴드 트리 구문

-   **목적**: 디렉토리 구조와 빈 파일을 정의합니다.
-   **규칙**:
    -   `@ROOT {{Root}}`: 스캐폴딩이 시작될 논리적 루트를 선언합니다.
    -   들여쓰기(탭 또는 4칸 공백)를 통해 부모-자식 관계를 표현합니다.
    -   이름 끝에 `/`가 있으면 디렉토리로, 없으면 파일로 인식합니다.

    ```
    @ROOT {{Root}}

    {{Root}}/
        NewModule/
            Public/
                NewModule.h
            Private/
                NewModule.cpp
            NewModule.Build.cs
    ```

### 3.2. 블록 구문 (V2)

-   **목적**: 파일 내용, 주석 또는 기타 정의된 블록의 실제 내용을 정의합니다.
-   **규칙**:
    -   `@@@<KEYWORD>_BEGIN [선택적 식별자]`로 블록 내용 정의를 시작합니다. `<KEYWORD>`는 대문자여야 합니다 (예: `FILE`, `COMMENT`).
    -   `@@@<KEYWORD>_END`로 내용 정의를 끝냅니다. `<KEYWORD>`는 시작 태그와 일치해야 합니다.
    -   **`@@@<KEYWORD>_BEGIN`과 `@@@<KEYWORD>_END` 사이의 모든 텍스트(줄바꿈, 공백 포함)는 어떤 가공도 없이 그대로 내용으로 추출됩니다.**
    -   정의되지 않은 `<KEYWORD>`를 가진 블록이나 블록 외부의 텍스트는 파서에 의해 무시됩니다.

#### 예시: 파일 내용 블록 (`FILE`)

```
@@@FILE_BEGIN {{Root}}/NewModule/NewModule.Build.cs
using UnrealBuildTool;

public class NewModule : ModuleRules
{
    public NewModule(ReadOnlyTargetRules Target) : base(Target)
    {
        // ...
    }
}

@@@FILE_END
```

#### 예시: 주석 블록 (`COMMENT`)

```
@@@COMMENT_BEGIN 이 블록은 파서에 의해 무시됩니다.
이 내용은 최종 결과물에 포함되지 않지만,
구문 분석기 자체는 이 블록을 인식하고 건너뜁니다.
@@@COMMENT_END
```

---

## 4. 데이터 흐름 및 실행 순서 (GUI 기준)

1.  **사용자 입력**: 사용자가 GUI의 "Scaffold Tree" 또는 "Source Code" 텍스트 영역에 내용을 입력하고 "Compute Diff"를 클릭합니다.
2.  **계획 생성 (`generate_plan`)**:
    -   `gui_app.py`는 두 텍스트 영역의 내용을 합쳐 `scaffold_core.generate_plan` 함수에 전달합니다.
    -   `scaffold_core`는 먼저 트리 구문을 파싱하여 기본적인 디렉토리/파일 구조(`planned_dirs`, `planned_files`)를 계획합니다.
    -   그 다음 `v2_parser.parse_v2_format`를 호출하여 V2 구문에서 파일 경로와 내용을 추출하고 `file_contents` 딕셔너리에 저장합니다.
    -   파일 시스템을 스캔하여 계획된 경로의 현재 상태(`new`, `exists`, `overwrite`, `conflict`)를 `path_states` 딕셔너리에 기록합니다.
    -   이 모든 정보가 담긴 `Plan` 객체가 `gui_app.py`로 반환됩니다.
3.  **결과 시각화**: `gui_app.py`는 `Plan` 객체를 사용하여 "Before"와 "After" 트리 뷰를 그립니다. `new`, `overwrite` 등의 상태에 따라 다른 색상과 아이콘이 표시됩니다.
4.  **스캐폴드 적용 (`on_apply`)**:
    -   사용자가 "Apply Scaffold"를 클릭합니다.
    -   `plan.path_states`에 `overwrite` 상태인 파일이 하나라도 있으면, **"기존 파일이 덮어쓰기 됩니다"** 라는 내용의 경고창을 띄워 사용자에게 최종 확인을 받습니다. 사용자가 거부하면 작업은 즉시 중단됩니다.
    -   사용자가 동의하면 `_execute_scaffold` 메소드가 호출됩니다.
5.  **파일 시스템 쓰기 (`_execute_scaffold`)**:
    -   계획된 디렉토리를 먼저 생성합니다 (`_ensure_dir`).
    -   그 다음, 계획된 파일을 생성/덮어쓰기 합니다 (`_ensure_file`).
    -   `_ensure_file` 함수는 `path.write_text(content, encoding='utf-8')`를 사용하여 파일을 씁니다. 이 방식은 **UTF-8 (BOM 없음)** 인코딩을 보장하며, 기존 파일이 있다면 내용을 완전히 덮어씁니다.
6.  **완료**: 모든 작업이 끝나면 로그가 기록되고, "Before/After" 뷰가 새로고침됩니다.

---

## 5. 중요 로직 상세

### 파일 덮어쓰기 (Overwrite) 로직

-   **판단 기준**: `scaffold_core.generate_plan`에서 파일 시스템의 경로(`path`)가 이미 존재하고(`path.exists()`), 계획된 파일이며(`path in plan.planned_files`), V2 포맷으로 파일 내용까지 정의되었을 때(`path.resolve() in plan.file_contents`), 해당 파일의 상태는 `'overwrite'`가 됩니다.
-   **실행**: `_ensure_file` 함수는 `is_overwrite` 플래그가 True일 때, `path.write_text()`를 사용하여 기존 파일을 열고 새로운 내용으로 덮어씁니다.

### 블록 내용 처리 (Verbatim)

-   **규칙**: `v2_parser.py`는 `@@@<KEYWORD>_BEGIN`과 `@@@<KEYWORD>_END` 태그 사이의 내용을 어떤 수정(예: 줄바꿈 제거, 공백 다듬기) 없이 **있는 그대로(verbatim)** 추출합니다. 따라서 V2 포맷에 입력된 줄바꿈, 공백 문자는 최종 결과물에 그대로 반영됩니다.

---

## 6. 환경 설정 (`config.json`)

애플리케이션의 동작을 제어하는 설정 파일입니다.

-   `enable_runtime_logging` (boolean)
    -   **`true`**: 애플리케이션 실행 시, 모든 동작과 오류를 기록하는 `runtime.log` 파일을 생성합니다. 이 로그는 GUI의 로그 패널보다 더 상세하며, 문제 해결에 유용합니다.
    -   **`false`**: `runtime.log` 파일을 생성하지 않습니다.

---

## 7. 키보드 단축키 (Keyboard Shortcuts)

애플리케이션은 `Resources/key_bindings_map.json` 파일에 정의된 키보드 단축키를 지원합니다.
현재 정의된 단축키 목록은 다음과 같습니다:

| 키 시퀀스      | 동작 (Action)                   | 설명                                                                 |
| :------------- | :------------------------------ | :------------------------------------------------------------------- |
| `Space`        | `Load Test Data`                | 테스트 데이터를 로드합니다 (텍스트/입력 위젯에 포커스가 없을 때만). |
| `Escape`       | `Reset Focus`                   | 현재 포커스를 해제하고 루트 창으로 이동합니다.                      |
| `` ` `` (Grave)| `Cycle Main Notebook Tabs`      | 메인 노트북 탭을 순환합니다 (텍스트/입력 위젯에 포커스가 없을 때만). |
| `1`            | `Cycle Before Notebook Tabs`    | 'Before' 패널의 노트북 탭을 순환합니다 (텍스트/입력 위젯에 포커스가 없을 때만). |
| `2`            | `Cycle After Notebook Tabs`     | 'After' 패널의 노트북 탭을 순환합니다 (텍스트/입력 위젯에 포커스가 없을 때만). |
| `3`            | `Cycle Editor Notebook Tabs`    | 'Editor' 패널의 노트북 탭을 순환합니다 (텍스트/입력 위젯에 포커스가 없을 때만). |
| `v`            | `Previous Folder`               | 이전에 선택했던 루트 폴더로 돌아갑니다.                               |
| `b`            | `Browse Folder`                 | 새 루트 폴더를 탐색하여 선택합니다.                                  |
| `c`            | `Clear Data`                    | 모든 편집기 내용과 계획된 데이터를 초기화합니다.                     |
| `d`            | `Compute Diff`                  | 현재 입력된 트리와 소스 코드를 기반으로 스캐폴딩 계획을 계산합니다. |
| `f`            | `Apply Scaffold`                | 계산된 스캐폴딩 계획을 파일 시스템에 적용합니다.                    |
