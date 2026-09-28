"""Fonte "CSAT por item + Comentários com nome" -- reaproveita direto o
pipeline do repositório vizinho `csat` (mesma pesquisa Indecx, mesma conta),
rodando num subprocesso com cwd em csat/pipeline (ver _subprocess_reuso.py
pro motivo: evita colisão do módulo `config` entre repositórios).

`nome` já vem incluído em build_data_feedback() desde 2026-09-25 (decisão
explícita do usuário no csat, ver memória [[csat_nome_aluno_comentarios]]) --
aqui o campo fica atrás de senha + criptografia (pagina.enc), nunca em texto
puro no repositório.
"""
from __future__ import annotations

from config import CSAT_PIPELINE_DIR

from _subprocess_reuso import rodar_em

_CODIGO = r"""
import json, sys
from datetime import date
from pathlib import Path

import pandas as pd

from config import DADOS_FONTE_DIR
from fetch_indecx import fetch_and_save
from indecx_client import IndecxConfigurationError
from transform_csat import (
    build_data_feedback, build_data_geral, build_data_itens, build_data_turmas, melt_raw_export,
)

entrada = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
di_turma_map = entrada["di_turma_map"]

def planilha_de_hoje():
    p = DADOS_FONTE_DIR / f"export_indecx_csat_{date.today():%y_%m_%d}.xlsx"
    return p if p.exists() else None

saida = {"warnings": [], "erro": None}
try:
    xlsx = planilha_de_hoje()
    if xlsx is None:
        xlsx = fetch_and_save()
    if xlsx is None:
        saida["erro"] = "Exportação do Indecx vazia -- nenhuma planilha nova pra processar hoje."
    else:
        df = pd.read_excel(xlsx)
        warnings = []
        rows = melt_raw_export(df, warnings=warnings)
        data_geral = build_data_geral(rows, di_turma_map)
        saida.update({
            "arquivo": xlsx.name,
            "warnings": warnings,
            "DATA_GERAL": data_geral,
            "DATA_ITENS": build_data_itens(rows),
            "DATA_TURMAS": build_data_turmas(data_geral),
            "DATA_FEEDBACK_FULL": build_data_feedback(rows, di_turma_map),
        })
except IndecxConfigurationError as e:
    saida["erro"] = str(e)
except Exception:
    import traceback
    saida["erro"] = "erro inesperado:\n" + traceback.format_exc()

Path(sys.argv[2]).write_text(json.dumps(saida, ensure_ascii=False), encoding="utf-8")
"""


def montar_dados(di_turma_map: dict) -> dict:
    resultado = rodar_em(CSAT_PIPELINE_DIR, _CODIGO, {"di_turma_map": di_turma_map})
    if resultado.get("erro"):
        raise RuntimeError(f"Fonte CSAT por item: {resultado['erro']}")
    return resultado


__all__ = ["montar_dados"]
