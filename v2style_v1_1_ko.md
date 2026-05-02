# Text Patch Format Manual v1.1

## 0. 목적

이 포맷은 텍스트 파일을 안전하게 수정하기 위한 패치 포맷이다.

이 포맷은 C++, Unreal, include, 함수, 클래스, enum 같은 개념을 이해하지 않는다.

대상은 오직 텍스트 파일이다.

따라서 기능은 다음만 다룬다.

```
1. 파일 전체 내용 덮어쓰기2. 파일 안의 특정 텍스트 교체3. 파일 안의 특정 텍스트 뒤에 삽입4. 파일 맨 위에 삽입5. 파일 맨 아래에 삽입6. 특정 텍스트 제거7. 파일 내용 전체 비우기8. 특정 라인 이후 내용 비우기
```

중요한 제한:

```
파일 삭제 기능은 절대 제공하지 않는다.파일 자체를 삭제하는 키워드는 만들지 않는다.파일 이동 기능도 만들지 않는다.디렉터리 삭제 기능도 만들지 않는다.
```

---

# 1. 기본 형태

모든 키워드는 반드시 BEGIN / END 쌍을 가진다.

형태:

```
@@@KEYWORD_BEGIN {{Parameter}}내용@@@KEYWORD_END
```

예:

```
@@@FIND_BEGIN {{None}}PendingInteractionRequest.Reset();@@@FIND_END
```

단일 라인 키워드는 금지한다.

금지:

```
@@@FIND@@@REPLACE@@@PATCH_END만 단독 사용@@@DELETE_FILE
```

허용:

```
@@@FIND_BEGIN {{None}}찾을 텍스트@@@FIND_END
```

---

# 2. Parameter 규칙

`{{...}}` 영역을 Parameter라고 부른다.

예:

```
@@@PATCH_BEGIN {{Root}}/Source/ModeMercenary/Public/Runtime/MercenaryGameSessionRuntime.h
```

여기서 `{{Root}}/Source/ModeMercenary/Public/Runtime/MercenaryGameSessionRuntime.h`가 Parameter다.

## 2.1 Parameter는 반드시 존재한다

모든 BEGIN 키워드는 Parameter를 가진다.

Parameter가 필요 없으면 반드시 다음을 쓴다.

```
{{None}}
```

예:

```
@@@FIND_BEGIN {{None}}찾을 텍스트@@@FIND_END
```

## 2.2 파일 경로 Parameter

파일 경로가 필요한 키워드는 반드시 `{{Root}}` 기준 경로를 사용한다.

예:

```
@@@FILE_BEGIN {{Root}}/Source/Example/Public/ExampleTypes.h@@@PATCH_BEGIN {{Root}}/Source/Example/Private/Example.cpp
```

금지:

```
C:/Users/...Source/Example/...../Source/Example/..../Source/Example/...
```

## 2.3 의미 없는 개념명 Parameter 금지

다음 같은 개념명은 쓰지 않는다.

```
{{IncludeSection}}{{PublicFunctionSection}}{{DelegateSection}}{{PrivateArea}}{{TargetFunction}}{{SomeBlock}}
```

이유:

```
툴은 C++ 구조를 이해하지 않는다.툴은 include, public, delegate, function 같은 개념을 모른다.실제 기준은 FIND에 들어간 텍스트뿐이다.개념명 Parameter는 AI가 임의로 만든 장식이 되기 쉽다.
```

따라서 파일 경로가 아닌 경우에는 거의 항상 다음을 쓴다.

```
{{None}}
```

---

# 3. 지원 키워드 목록

지원 키워드는 아래만 둔다.

