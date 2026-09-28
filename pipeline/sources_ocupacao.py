"""Fonte "Ocupação de Agendas" -- reaproveita direto
agendas_pgmed/pipeline/transform_ocupacao.py:build_raw() (mesma
checklist-captacao.xlsx do SharePoint, já compartilhada em dados-fonte/),
rodando num subprocesso com cwd em agendas_pgmed/pipeline (ver
_subprocess_reuso.py pro motivo).

O parse de "Dermatologia CPS T05" -> especialidade/unidade/número é feito
aqui (não em agendas_pgmed/attendance_consultaja.py:parse_turma(), que
normaliza o nome do curso pra virar chave de cruzamento -- aqui o valor é
pra exibição, precisa manter a grafia original).

`mes`/`mes_label` são o mês-calendário real da data de prática (a
checklist só cobre mai-nov de um único ano) -- diferente do `mes_order` da
pesquisa CSAT (que tem uma sequência especial pra distinguir set/25 de
set/26 dentro do ano letivo), domínio diferente, não reaproveitado aqui.
"""
from __future__ import annotations

from config import AGENDAS_PGMED_PIPELINE_DIR

from _subprocess_reuso import rodar_em

_CODIGO = r"""
import json, re, sys
from datetime import datetime
from pathlib import Path

from transform_ocupacao import build_raw

_TURMA_RE = re.compile(r"^(.+)\s(BSB|CPS|SP|ONL)\sT0*(\d+)$")
UNI_NOME = {"SP": "CONSOLAÇÃO", "CPS": "CAMPINAS", "BSB": "BRASÍLIA", "ONL": "ONLINE"}
MES_ABREV = {1:"jan",2:"fev",3:"mar",4:"abr",5:"mai",6:"jun",7:"jul",8:"ago",9:"set",10:"out",11:"nov",12:"dez"}

entrada = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
checklist_path = Path(entrada["checklist_path"])

saida = {"warnings": [], "erro": None}
try:
    warnings = []
    linhas = build_raw(checklist_path, warnings=warnings)
    out = []
    for turma, unidade, modulo, data_str, sp, se, st, ag in linhas:
        m = _TURMA_RE.match(turma.strip())
        if not m:
            warnings.append(f'Ocupação: turma "{turma}" fora do padrão esperado -- linha ignorada.')
            continue
        esp, uni_cod, tnum = m.group(1), m.group(2), int(m.group(3))
        data_dt = datetime.strptime(data_str, "%d/%m/%Y")
        out.append({
            "turma": turma, "esp": esp, "uni": UNI_NOME.get(uni_cod, unidade),
            "uni_cod": uni_cod, "tnum": f"T{tnum:02d}", "modulo": modulo, "data": data_str,
            "mes": data_dt.month, "mes_label": f"{MES_ABREV[data_dt.month]}/{data_dt.year % 100:02d}",
            "sp": sp, "ob": se, "st": st, "ag": ag,
        })
    saida["warnings"] = warnings
    saida["DATA_OCUPACAO"] = out
except Exception:
    import traceback
    saida["erro"] = "erro inesperado:\n" + traceback.format_exc()

Path(sys.argv[2]).write_text(json.dumps(saida, ensure_ascii=False), encoding="utf-8")
"""


def montar_dados(checklist_path) -> dict:
    resultado = rodar_em(AGENDAS_PGMED_PIPELINE_DIR, _CODIGO, {"checklist_path": str(checklist_path)})
    if resultado.get("erro"):
        raise RuntimeError(f"Fonte Ocupação de Agendas: {resultado['erro']}")
    return resultado


__all__ = ["montar_dados"]
