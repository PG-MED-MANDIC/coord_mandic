"""Fonte "Atendimentos" -- reaproveita a base ConsultaJá do repositório
vizinho agendas-pac-real e sua função `_prepare()`, rodando num subprocesso
com cwd em agendas-pac-real/pipeline (ver _subprocess_reuso.py pro motivo).

Diferente de transform_triagem.py:build_raw() (agrupa por u/m/d/c/t, sem a
semana "w"), o DATA_ATD do coord_mandic também precisa de "w" -- por isso um
groupby próprio aqui em vez de reaproveitar build_raw() direto (mudança
aditiva no repo vizinho evitada de propósito, pra não arriscar quebrar o uso
que agendas-pac-real já faz dele).

Nunca sai daqui nome/celular/profissional/convênio de paciente -- só as
contagens agregadas que `_prepare()`/`build_slots()` já produzem hoje.
"""
from __future__ import annotations

from config import AGENDAS_PAC_REAL_PIPELINE_DIR

from _subprocess_reuso import rodar_em

_CODIGO = r"""
import json, sys
from datetime import date
from pathlib import Path

import pandas as pd

from config import DADOS_FONTE_DIR
from consultaja_client import ConsultaJaConfigurationError
from fetch_consultaja import fetch_and_save
from transform_slots import build_slots
from transform_triagem import _prepare

entrada = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
checklist_path = Path(entrada["checklist_path"]) if entrada.get("checklist_path") else None

def planilha_de_hoje():
    p = DADOS_FONTE_DIR / f"Base_Consulta_Ja{date.today():%y_%m_%d}.xlsx"
    return p if p.exists() else None

saida = {"warnings": [], "erro": None}
try:
    xlsx = planilha_de_hoje()
    if xlsx is None:
        xlsx = fetch_and_save()
    if xlsx is None:
        saida["erro"] = "Nenhum agendamento encontrado na ConsultaJá hoje -- nada pra processar."
    else:
        df = pd.read_excel(xlsx)
        prep = _prepare(df)
        grouped = (
            prep.groupby(["u", "m", "d", "c", "t", "w"])[["r", "f", "x", "a"]]
            .sum().reset_index().sort_values(["u", "m", "d", "c", "t"])
        )
        saida["arquivo"] = xlsx.name
        saida["DATA_ATD"] = grouped.to_dict(orient="records")
        if checklist_path is not None and checklist_path.exists():
            warnings = []
            saida["DATA_ATD_SLOTS"] = build_slots(checklist_path, df, warnings=warnings)
            saida["warnings"] = warnings
except ConsultaJaConfigurationError as e:
    saida["erro"] = str(e)
except Exception:
    import traceback
    saida["erro"] = "erro inesperado:\n" + traceback.format_exc()

Path(sys.argv[2]).write_text(json.dumps(saida, ensure_ascii=False), encoding="utf-8")
"""


def montar_dados(checklist_path=None) -> dict:
    entrada = {"checklist_path": str(checklist_path)} if checklist_path else {}
    resultado = rodar_em(AGENDAS_PAC_REAL_PIPELINE_DIR, _CODIGO, entrada)
    if resultado.get("erro"):
        raise RuntimeError(f"Fonte Atendimentos: {resultado['erro']}")
    return resultado


__all__ = ["montar_dados"]
