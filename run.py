"""
Novel2Script — Entry point script.
Runs both FastAPI backend and Gradio frontend.
Usage: python run.py [--frontend-only] [--backend-only] [--port PORT]
"""

import sys
import os
import argparse
import threading
import time
import subprocess

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FRONTEND_PORT = 7860
BACKEND_PORT = 8000


def run_backend():
    """Start FastAPI backend server."""
    import uvicorn
    from backend.api.app import app

    print(f"\n[Backend] Starting FastAPI on http://localhost:{BACKEND_PORT}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=BACKEND_PORT,
        log_level="info",
        reload=False,
    )


def run_frontend():
    """Start Gradio frontend."""
    print(f"\n[Frontend] Starting Gradio on http://localhost:{FRONTEND_PORT}")
    from frontend.app import build_ui
    import asyncio

    demo = build_ui()
    # Fix: ensure queue locks exist (gradio 4.44.1 anyio compat)
    if demo._queue is not None:
        if demo._queue.pending_message_lock is None:
            demo._queue.pending_message_lock = asyncio.Lock()
        if demo._queue.delete_lock is None:
            demo._queue.delete_lock = asyncio.Lock()
    demo.launch(
        server_name="0.0.0.0",
        server_port=FRONTEND_PORT,
        share=False,
        show_error=True,
        inbrowser=True,
    )


def main():
    parser = argparse.ArgumentParser(description="Novel2Script — AI 小说转剧本工具")
    parser.add_argument("--frontend-only", action="store_true", help="仅启动前端（需手动启动后端）")
    parser.add_argument("--backend-only", action="store_true", help="仅启动后端 API 服务")
    parser.add_argument("--port", type=int, default=None, help="指定前端端口")
    args = parser.parse_args()

    global FRONTEND_PORT
    if args.port:
        FRONTEND_PORT = args.port

    # Set environment variable for frontend to find backend
    os.environ["NOVEL2SCRIPT_API"] = f"http://localhost:{BACKEND_PORT}"

    print("=" * 50)
    print("  Novel2Script · AI 小说转剧本工具")
    print("=" * 50)
    print(f"  后端 API:  http://localhost:{BACKEND_PORT}")
    print(f"  前端界面:  http://localhost:{FRONTEND_PORT}")
    print("=" * 50)

    if args.frontend_only:
        run_frontend()
        return

    if args.backend_only:
        run_backend()
        return

    # Run both
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    time.sleep(2)  # Give backend time to start

    frontend_thread = threading.Thread(target=run_frontend, daemon=False)
    frontend_thread.start()

    print("\n  Press Ctrl+C to stop all services\n")
    try:
        frontend_thread.join()
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()
