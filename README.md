# ETNS 할일관리 앱

Python Flask 로 만든 간단한 할 일 관리 웹 앱입니다. `DATABASE_URL` 환경변수가
있으면 Supabase(Postgres) 를, 없으면 로컬 SQLite 를 사용합니다.

## 기능
- 할 일 등록 (제목 / 메모 / 우선순위 / 마감일)
- 완료 체크 토글, 수정, 삭제
- 전체 / 진행중 / 완료 필터, 제목·메모 검색
- 완료 항목 일괄 정리
- 우선순위 → 마감일 순 자동 정렬, 마감 지난 항목 강조

## 실행 방법 (로컬, SQLite)

```bash
cd ETNS_TODO_APP
python -m venv .venv
.venv\Scripts\activate      # Windows (PowerShell/CMD)
pip install -r requirements.txt
python app.py
```

브라우저에서 http://127.0.0.1:5000 접속.

데이터는 같은 폴더의 `todo.db` (SQLite) 에 저장되며, 최초 실행 시 자동 생성됩니다.
`DATABASE_URL` 을 설정하면 로컬에서도 Supabase 에 바로 연결해 테스트할 수 있습니다.

## Vercel 배포

이 저장소는 Vercel Python 런타임으로 바로 배포되도록 구성돼 있습니다.

- `api/index.py` — Vercel 진입점 (루트의 Flask `app` 을 WSGI 로 노출)
- `vercel.json` — 모든 요청을 `/api/index` 로 rewrite, `templates/`·`static/` 번들 포함

Vercel 대시보드에서 **Add New → Project → 이 GitHub 저장소 Import** 하면 됩니다.
빌드 설정은 건드릴 필요 없이 기본값 그대로 두면 됩니다.

## Supabase 연동 (프로덕션 DB)

Vercel 은 서버리스라 파일시스템이 읽기 전용이고 `/tmp` 도 인스턴스가
재활용되면 사라지므로, SQLite 만으로는 배포본에서 데이터가 유지되지
않습니다. 이 앱은 **Supabase(Postgres)** 를 붙이면 자동으로 그쪽을 쓰도록
만들어져 있습니다 — `app.py` 가 `DATABASE_URL` 유무로 SQLite/Postgres 를
가른다.

프로젝트: **20260915_ETNS_S** (조직 `ETNS`, 리전 `ap-northeast-2` 서울)

Vercel 프로젝트의 **Settings → Environment Variables** 에 아래 값이
설정돼 있어야 합니다 (Production 환경 기준으로 이미 등록됨):

| 환경변수 | 설명 |
|---|---|
| `DATABASE_URL` | Supabase Postgres 연결 문자열 (transaction pooler, port 6543) |

연결 문자열 형태:
```
postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require
```

Vercel 서버리스 함수는 커넥션이 짧고 많아지므로, direct connection(5432)이
아니라 **transaction pooler(6543)** 를 반드시 사용해야 합니다. 또한 pgbouncer
transaction 모드에서는 server-side prepared statement 를 재사용할 수 없어
`psycopg.connect(..., prepare_threshold=None)` 로 비활성화해 두었습니다.

다른 환경변수:

| 환경변수 | 설명 |
|---|---|
| `TODO_DB_PATH` | (SQLite 모드) 파일 경로 직접 지정 |
| `SECRET_KEY` | Flask 세션/flash 용 키 (운영 시 반드시 설정) |

## 구성
```
ETNS_TODO_APP/
├─ app.py              # Flask 앱 + 라우트 + DB 처리 (SQLite / Postgres 겸용)
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
