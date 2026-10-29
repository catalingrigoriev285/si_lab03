"""Tema facultativă 5: agentul cu rezumarea istoricului, în loc de fereastra glisantă.

Când conversația ar depăși `max_turns` ture, turele vechi nu sunt doar tăiate: modelul
le rezumă, iar rezumatul se păstrează în mesajul system. Rulare: python agent_rezumat.py
"""
import asyncio
import json
import time

from agent import MAX_TURNS, SYSTEM_PROMPT, Agent
from llm import create_chat

PROMPT_REZUMAT = (
    "Ții evidența unei conversații dintre un utilizator și asistentul unei clădiri inteligente. "
    "Primești REZUMATUL DE PÂNĂ ACUM (poate lipsi) și TURELE NOI. Scrie un singur rezumat actualizat, "
    "în limba română, ca listă scurtă de fapte (câte o liniuță pe fapt). Păstrează TOATE faptele din "
    "rezumatul de până acum și adaugă-le pe cele noi: dispozitivele discutate, valorile numerice "
    "(ore, kWh, grade), acțiunile executate sau refuzate. La final, o linie „Subiect curent: …”. "
    "Nu adăuga nimic ce nu apare în text."
)

def ca_text(messages: list[dict]) -> str:
    """Transcrie turele (inclusiv apelurile și rezultatele) ca text simplu, pentru rezumare."""
    linii = []
    for m in messages:
        if m["role"] == "user":
            linii.append(f"Utilizator: {m['content']}")
        elif m["role"] == "assistant" and m.get("tool_calls"):
            for c in m["tool_calls"]:
                linii.append(f"Asistentul apelează {c['function']['name']}({c['function']['arguments']})")
        elif m["role"] == "tool":
            linii.append(f"Rezultat: {m['content']}")
        elif m["role"] == "assistant":
            linii.append(f"Asistent: {m['content']}")
    return "\n".join(linii)

class AgentCuRezumat(Agent):
    def __init__(self, confirm=None, max_turns: int = MAX_TURNS):
        self.max_turns = max_turns
        self.rezumat = ""
        super().__init__(confirm)

    def reset(self):
        self.rezumat = ""
        super().reset()

    def _rezuma(self, vechi: list[dict]) -> str:
        text = (f"REZUMATUL DE PÂNĂ ACUM:\n{self.rezumat or '(niciunul)'}\n\n"
                f"TURELE NOI:\n{ca_text(vechi)}")
        t0 = time.perf_counter()
        reply = create_chat(self.llm, model=self.model, messages=[
            {"role": "system", "content": PROMPT_REZUMAT},
            {"role": "user", "content": text},
        ])
        rezumat = (reply.choices[0].message.content or "").strip()
        usage = getattr(reply, "usage", None)
        self.log.write("rezumat", ture=sum(m["role"] == "user" for m in vechi), text=rezumat,
                       durata_ms=round((time.perf_counter() - t0) * 1000),
                       prompt_tokens=getattr(usage, "prompt_tokens", None))
        return rezumat

    async def ask(self, text: str) -> str:
        starts = [i for i, m in enumerate(self.messages) if m["role"] == "user"]
        # Înainte de întrebarea nouă rămân cel mult max_turns - 1 ture întregi; restul se rezumă.
        if len(starts) >= self.max_turns:
            taie = starts[len(starts) - self.max_turns + 1] if self.max_turns > 1 else len(self.messages)
            self.rezumat = self._rezuma(self.messages[1:taie])
            sistem = f"{SYSTEM_PROMPT}\n\nRezumatul conversației anterioare: {self.rezumat}"
            self.messages = [{"role": "system", "content": sistem}] + self.messages[taie:]
        return await super().ask(text)

async def main():
    from chat import cere_acord
    async with AgentCuRezumat(confirm=cere_acord, max_turns=2) as agent:
        print(f"Furnizor: {agent.provider} | rezumare după {agent.max_turns} ture | log: {agent.log.path}")
        while True:
            try:
                text = input("Tu: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if text == "/iesire":
                break
            if not text:
                continue
            print("Agent:", await agent.ask(text))
            if agent.rezumat:
                print(f"  (rezumat: {json.dumps(agent.rezumat, ensure_ascii=False)[:200]})")

if __name__ == "__main__":
    asyncio.run(main())
