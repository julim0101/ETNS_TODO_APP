# 연결 작업 정리 (GitHub · Vercel · Supabase)

`ETNS_TODO_APP` 을 만든 뒤 지금까지 진행한 연결/배포 작업 전체를 정리한 문서입니다.
날짜는 모두 2026-09-15 기준입니다.

## 전체 구조

```
┌─────────────┐   git push    ┌──────────────┐   자동 재배포   ┌────────────────┐
│   로컬 PC    │ ────────────▶ │    GitHub    │ ──────────────▶ │     Vercel     │
│ ETNS_TODO_  │               │ julim0101/   │                 │ 20260915_etns_v│
│    APP      │               │ ETNS_TODO_APP│                 │  (jonguk1 계정) │
└─────────────┘               └──────────────┘                 └───────┬────────┘
                                                                        │ DATABASE_URL
                                                                        ▼
                                                                ┌────────────────┐
                                                                │   Supabase     │
                                                                │ 20260915_ETNS_S│
                                                                │ (Postgres, 서울)│
                                                                └────────────────┘
```

GitHub 저장소로 push 하면 Vercel 이 자동으로 감지해 재배포하고, 배포된 Flask 앱은
`DATABASE_URL` 환경변수를 통해 Supabase Postgres 에 데이터를 저장합니다.

---

## 1. GitHub

