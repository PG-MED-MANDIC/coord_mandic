"""Fonte "CSAT por item + Comentários com nome" -- reaproveita direto o
pipeline do repositório vizinho `csat` (mesma pesquisa, mesma conta),
rodando num subprocesso com cwd em csat/pipeline (ver _subprocess_reuso.py
pro motivo: evita colisão do módulo `config` entre repositórios).

Duas origens, somadas:
  - Indecx (exportação completa do dia) -- opcional se houver Typeform;
  - Typeform (typeform_respostas.json, baixado do endpoint n8n pelo Actions;
    ver csat/pipeline/fonte_typeform.py) -- cada resposta é nova, então o
    resultado é MESCLADO com o que já está na página (o histórico nunca é
    apagado), igual ao csat.
Se o Indecx cair ou for desligado e houver Typeform, segue só com o Typeform.

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
from fonte_typeform import carregar_linhas, rows_do_typeform
from mesclar import mesclar_por_id, rotular_pendentes
from transform_csat import (
    build_data_feedback, build_data_geral, build_data_itens, build_data_turmas, melt_raw_export,
)

entrada = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
di_turma_map = entrada["di_turma_map"]
anteriores = entrada.get("anteriores") or {}

def planilha_de_hoje():
    p = DADOS_FONTE_DIR / f"export_indecx_csat_{date.today():%y_%m_%d}.xlsx"
    return p if p.exists() else None

saida = {"warnings": [], "erro": None, "mesclar": False}
try:
    linhas_tf = carregar_linhas(DADOS_FONTE_DIR, DADOS_FONTE_DIR.parent / "automacao-dashboard" / "dados-fonte")
    warnings = []
    xlsx = planilha_de_hoje()
    if xlsx is None:
        try:
            xlsx = fetch_and_save()
        except Exception as e:
            if not linhas_tf:
                raise
            warnings.append(f"Indecx indisponível ({type(e).__name__}) -- seguindo só com o Typeform.")
    if xlsx is None and not linhas_tf:
        saida["erro"] = "Exportação do Indecx vazia -- nenhuma planilha nova pra processar hoje."
    else:
        rows = []
        if xlsx is not None:
            rows += melt_raw_export(pd.read_excel(xlsx), warnings=warnings)
        if linhas_tf:
            rows_tf, resumo_tf = rows_do_typeform(linhas_tf, warnings=warnings)
            rows += rows_tf
            saida["resumo_typeform"] = resumo_tf
        data_geral = build_data_geral(rows, di_turma_map)
        data_itens = build_data_itens(rows)
        data_fb = build_data_feedback(rows, di_turma_map)
        if linhas_tf:
            # Mescla incremental: mantém o histórico já gravado na página, substitui o que veio de
            # novo (por db-id) e atualiza rótulos de turma antigos que ficaram no nome de reserva.
            ant_geral = anteriores.get("DATA_GERAL") or []
            ant_itens = anteriores.get("DATA_ITENS") or []
            ant_fb = anteriores.get("DATA_FEEDBACK_FULL") or []
            saida["rotulos_atualizados"] = rotular_pendentes(ant_geral, di_turma_map) + rotular_pendentes(ant_fb, di_turma_map)
            saida["historico_mantido"] = len(ant_geral)
            data_geral = mesclar_por_id(ant_geral, data_geral, "db-id")
            data_itens = mesclar_por_id(ant_itens, data_itens, "db-id")
            data_fb = mesclar_por_id(ant_fb, data_fb, "db_id")
            saida["mesclar"] = True
        saida.update({
            "arquivo": xlsx.name if xlsx is not None else "(só Typeform)",
            "warnings": warnings,
            "DATA_GERAL": data_geral,
            "DATA_ITENS": data_itens,
            "DATA_TURMAS": build_data_turmas(data_geral),
            "DATA_FEEDBACK_FULL": data_fb,
        })
except Exception as e:
    import traceback
    saida["erro"] = f"{type(e).__name__}: {e}" if type(e).__name__ == "IndecxConfigurationError" else "erro inesperado:\n" + traceback.format_exc()

Path(sys.argv[2]).write_text(json.dumps(saida, ensure_ascii=False), encoding="utf-8")
"""


def montar_dados(di_turma_map: dict, anteriores: dict | None = None) -> dict:
    resultado = rodar_em(
        CSAT_PIPELINE_DIR, _CODIGO, {"di_turma_map": di_turma_map, "anteriores": anteriores or {}}
    )
    if resultado.get("erro"):
        raise RuntimeError(f"Fonte CSAT por item: {resultado['erro']}")
    return resultado


__all__ = ["montar_dados"]