```
@@@FILE_BEGIN {{Root}}/Path@@@FILE_END@@@PATCH_BEGIN {{Root}}/Path@@@PATCH_END@@@FIND_BEGIN {{None}}@@@FIND_END@@@REPLACE_BEGIN {{None}}@@@REPLACE_END@@@INSERT_AFTER_BEGIN {{None}}@@@INSERT_AFTER_END@@@INSERT_TOP_BEGIN {{None}}@@@INSERT_TOP_END@@@INSERT_BOTTOM_BEGIN {{None}}@@@INSERT_BOTTOM_END@@@REMOVE_BEGIN {{None}}@@@REMOVE_END@@@CLEAR_FILE_BEGIN {{Root}}/Path@@@CLEAR_FILE_END@@@CLEAR_AFTER_BEGIN {{None}}@@@CLEAR_AFTER_END@@@COMMENT_BEGIN {{None}}@@@COMMENT_END
```

지원하지 않는 키워드:

```
@@@DELETE_FILE_BEGIN@@@DELETE_FILE_END@@@MOVE_FILE_BEGIN@@@MOVE_FILE_END@@@DELETE_DIRECTORY_BEGIN@@@DELETE_DIRECTORY_END@@@INCLUDE_ADD_BEGIN@@@ADD_FUNCTION_BEGIN@@@REPLACE_STRUCT_BEGIN@@@REPLACE_CLASS_BEGIN
```

이 포맷은 파일/텍스트 수정 포맷이지 C++ 구조 수정 포맷이 아니다.

---

# 4. 파일 삭제 금지 원칙

파일 삭제 기능은 절대 넣지 않는다.

금지 키워드:

```
@@@DELETE_FILE_BEGIN@@@DELETE_FILE_END@@@MOVE_FILE_BEGIN@@@MOVE_FILE_END@@@DELETE_DIRECTORY_BEGIN@@@DELETE_DIRECTORY_END
```

금지 이유:

```
잘못된 Parameter 해석으로 엉뚱한 파일이 삭제될 수 있다.경로 계산 오류가 생기면 말도 안 되는 영역의 파일을 지울 수 있다.자동화 도구가 실수했을 때 복구 비용이 너무 크다.패치 포맷은 안전해야 하므로 파괴적 작업을 제공하지 않는다.
```

파일을 없애고 싶을 때도 실제 파일 삭제는 하지 않는다.

대신 가능한 선택지는 다음뿐이다.

```
1. 파일 내용을 빈 파일로 만든다.2. 파일 내용 일부를 제거한다.3. 파일 내용을 새 내용으로 덮어쓴다.4. 사용자가 수동으로 삭제한다.
```

즉, 툴은 파일 시스템에서 파일 자체를 지우지 않는다.

---

# 5. FILE

파일 전체 내용을 덮어쓴다.

형태:

```
@@@FILE_BEGIN {{Root}}/Path/File.h파일 전체 내용@@@FILE_END
```

의미:

```
해당 파일의 내용을 블록 안의 전체 내용으로 교체한다.
```

규칙:

```
파일 일부만 넣지 않는다.FILE은 항상 전체 파일 덮어쓰기다.@@@FILE_END 바로 위에는 빈 줄 1줄을 둔다.파일과 파일 사이에는 빈 줄 2줄을 둔다.
```

주의:

```
FILE은 강력한 덮어쓰기 작업이다.툴은 적용 전 기존 파일 백업 또는 변경 미리보기를 제공하는 것이 좋다.툴은 경로가 {{Root}} 내부인지 반드시 확인해야 한다.
```

---

# 6. PATCH

파일 일부를 수정한다.

형태:

```
@@@PATCH_BEGIN {{Root}}/Path/File.h패치 내용@@@PATCH_END
```

PATCH 안에서 사용할 수 있는 키워드:

```
@@@FIND_BEGIN / @@@FIND_END@@@REPLACE_BEGIN / @@@REPLACE_END@@@INSERT_AFTER_BEGIN / @@@INSERT_AFTER_END@@@INSERT_TOP_BEGIN / @@@INSERT_TOP_END@@@INSERT_BOTTOM_BEGIN / @@@INSERT_BOTTOM_END@@@REMOVE_BEGIN / @@@REMOVE_END@@@CLEAR_AFTER_BEGIN / @@@CLEAR_AFTER_END@@@COMMENT_BEGIN / @@@COMMENT_END
```