| 항목 | 값 |
|---|---|
| 저장소 | [github.com/julim0101/ETNS_TODO_APP](https://github.com/julim0101/ETNS_TODO_APP) |
| 공개 범위 | Public |
| 기본 브랜치 | `main` |
| 커밋 작성자 (이 저장소 한정) | `julim01 <julim01@etners.com>` |

**진행 과정**
1. 로컬에 `git init`, GitHub CLI(`gh`) 를 winget 으로 설치
2. 사용자가 직접 `gh auth login --web` 으로 브라우저 인증 (계정: `julim0101`)
3. `gh repo create ETNS_TODO_APP --public --source=. --push` 로 저장소 생성 및 최초 push

**이후 반영된 주요 커밋**
| 커밋 | 내용 |
|---|---|
| `af47f33` | Flask + SQLite 할일관리 앱 최초 작성 |
| `60eac94` | Vercel 배포용 구조 추가 (`api/index.py`, `vercel.json`) |
| `a674b8e` | Vercel 로컬 파일(`.vercel`, `.env*`) gitignore 처리 |
| `b509dbc` | 타임스탬프를 서버 UTC 대신 KST 로 표시하도록 수정 |
| `b12b983` | Supabase(Postgres) 연동, SQLite 는 로컬 fallback 으로 유지 |

**앞으로 코드를 수정하면**
```bash
cd C:\Users\etners\Desktop\ETNS_VIBE\ETNS_TODO_APP
git add -A && git commit -m "메시지" && git push
```
push 하는 순간 Vercel 이 자동으로 새 버전을 빌드·배포합니다 (아래 2번 참고).

---

## 2. Vercel

| 항목 | 값 |
|---|---|
| 프로젝트명 | `20260915_etns_v` |
| 계정 | `jonguk1` (GitHub 로그인) |
| 프로덕션 URL | https://20260915etnsv-xi.vercel.app |
| 대시보드 | https://vercel.com/jonguk1/20260915_etns_v |
| GitHub 연동 | `julim0101/ETNS_TODO_APP` — `main` 브랜치 push 시 자동 재배포 |

> 요청하신 이름 `20260915_ETNS_V` 는 Vercel 프로젝트명이 소문자만 허용해
> `20260915_etns_v` 로 생성했습니다.

**진행 과정**
1. Node.js LTS, Vercel CLI 를 winget/npm 으로 설치
2. 사용자가 직접 `vercel login --github` 으로 브라우저 인증
3. `vercel project add 20260915_etns_v` 로 프로젝트 생성
4. `vercel link` 로 로컬 폴더 ↔ 프로젝트 연결
5. `vercel git connect` 로 GitHub 저장소 연동
6. `vercel deploy --prod` 로 최초 프로덕션 배포

**배포를 위해 추가한 파일**
| 파일 | 역할 |
|---|---|
| [api/index.py](api/index.py) | Vercel Python 런타임 진입점. 루트의 Flask `app` 을 WSGI 로 노출 |
| [vercel.json](vercel.json) | 모든 요청을 `/api/index` 로 rewrite, `templates/`·`static/` 폴더 번들 포함 |
| `.vercelignore` | `.venv`, `__pycache__`, `todo.db` 등 배포에서 제외 |

**환경변수 (Production)**
| 이름 | 타입 | 설명 |
|---|---|---|
| `DATABASE_URL` | Secret | Supabase Postgres 연결 문자열 (3번 참고) |

**겪었던 이슈와 해결**
- Vercel 서버가 UTC 로 동작해 등록 시각이 9시간 어긋남 → `app.py` 에서 시간 계산을 KST(Asia/Seoul) 고정으로 수정 (`b509dbc`)
- 최초 `DATABASE_URL` 등록 시 PowerShell 파이프가 값 앞에 UTF-8 BOM 문자를 끼워넣어 배포가 500 에러 → BOM 없는 파일로 재작성해 재등록, 재배포로 해결

---

## 3. Supabase

| 항목 | 값 |
|---|---|
| 조직(Organization) | `ETNS` |
| 프로젝트명 | `20260915_ETNS_S` |
| 리전 | `ap-northeast-2` (서울) |
| DB 엔진 | PostgreSQL 17 |
| 상태 | `ACTIVE_HEALTHY` |
| 대시보드 | https://supabase.com/dashboard/project/qxqcfzdvlnviipvejcdw |

**진행 과정**
1. Supabase CLI 를 npm 으로 설치
2. 사용자가 직접 `supabase login` 으로 브라우저 인증
3. 계정에 조직이 없어 `supabase orgs create ETNS` 로 조직 생성
4. `supabase projects create 20260915_ETNS_S --org-id <ETNS 조직ID> --region ap-northeast-2` 로 프로젝트 생성
5. DB 비밀번호는 임의의 24자 랜덤 문자열로 자동 생성 (Vercel `DATABASE_URL` 환경변수에만 저장, 이 문서에는 기록하지 않음 — 필요하면 Vercel 프로젝트 설정에서 확인하거나, 분실 시 Supabase 대시보드에서 재설정 가능)

**연결 방식**
- Vercel(서버리스)은 커넥션이 짧고 많이 생성되므로, direct connection(5432)이 아니라
  **transaction pooler(6543, pgbouncer)** 를 사용합니다.
- 연결 문자열 형태:
  ```
  postgresql://postgres.<project-ref>:<password>@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres?sslmode=require
  ```
- pgbouncer transaction 모드는 서버측 prepared statement 를 커넥션 간 공유할 수 없어,
  앱 코드에서 `psycopg.connect(..., prepare_threshold=None)` 으로 비활성화해 두었습니다.

**앱 코드 쪽 변경 (`app.py`)**
- `DATABASE_URL` 환경변수가 있으면 Postgres(`psycopg`), 없으면 기존 SQLite 로 동작
- 로컬 개발은 지금까지처럼 SQLite 로 그대로 가능 (`DATABASE_URL` 을 안 주면 됨)
- `requirements.txt` 에 `psycopg[binary]` 추가

**검증**
- 로컬에서 Supabase DB에 직접 연결해 전체 라우트(등록/토글/수정/삭제/검색/필터/일괄정리) 스모크 테스트 통과
- 배포 사이트에서 항목을 추가한 뒤, 별도 연결로 Supabase DB를 직접 조회해 같은 행이 저장된 것을 확인 → 서버리스 인스턴스 재활용과 무관하게 데이터가 영구 보존됨을 확인

---

## 계정/자격 증명 요약

| 서비스 | 로그인 방식 | 계정 |
|---|---|---|
| GitHub | `gh auth login --web` (사용자 직접 승인) | `julim0101` |
| Vercel | `vercel login --github` (사용자 직접 승인) | `jonguk1` |
| Supabase | `supabase login` (사용자 직접 승인) | (Supabase 계정, org: `ETNS`) |

이 PC에 설치된 CLI 도구: GitHub CLI(`gh`), Node.js + Vercel CLI, Supabase CLI.
모두 winget/npm 으로 설치했고, 로그인 세션은 각 CLI 의 로컬 설정에 저장돼 있습니다.

## 참고: 서버리스 데이터 유지 한계 해소

Vercel 단독 배포 시점에는 파일시스템이 읽기 전용이라 SQLite 데이터가
인스턴스 재활용 때마다 사라지는 문제가 있었으나, Supabase 연동 이후에는
모든 데이터가 Postgres 에 영구 저장되어 이 문제가 해결되었습니다.
