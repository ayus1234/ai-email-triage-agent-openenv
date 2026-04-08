import subprocess
import time
import requests

print("Starting server...")
server = subprocess.Popen(['uv', 'run', 'server', '--port', '7860'])
time.sleep(15)

print("\n--- Checking health endpoint ---")
try:
    print(requests.get("http://localhost:7860/health").json())
except Exception as e:
    print("Health check failed:", e)

print("\n--- Checking reset endpoint (simulating Judges) ---")
try:
    r = requests.post("http://localhost:7860/reset", json={})
    print("Status:", r.status_code)
    print(str(r.json())[:200] + "...")
except Exception as e:
    print("Reset check failed:", e)

print("\n--- Running inference.py ---")
res = subprocess.run(["python", "inference.py"], capture_output=True, text=True)
print("OUT:\n", res.stdout)
if res.stderr:
    print("ERR:\n", res.stderr)

server.terminate()
print("Done.")