PATCH는 파일 삭제를 하지 않는다.  
PATCH는 오직 파일 내용만 수정한다.

---

# 7. FIND

수정 기준이 되는 텍스트를 찾는다.

형태:

```
@@@FIND_BEGIN {{None}}찾을 텍스트@@@FIND_END
```

예:

```
@@@FIND_BEGIN {{None}}PendingInteractionRequest.Reset();@@@FIND_END
```

FIND 다음에는 보통 다음 중 하나가 온다.

```
REPLACEINSERT_AFTERREMOVECLEAR_AFTER
```

주의:

```
FIND는 텍스트 기준이다.툴은 C++ 문법을 해석하지 않는다.같은 FIND 텍스트가 여러 번 나오면 위험하다.기본 적용 정책은 “정확히 1회만 매칭되어야 성공”으로 한다.
```

---

# 8. REPLACE

직전 FIND로 찾은 텍스트를 새 텍스트로 교체한다.

형태:

```
@@@FIND_BEGIN {{None}}기존 텍스트@@@FIND_END@@@REPLACE_BEGIN {{None}}새 텍스트@@@REPLACE_END
```

예:

```
@@@PATCH_BEGIN {{Root}}/Source/Example/Private/Example.cpp@@@FIND_BEGIN {{None}}PendingInteractionRequest.Reset();@@@FIND_END@@@REPLACE_BEGIN {{None}}PendingInteractionRequest.Reset();PendingReturnOpportunity = FMercenaryReturnOpportunity();@@@REPLACE_END@@@PATCH_END
```

적용 의미:

```
기존 텍스트를 찾아 새 텍스트로 교체한다.
```

---

# 9. INSERT_AFTER

직전 FIND로 찾은 텍스트 바로 뒤에 새 텍스트를 삽입한다.

형태:

```
@@@FIND_BEGIN {{None}}기준 텍스트@@@FIND_END@@@INSERT_AFTER_BEGIN {{None}}추가 텍스트@@@INSERT_AFTER_END
```

예:

```
@@@PATCH_BEGIN {{Root}}/Source/Example/Public/ExampleTypes.h@@@FIND_BEGIN {{None}}int32 Value = 0;@@@FIND_END@@@INSERT_AFTER_BEGIN {{None}}int32 NextValue = 0;@@@INSERT_AFTER_END@@@PATCH_END
```

적용 의미:

```
기준 텍스트를 찾고 그 바로 뒤에 추가 텍스트를 넣는다.
```

INSERT_BEFORE는 만들지 않는다.

이유:

```
기능을 줄이기 위해서다.대부분 FIND 기준을 앞쪽 텍스트로 잡고 INSERT_AFTER로 해결할 수 있다.키워드가 많아질수록 포맷이 흔들린다.
```

---

# 10. INSERT_TOP

파일 맨 위에 텍스트를 삽입한다.

형태:

```
@@@PATCH_BEGIN {{Root}}/Path/File.h@@@INSERT_TOP_BEGIN {{None}}추가할 텍스트@@@INSERT_TOP_END@@@PATCH_END
```

의미:

```
파일 가장 앞에 텍스트를 추가한다.
```

주의:

```
툴은 C++ 문법을 모른다.#pragma once 위에 들어가도 툴은 판단하지 않는다.사용자가 넣은 그대로 파일 맨 위에 삽입한다.
```

---

# 11. INSERT_BOTTOM

파일 맨 아래에 텍스트를 삽입한다.

형태:

```
@@@PATCH_BEGIN {{Root}}/Path/File.cpp@@@INSERT_BOTTOM_BEGIN {{None}}추가할 텍스트@@@INSERT_BOTTOM_END@@@PATCH_END
```

의미:

```
파일 가장 뒤에 텍스트를 추가한다.
```

