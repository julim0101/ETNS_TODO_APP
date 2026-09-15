# ETNS 할일관리 앱

Python Flask + SQLite 로 만든 간단한 할 일 관리 웹 앱입니다.

## 기능
- 할 일 등록 (제목 / 메모 / 우선순위 / 마감일)
- 완료 체크 토글, 수정, 삭제
- 전체 / 진행중 / 완료 필터, 제목·메모 검색
- 완료 항목 일괄 정리
- 우선순위 → 마감일 순 자동 정렬, 마감 지난 항목 강조

## 실행 방법

```bash
cd ETNS_TODO_APP
python -m venv .venv
.venv\Scripts\activate      # Windows (PowerShell/CMD)
pip install -r requirements.txt
python app.py
```

브라우저에서 http://127.0.0.1:5000 접속.

데이터는 같은 폴더의 `todo.db` (SQLite) 에 저장되며, 최초 실행 시 자동 생성됩니다.

## 구성
```
ETNS_TODO_APP/
├─ app.py              # Flask 앱 + 라우트 + DB 처리
├─ requirements.txt
├─ templates/
│  ├─ base.html        # 공통 레이아웃
│  ├─ index.html       # 목록 / 등록 / 필터
│  └─ edit.html        # 수정 화면
└─ static/
   └─ style.css
```
