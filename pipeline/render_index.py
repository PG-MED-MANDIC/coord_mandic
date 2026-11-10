"""Regrava as 7 constantes DATA_* automatizadas dentro do HTML de trabalho
(decifrado de pagina.enc) -- mesma técnica de csat/pipeline/render_index.py:
_upsert_const().

Nunca toca em DATA_FEEDBACK (shape antigo sem nome, confirmado morto -- só
usado pela função manual de upload de planilha e pelo cache de
localStorage, nunca lido por nenhuma função de render), DATA_ITENS_AGG
(morto, mesma razão), DATA_OTU/DATA_NPS/DATA_INAD/DATA_PDD (fora de escopo
desta automação).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

NAMES = (
    "DATA_GERAL",
    "DATA_ITENS",
    "DATA_TURMAS",
    "DATA_FEEDBACK_FULL",
    "DATA_OCUPACAO",
    "DATA_ATD",
    "DATA_ATD_SLOTS",
)


def _upsert_const(lines: list[str], name: str, value) -> list[str]:
    # Regex gulosa casa até o ÚLTIMO ';' da linha -- lida sozinha com as
    # constantes que hoje terminam em ';;' (família CSAT), sempre regravando
    # com ';' simples (achado desta sessão, não precisa de tratamento
    # especial pro `;` duplo).
    pattern = re.compile(rf"^const {re.escape(name)} = .*;")
    new_value = json.dumps(value, ensure_ascii=False)

    for i, line in enumerate(lines):
        if pattern.match(line):
            ending = line[len(line.rstrip("\r\n")):]
            lines[i] = f"const {name} = {new_value};{ending}"
            return lines

    raise RuntimeError(
        f"Não encontrei a linha 'const {name} = ...;' no HTML de trabalho -- abortando para não "
        "corromper o arquivo. Verifique manualmente antes de rodar de novo."
    )


def read_di_turma_map(html: str) -> dict:
    m = re.search(r"^const DI_TURMA_MAP = (\{.*\});", html, re.MULTILINE)
    if not m:
        raise RuntimeError("Não encontrei 'const DI_TURMA_MAP = ...;' no HTML de trabalho.")
    return json.loads(m.group(1))


def read_const(html: str, name: str) -> list:
    """Lê (sem alterar) uma constante de dado (`const NAME = [...];`) do HTML de trabalho.
    Usada pela mescla incremental do Typeform. Constante ausente = lista vazia."""
    m = re.search(rf"^const {re.escape(name)} = (.*);\s*$", html, re.MULTILINE)
    return json.loads(m.group(1)) if m else []


def upsert_all(html: str, data: dict[str, list[dict]]) -> str:
    # Chaves ausentes em `data` são puladas (não apagadas) -- permite rodar
    # com uma fonte faltando (ex.: checklist-captacao.xlsx do dia ainda não
    # chegou) sem perder o que já estava publicado nas outras constantes.
    lines = html.splitlines(keepends=True)
    for name in NAMES:
        if name not in data:
            continue
        lines = _upsert_const(lines, name, data[name])
    return "".join(lines)





def carregar_mapa_turmas(*pastas: Path) -> dict:
    """Lê `mapa_turmas.json` (DI -> rótulo "Especialidade Unidade - Tn (DI x)"), gerado LOCALMENTE por
    automacao-dashboard/atualizar_mapa_turmas.py a partir do Book do TOTVS + rótulos do Painel-alunos
    (sem dado pessoal). Procura na primeira pasta que o tiver. Se não existir ou estiver inválido,
    devolve {} e o DI_TURMA_MAP segue como está (não quebra a atualização)."""
    for pasta in pastas:
        f = Path(pasta) / "mapa_turmas.json"
        if f.exists():
            try:
                return json.loads(f.read_text(encoding="utf-8")).get("mapa") or {}
            except (ValueError, OSError):
                return {}
    return {}


def upsert_di_turma_map(html: str, mapa: dict) -> str:
    """Regrava a constante DI_TURMA_MAP no HTML de trabalho (o navegador usa ela em diTurmaLabel)."""
    return "".join(_upsert_const(html.splitlines(keepends=True), "DI_TURMA_MAP", mapa))


__all__ = ["NAMES", "upsert_all", "read_const", "read_di_turma_map", "carregar_mapa_turmas", "upsert_di_turma_map"]