주의:

```
파일 끝 개행 처리는 툴에서 안정적으로 보정하는 것이 좋다.기존 파일 끝에 개행이 없더라도 결과 파일은 개행으로 끝나게 한다.
```

---

# 12. REMOVE

직전 FIND로 찾은 텍스트를 제거한다.

형태:

```
@@@FIND_BEGIN {{None}}삭제할 텍스트@@@FIND_END@@@REMOVE_BEGIN {{None}}@@@REMOVE_END
```

예:

```
@@@PATCH_BEGIN {{Root}}/Source/Example/Private/Example.cpp@@@FIND_BEGIN {{None}}DebugOnlyFunction();@@@FIND_END@@@REMOVE_BEGIN {{None}}@@@REMOVE_END@@@PATCH_END
```

의미:

```
FIND로 찾은 텍스트를 파일 내용에서 제거한다.
```

규칙:

```
REMOVE 본문은 비워둔다.제거 대상은 직전 FIND의 내용이다.매칭이 정확히 1회일 때만 적용한다.
```

---

# 13. CLEAR_FILE

파일 내용 전체를 비운다.

형태:

```
@@@CLEAR_FILE_BEGIN {{Root}}/Path/File.h@@@CLEAR_FILE_END
```

의미:

```
파일은 그대로 두고, 파일 안의 내용만 전부 삭제한다.결과적으로 빈 파일이 된다.
```

중요:

```
CLEAR_FILE은 파일 삭제가 아니다.파일 시스템에서 파일은 남아 있어야 한다.내용만 빈 상태가 된다.
```

안전 규칙:

```
툴은 CLEAR_FILE 적용 전에 반드시 경고해야 한다.툴은 대상 경로가 {{Root}} 내부인지 확인해야 한다.툴은 대상이 파일인지 확인해야 한다.툴은 디렉터리에는 절대 적용하지 않는다.툴은 가능하면 적용 전 백업을 만든다.툴은 적용 전 변경 미리보기를 제공하는 것이 좋다.
```

권장 2중 체크:

```
1차 체크: 경로가 {{Root}} 내부인가?2차 체크: 대상이 실제 파일인가?3차 체크: 사용자가 CLEAR_FILE을 명시했는가?
```

---

# # 14. CLEAR_AFTER

`CLEAR_AFTER`는 파일 맨 위부터 아래로 탐색하면서, `FIND`로 지정한 텍스트가 **처음 등장한 위치**를 기준으로 그 아래 내용을 전부 비운다.

형태:

```
@@@PATCH_BEGIN {{Root}}/Path/File.h@@@FIND_BEGIN {{None}}기준 텍스트@@@FIND_END@@@CLEAR_AFTER_BEGIN {{None}}@@@CLEAR_AFTER_END@@@PATCH_END
```

의미:

```
파일 맨 위부터 FIND 텍스트를 검색한다.처음 찾은 FIND 텍스트는 결과에 남긴다.처음 찾은 FIND 텍스트가 포함된 라인도 결과에 남긴다.그 라인 아래의 모든 내용은 삭제한다.
```

예:

```
@@@PATCH_BEGIN {{Root}}/Source/Example/Public/ExampleTypes.h@@@FIND_BEGIN {{None}}#include "CoreMinimal.h"@@@FIND_END@@@CLEAR_AFTER_BEGIN {{None}}@@@CLEAR_AFTER_END@@@PATCH_END
```

적용 전:

```
#pragma once#include "CoreMinimal.h"#include "SomethingElse.h"struct FExample{};
```

적용 후:

```
#pragma once#include "CoreMinimal.h"
```

규칙:

```
CLEAR_AFTER 본문은 비워둔다.FIND 텍스트는 결과에 남긴다.FIND 텍스트가 포함된 라인도 결과에 남긴다.파일 맨 위부터 검색했을 때 처음 발견된 매칭만 사용한다.첫 번째 매칭 라인 아래의 내용만 제거한다.FIND 텍스트가 여러 번 있어도 첫 번째 매칭만 기준으로 삼는다.FIND 텍스트가 없으면 적용하지 않고 실패 처리한다.
```

