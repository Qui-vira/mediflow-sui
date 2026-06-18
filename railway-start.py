"""Railway multi-service start wrapper (web + Band workers)."""
import os
import subprocess
import sys

SERVICE = os.environ.get("SERVICE_TYPE", "web")
PORT = os.environ.get("PORT", "5000")

COMMANDS = {
    "coordinator": [sys.executable, "agents/coordinator.py"],
    "intake": [sys.executable, "agents/intake.py"],
    "verification": [sys.executable, "agents/verification.py"],
    "resource": [sys.executable, "agents/resource.py"],
    "web": [
        "gunicorn",
        "-w",
        "4",
        "-b",
        f"0.0.0.0:{PORT}",
        "--timeout",
        "120",
        "--keep-alive",
        "5",
        "--max-requests",
        "1000",
        "frontend.app:app",
    ],
}

# sui-web: the same Flask app as "web", but with the Sui execution path
# (SUI_MODE=true) enabled. Set SERVICE_TYPE=sui-web on the Railway service.
COMMANDS["sui-web"] = COMMANDS["web"]
if SERVICE == "sui-web":
    os.environ["SUI_MODE"] = "true"
    # Bootstrap the Sui CLI keystore/config before serving (idempotent). Fail
    # fast if it errors, rather than serving with a broken Sui path.
    subprocess.run([sys.executable, "scripts/bootstrap_sui.py"], check=True)

cmd = COMMANDS.get(SERVICE, COMMANDS["web"])
os.execvp(cmd[0], cmd)
