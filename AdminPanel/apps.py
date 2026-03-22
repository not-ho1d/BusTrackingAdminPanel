import signal
import sys
import os
import requests
def process_queues():
    print("SERVER STWOPPIN.....")

    try:
        res = requests.post(
            "http://127.0.0.1:8000/Api/",
            json={
                "action": "db_reload",
            },
            timeout=5
        )

    except Exception as e:
        print("Request failed:", e)

def server_shutdown(sig, frame):
    from AdminPanel.views import update_queue, delete_queue
    process_queues()
    sys.exit(0)

if os.environ.get("RUN_MAIN") == "true":
    signal.signal(signal.SIGINT, server_shutdown)