안전 규칙:

```
툴은 CLEAR_AFTER 적용 전에 반드시 경고해야 한다.툴은 FIND 텍스트가 없으면 실패 처리해야 한다.툴은 첫 번째 매칭 위치와 삭제될 라인 수를 미리보기로 보여주는 것이 좋다.툴은 적용 후 결과가 의도보다 과도하게 줄어들 수 있음을 알려야 한다.툴은 가능하면 변경 전 백업을 만든다.
```

---

# 15. COMMENT

패치 적용자에게 주는 메모다.

형태:

```
@@@COMMENT_BEGIN {{None}}메모 내용@@@COMMENT_END
```

의미:

```
COMMENT는 실제 파일 수정이 아니다.툴은 COMMENT를 적용하지 않는다.툴은 COMMENT를 로그나 미리보기 설명으로만 표시할 수 있다.
```

Parameter에는 긴 설명을 넣지 않는다.  
긴 설명은 COMMENT 본문에 적는다.

---

# 16. 안전 규칙

## 16.1 절대 금지

툴은 다음 작업을 절대 수행하지 않는다.

```
파일 삭제디렉터리 삭제파일 이동디렉터리 이동{{Root}} 밖 경로 수정와일드카드 경로 수정상대 경로 탈출 수정
```

금지 예:

```
../..\{{Root}}/../*?C:/Users/.../Users/.../home/...
```

## 16.2 경로 안전 검사

파일 경로를 받는 키워드는 다음뿐이다.

```
@@@FILE_BEGIN {{Root}}/Path@@@PATCH_BEGIN {{Root}}/Path@@@CLEAR_FILE_BEGIN {{Root}}/Path
```

모든 파일 경로는 다음 조건을 만족해야 한다.

```
반드시 {{Root}}로 시작한다.{{Root}} 밖으로 나갈 수 없다.상대 경로 탈출을 포함하지 않는다.와일드카드를 포함하지 않는다.디렉터리가 아니라 파일이어야 한다.
```

## 16.3 매칭 안전 검사

FIND를 사용하는 작업은 기본적으로 정확히 1회 매칭되어야 한다.

대상 작업:

```
REPLACEINSERT_AFTERREMOVECLEAR_AFTER
```

매칭 결과:

```
0회 매칭: 실패1회 매칭: 적용 가능2회 이상 매칭: 실패
```

이유:

```
동일 텍스트가 여러 곳에 있을 때 엉뚱한 위치가 수정될 수 있다.
```

## 16.4 파괴적 내용 변경 안전 검사

다음 작업은 내용 손실 가능성이 높으므로 별도 안전 검사를 한다.

```
FILECLEAR_FILECLEAR_AFTERREMOVE
```

권장 안전 체크:

```
1. 경로가 {{Root}} 내부인지 확인한다.2. 대상이 파일인지 확인한다.3. 적용 전 변경 미리보기를 만든다.4. 기존 파일 백업을 만든다.5. 사용자가 해당 작업을 명시했는지 확인한다.6. CLEAR_FILE / CLEAR_AFTER는 별도 경고를 표시한다.
```

---

# 17. 산출물 작성 예시

## 17.1 전체 파일 덮어쓰기

```
@@@FILE_BEGIN {{Root}}/Source/Example/Public/ExampleTypes.h#pragma once#include "CoreMinimal.h"struct FExampleTypes final{	int32 Value = 0;	bool IsValid() const	{		return Value > 0;	}};@@@FILE_END
```

## 17.2 텍스트 교체

```
@@@PATCH_BEGIN {{Root}}/Source/Example/Private/Example.cpp@@@FIND_BEGIN {{None}}Value = 1;@@@FIND_END@@@REPLACE_BEGIN {{None}}Value = 2;@@@REPLACE_END@@@PATCH_END
```

