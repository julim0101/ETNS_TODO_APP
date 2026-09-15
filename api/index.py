"""Vercel Python 런타임 진입점.

프로젝트 루트의 Flask 앱(app.py)을 그대로 노출한다.
Vercel 의 Python 런타임이 모듈에서 `app` (WSGI 콜러블) 을 찾아 실행한다.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402,F401
