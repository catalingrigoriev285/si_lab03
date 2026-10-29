"""Laborator 3 SI - doi clienți FastMCP conectați prin HTTP la ACELAȘI server.

Serverul trebuie să ruleze în alt terminal:  python server.py http
Rulare:  python client_demo.py
"""
import asyncio

from fastmcp import Client

URL = "http://127.0.0.1:8000/mcp"


async def main() -> None:
    async with Client(URL) as ana, Client(URL) as bogdan:
        # Ana pornește radiatorul.
        r = await ana.call_tool("set_device_state", {"name": "radiator", "on": True})
        print("Ana    -> set_device_state:", r.structured_content)

        # Bogdan, alt client, citește starea clădirii.
        r = await bogdan.call_tool("get_building_state", {})
        print("Bogdan -> get_building_state:", r.structured_content)

        # Bogdan încearcă să pornească aerul condiționat: eroare de execuție (isError).
        r = await bogdan.call_tool("set_device_state", {"name": "aer_conditionat", "on": True},
                                   raise_on_error=False)
        print("Bogdan -> set_device_state: isError =", r.is_error, "|", getattr(r.content[0], "text", ""))

        # Curățenie, ca demonstrația să poată fi rulată din nou.
        await ana.call_tool("reset_building", {})


if __name__ == "__main__":
    asyncio.run(main())
