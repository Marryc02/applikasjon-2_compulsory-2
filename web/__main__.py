"""python -m web [--host HOST] [--port PORT]

Starts the public page with Flask's development server. It binds to
127.0.0.1 by default; use a proper WSGI server for real hosting.
"""
from __future__ import annotations

import argparse

from .app import create_app


def main() -> None:
    p = argparse.ArgumentParser(prog="web", description="Public page for approved youth events")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=5000)
    args = p.parse_args()
    create_app().run(host=args.host, port=args.port, load_dotenv=False)


if __name__ == "__main__":
    main()
