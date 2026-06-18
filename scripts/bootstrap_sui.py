#!/usr/bin/env python3
"""Bootstrap the Sui CLI config + keystore inside the Railway container.

Invoked by ``railway-start.py`` at container start when ``SERVICE_TYPE=sui-web``,
so that ``sui client call`` (see ``core/sui_client.py``) has a testnet env and a
signing address available. There is no real ``sui client bootstrap`` subcommand,
so "bootstrap" here means:

  1. Ensure ``~/.sui/sui_config`` exists with a keystore and a testnet client.yaml.
  2. Import ``SUI_PRIVATE_KEY`` (a ``suiprivkey1...`` bech32 key) into the keystore.
  3. Point ``active_env`` at testnet and ``active_address`` at the imported key.

Idempotent: safe to run on every boot. Re-importing the same key is a no-op that
simply returns the same address, and the client.yaml is rewritten deterministically.

Configuration (env):
    SUI_PRIVATE_KEY  required - bech32 signing key (suiprivkey1...)
    SUI_RPC_URL      testnet full node RPC (default: testnet public endpoint)
    SUI_BIN          path to the sui binary (default: "sui" on PATH)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SUI_BIN = os.environ.get("SUI_BIN", "sui")
RPC_URL = os.environ.get("SUI_RPC_URL", "https://fullnode.testnet.sui.io:443")
PRIVATE_KEY = os.environ.get("SUI_PRIVATE_KEY", "").strip()

CONFIG_DIR = Path.home() / ".sui" / "sui_config"
CLIENT_YAML = CONFIG_DIR / "client.yaml"
KEYSTORE = CONFIG_DIR / "sui.keystore"


def _run(args: list[str]) -> subprocess.CompletedProcess:
    print("[bootstrap_sui] $ sui " + " ".join(args), flush=True)
    proc = subprocess.run([SUI_BIN, *args], text=True, capture_output=True)
    if proc.stdout.strip():
        print(proc.stdout.strip(), flush=True)
    if proc.returncode != 0 and proc.stderr.strip():
        print(proc.stderr.strip(), file=sys.stderr, flush=True)
    return proc


def main() -> int:
    if not PRIVATE_KEY:
        print("[bootstrap_sui] SUI_PRIVATE_KEY is not set; nothing to bootstrap.",
              file=sys.stderr, flush=True)
        return 1

    # 1. Ensure the config dir + an (at least empty) keystore exist.
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not KEYSTORE.exists():
        KEYSTORE.write_text("[]\n")

    # 2. Import the signing key (idempotent: re-importing the same key returns
    #    the same address and does not error).
    imported = _run([
        "keytool", "--keystore-path", str(KEYSTORE),
        "import", PRIVATE_KEY, "ed25519", "--json",
    ])
    if imported.returncode != 0:
        print("[bootstrap_sui] key import failed", file=sys.stderr, flush=True)
        return 1
    try:
        address = json.loads(imported.stdout)["suiAddress"]
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"[bootstrap_sui] could not parse imported address: {exc}",
              file=sys.stderr, flush=True)
        return 1
    print(f"[bootstrap_sui] signing address: {address}", flush=True)

    # 1+3. Write a testnet client.yaml pointing at the imported address. Written
    #      deterministically each boot so the active env/address are always correct.
    CLIENT_YAML.write_text(
        "---\n"
        "keystore:\n"
        f"  File: {KEYSTORE}\n"
        "envs:\n"
        "  - alias: testnet\n"
        f"    rpc: \"{RPC_URL}\"\n"
        "    ws: ~\n"
        "    basic_auth: ~\n"
        "active_env: testnet\n"
        f"active_address: \"{address}\"\n"
    )

    # 3. Confirm active env + address via the CLI (local, idempotent). Not fatal
    #    if these report non-zero, since client.yaml already encodes both.
    _run(["client", "switch", "--env", "testnet"])
    _run(["client", "switch", "--address", address])

    print("[bootstrap_sui] bootstrap complete.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
