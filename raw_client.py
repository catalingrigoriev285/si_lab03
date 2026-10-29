"""Laborator 3 SI - client MCP „de mână": trimite mesaje JSON-RPC prin HTTP, fără SDK.

Serverul trebuie să ruleze în alt terminal:  python server.py http

Utilizare:
    python raw_client.py discover
    python raw_client.py list
    python raw_client.py call get_device_info name=radiator
    python raw_client.py call estimate_energy name=radiator hours=2
    python raw_client.py call set_device_state name=radiator on=true

Experimente (cereri greșite intenționat):
    python raw_client.py fara-antet      lipsește antetul Mcp-Name
    python raw_client.py antet-gresit    Mcp-Name nu corespunde corpului
    python raw_client.py versiune        versiune de protocol necunoscută
    python raw_client.py metoda          metodă inexistentă
    python raw_client.py instrument      instrument inexistent
    python raw_client.py origin          cerere dintr-o pagină web străină
"""
import json
import sys

import httpx

URL = "http://127.0.0.1:8000/mcp"
VERSIUNE = "2026-07-28"
_id = 0


def send(method: str, params: dict | None = None, *, versiune: str = VERSIUNE,
         antete: dict | None = None, fara: tuple[str, ...] = ()) -> None:
    """Construiește o cerere JSON-RPC, o trimite și afișează cererea și răspunsul."""
    global _id
    _id += 1
    params = dict(params or {})
    # Fără handshake: fiecare cerere își spune singură versiunea și capabilitățile clientului.
    params["_meta"] = {
        "io.modelcontextprotocol/protocolVersion": versiune,
        "io.modelcontextprotocol/clientInfo": {"name": "raw-client", "version": "1.0"},
        "io.modelcontextprotocol/clientCapabilities": {},
    }
    corp = {"jsonrpc": "2.0", "id": _id, "method": method, "params": params}

    h = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": versiune,
        "Mcp-Method": method,
    }
    if "name" in params:            # tools/call, prompts/get
        h["Mcp-Name"] = params["name"]
    elif "uri" in params:           # resources/read
        h["Mcp-Name"] = params["uri"]
    h.update(antete or {})
    for cheie in fara:
        h.pop(cheie, None)

    print(">>> CERERE  POST", URL)
    for k, v in h.items():
        print(f"    {k}: {v}")
    print(json.dumps(corp, indent=2, ensure_ascii=False))

    r = httpx.post(URL, headers=h, json=corp)
    print(f"\n<<< RĂSPUNS  HTTP {r.status_code}  ({r.headers.get('content-type', '-')})")
    try:
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except ValueError:
        print(r.text)


def _argumente(perechi: list[str]) -> dict:
    """Transformă ['name=radiator', 'hours=2'] în {'name': 'radiator', 'hours': 2}."""
    rezultat = {}
    for p in perechi:
        cheie, _, valoare = p.partition("=")
        try:
            rezultat[cheie] = json.loads(valoare)   # 2 -> 2, true -> True
        except ValueError:
            rezultat[cheie] = valoare               # radiator -> "radiator"
    return rezultat


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd, rest = sys.argv[1], sys.argv[2:]
    radiator = {"name": "get_device_info", "arguments": {"name": "radiator"}}

    if cmd == "discover":
        send("server/discover")
    elif cmd == "list":
        send("tools/list")
    elif cmd == "call" and rest:
        send("tools/call", {"name": rest[0], "arguments": _argumente(rest[1:])})
    elif cmd == "fara-antet":
        send("tools/call", radiator, fara=("Mcp-Name",))
    elif cmd == "antet-gresit":
        send("tools/call", radiator, antete={"Mcp-Name": "reset_building"})
    elif cmd == "versiune":
        send("tools/list", versiune="2030-01-01")
    elif cmd == "metoda":
        send("tools/run")
    elif cmd == "instrument":
        send("tools/call", {"name": "porneste_tot", "arguments": {}})
    elif cmd == "origin":
        send("tools/list", antete={"Origin": "http://site-strain.example"})
    else:
        print(__doc__)


if __name__ == "__main__":
    try:
        main()
    except httpx.ConnectError:
        print(f"Nu mă pot conecta la {URL}. Ați pornit serverul cu: python server.py http ?")
