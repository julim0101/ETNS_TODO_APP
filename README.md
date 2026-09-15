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

## Vercel 배포

이 저장소는 Vercel Python 런타임으로 바로 배포되도록 구성돼 있습니다.

- `api/index.py` — Vercel 진입점 (루트의 Flask `app` 을 WSGI 로 노출)
- `vercel.json` — 모든 요청을 `/api/index` 로 rewrite, `templates/`·`static/` 번들 포함

Vercel 대시보드에서 **Add New → Project → 이 GitHub 저장소 Import** 하면 됩니다.
빌드 설정은 건드릴 필요 없이 기본값 그대로 두면 됩니다.

### ⚠️ 서버리스에서의 데이터 저장 한계

Vercel 은 서버리스라 파일시스템이 읽기 전용이고, 쓰기 가능한 `/tmp` 도
**인스턴스가 재활용되면 사라집니다.** 따라서 배포본에서는:

- 할 일 데이터가 일정 시간 뒤 또는 배포 시 초기화됩니다
- 동시에 여러 인스턴스가 뜨면 서로 다른 데이터를 보게 됩니다

데모·UI 확인 용도로는 충분하지만, 실제로 데이터를 유지하려면 SQLite 대신
외부 DB(Vercel Postgres / Neon / Supabase / Turso 등)로 교체해야 합니다.

환경변수로 DB 위치를 지정할 수 있습니다.

| 환경변수 | 설명 |
|---|---|
| `TODO_DB_PATH` | SQLite 파일 경로 직접 지정 |
| `SECRET_KEY` | Flask 세션/flash 용 키 (운영 시 반드시 설정) |

## 구성
```
ETNS_TODO_APP/
├─ app.py              # Flask 앱 + 라우트 + DB 처리
├─ api/
│  └─ index.py         # Vercel 서버리스 진입점
├─ vercel.json         # Vercel 라우팅 / 번들 설정
├─ requirements.txt
├─ templates/
│  ├─ base.html        # 공통 레이아웃
│  ├─ index.html       # 목록 / 등록 / 필터
│  └─ edit.html        # 수정 화면
└─ static/
   └─ style.css
```
