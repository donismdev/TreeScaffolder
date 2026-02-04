# 📁 Tree Scaffolder

> 텍스트로 작성한 트리 구조를 기반으로 폴더와 파일을 **안전하게** 생성하는 개발자용 스캐폴딩 도구

---

## 🧭 개요

**Tree Scaffolder**는 사람이 읽기 쉬운 트리 텍스트(들여쓰기 기반 DSL)를 입력하면,  
해당 구조대로 폴더와 빈 파일을 생성해주는 **로컬 개발자 생산성 도구**입니다.

- ❌ 기존 파일 덮어쓰기 없음 (exclusive create)
    
- ✅ 이미 존재하면 SKIP
    
- ⚠️ 위험한 경로(system32 등) 원천 차단
    
- 🔍 Before / After 구조 비교
    
- 🧱 확장자 → 아이콘 매핑 설정 가능
    
- 🖥️ Windows GUI 기반
    

---

## ✨ 주요 기능

---

### 1️⃣ 트리 텍스트 기반 구조 정의

`{{Root}}/     NewModule/         NewModule.Build.cs         Public/             NewModule.h         Private/             NewModule.cpp`

---

### 2️⃣ 안전한 생성 정책

- 기존 파일/폴더는 절대 덮어쓰지 않음
    
- 존재하면 자동 SKIP
    
- 파일 ↔ 폴더 충돌 시 에러
    

---

### 3️⃣ Before / After 비교 뷰

- 현재 폴더 구조 vs 생성 후 구조
    
- 새로 추가될 항목 하이라이트 표시
    
- 트리뷰에서 폴더 접기/펼치기 가능
    

---

### 4️⃣ 위험 경로 차단

- `C:\Windows`, `System32`, `Program Files`, 드라이브 루트 등 선택 불가
    
- 별도 `folder_selection_validator.py`로 안전성 검사
    

---

### 5️⃣ 아이콘 분류 시스템

- 파일 확장자를 **아이콘(이모지 키)** 기준으로 그룹화
    
- 외부 설정 파일에서 매핑 수정 가능
    

예시:

`{   "🎵": [".mp3", ".wav", ".ogg"],   "🖼️": [".png", ".jpg", ".jpeg"],   "🧩": [".cpp", ".c", ".hlsl"],   "📘": [".h", ".hpp"],   "📄": [] }`

---

## 🛠️ 사용 목적

---

- 새 모듈 / 새 기능 추가할 때 **폴더 + 빈 파일 구조 한 번에 생성**
    
- Unreal / C++ / C# / 스크립트 프로젝트 구조 빠르게 생성
    
- “파일부터 만들고 시작하는” 개발 스타일에 최적화된 툴
    

---

## 🚀 실행 방법

---

### 🖥️ GUI 버전

`python gui_app.py`

1. 트리 텍스트 입력
    
2. 루트 폴더 선택 (자동 안전 검사)
    
3. Before / After 비교 확인
    
4. 문제 없으면 **Apply Scaffold** 클릭
    

---

### 📄 Standalone 스크립트 사용

`scaffold_from_tree.py`를 **원하는 루트 폴더에 복사**한 뒤:

1. 파일 안의 `TREE_TEXT` 수정
    
2. 실행:
    

`python scaffold_from_tree.py`

- 해당 폴더 기준으로 구조 생성
    
- 기존 파일은 절대 덮어쓰지 않음
    

---

## 🔒 안전 정책

---

- ❌ 기존 파일 덮어쓰기 없음
    
- ❌ 시스템 디렉토리 대상 차단
    
- ❌ 드라이브 루트 차단
    
- ✅ 실패해도 가능한 부분은 계속 진행
    
- ✅ 요약 리포트 + 경고/에러 로그 출력
    

---

## 📄 License

---

This project is licensed under the **MIT License**.

---
