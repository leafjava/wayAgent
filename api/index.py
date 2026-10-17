"""Vercel 入口：把 Flask app 暴露成 serverless handler。"""
import sys
from pathlib import Path

# 把项目根目录加到 path（让 web_app 可 import）
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 自动加载 .env（如果存在，本地调试用；Vercel 用 Dashboard 配置）
try:
    from dotenv import load_dotenv
    env = ROOT / ".env"
    if env.exists():
        load_dotenv(env)
except ImportError:
    pass

from web_app import app  # noqa: E402,F401  Flask app 对象

class _OriginalPathMiddleware:
    def __init__(self, application):
        self.application = application

    def __call__(self, environ, start_response):
        from urllib.parse import parse_qs
        original = parse_qs(environ.get("QUERY_STRING", "")).get("__path", [None])[0]
        if original:
            environ["PATH_INFO"] = original
            environ["QUERY_STRING"] = "&".join(p for p in environ.get("QUERY_STRING", "").split("&") if not p.startswith("__path="))
        return self.application(environ, start_response)


app.wsgi_app = _OriginalPathMiddleware(app.wsgi_app)