## 17.3 텍스트 뒤에 삽입

```
@@@PATCH_BEGIN {{Root}}/Source/Example/Private/Example.cpp@@@FIND_BEGIN {{None}}Initialize();@@@FIND_END@@@INSERT_AFTER_BEGIN {{None}}Refresh();@@@INSERT_AFTER_END@@@PATCH_END
```

## 17.4 파일 맨 위에 삽입

```
@@@PATCH_BEGIN {{Root}}/Source/Example/Private/Example.cpp@@@INSERT_TOP_BEGIN {{None}}// Generated by patch tool@@@INSERT_TOP_END@@@PATCH_END
```

## 17.5 파일 맨 아래에 삽입

```
@@@PATCH_BEGIN {{Root}}/Source/Example/Private/Example.cpp@@@INSERT_BOTTOM_BEGIN {{None}}void DebugExample(){}@@@INSERT_BOTTOM_END@@@PATCH_END
```

## 17.6 텍스트 제거

```
@@@PATCH_BEGIN {{Root}}/Source/Example/Private/Example.cpp@@@FIND_BEGIN {{None}}DebugOnlyFunction();@@@FIND_END@@@REMOVE_BEGIN {{None}}@@@REMOVE_END@@@PATCH_END
```

## 17.7 파일 내용 전체 비우기

```
@@@CLEAR_FILE_BEGIN {{Root}}/Source/Example/Private/OldStub.cpp@@@CLEAR_FILE_END
```

## 17.8 특정 텍스트 이후 전부 비우기

```
@@@PATCH_BEGIN {{Root}}/Source/Example/Public/ExampleTypes.h@@@FIND_BEGIN {{None}}#include "CoreMinimal.h"@@@FIND_END@@@CLEAR_AFTER_BEGIN {{None}}@@@CLEAR_AFTER_END@@@PATCH_END
```

---

# 18. 최종 고정 요약

최종 키워드는 이것만 사용한다.

```
@@@FILE_BEGIN {{Root}}/Path@@@FILE_END@@@PATCH_BEGIN {{Root}}/Path@@@PATCH_END@@@FIND_BEGIN {{None}}@@@FIND_END@@@REPLACE_BEGIN {{None}}@@@REPLACE_END@@@INSERT_AFTER_BEGIN {{None}}@@@INSERT_AFTER_END@@@INSERT_TOP_BEGIN {{None}}@@@INSERT_TOP_END@@@INSERT_BOTTOM_BEGIN {{None}}@@@INSERT_BOTTOM_END@@@REMOVE_BEGIN {{None}}@@@REMOVE_END@@@CLEAR_FILE_BEGIN {{Root}}/Path@@@CLEAR_FILE_END@@@CLEAR_AFTER_BEGIN {{None}}@@@CLEAR_AFTER_END@@@COMMENT_BEGIN {{None}}@@@COMMENT_END
```

절대 만들지 않는 키워드:

```
@@@DELETE_FILE_BEGIN@@@DELETE_FILE_END@@@MOVE_FILE_BEGIN@@@MOVE_FILE_END@@@DELETE_DIRECTORY_BEGIN@@@DELETE_DIRECTORY_END
```

핵심 원칙:

```
이 포맷은 텍스트 수정 포맷이다.C++ 구조를 이해하지 않는다.파일 삭제 기능은 절대 없다.파일을 없애야 할 때도 파일 내용만 비운다.파일 경로는 반드시 {{Root}} 기준이다.파일 경로가 아닌 Parameter는 거의 항상 {{None}}이다.FIND 기반 작업은 정확히 1회 매칭될 때만 적용한다.CLEAR_FILE과 CLEAR_AFTER는 위험 작업으로 보고 2중 또는 3중 체크한다.잘못된 삭제를 막기 위해 툴에는 파일 삭제 기능을 절대 넣지 않는다.
```