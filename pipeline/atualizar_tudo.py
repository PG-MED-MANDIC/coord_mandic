"""Orquestra a atualização automática das 4 fontes prontas do dashboard da
coordenação (CSAT por item, Comentários com nome, Ocupação de Agendas,
Atendimentos). Ocupação por Turmas (DATA_OTU) fica de fora -- pendente de
modelagem da tabela SMATRICULA no datalake (decisão de 27/09/2026), o bloco
que a usa em "One Page por Turma" já tem aviso próprio de dado congelado.

Comando único:

    python pipeline/atualizar_tudo.py

Fluxo (mesma filosofia de csat/pipeline/atualizar_tudo.py, adaptada pro
formato deste repositório -- uma página HTML inteira cifrada, não um
data.js separado):
  1. Decifra pagina.enc (senha COORD_SENHA) -- na primeira execução, se
     pagina.enc ainda não refletir os dados mais recentes, usa
     fonte/index_aberto.html como semente (arquivo local, fora do git).
  2. Roda as 4 fontes, regrava as 7 constantes automatizadas no HTML.
  3. Reaplica a limpeza idempotente de publicar.py (remove tela de senha
     antiga, zera DATA_INAD/DATA_PDD, confere que não sobrou e-mail/senha
     antiga) -- nenhuma dessas operações muda nada depois da 1ª vez.
  4. Cifra de volta em pagina.enc e regrava index.html.

Log só com contagens agregadas -- nunca nome de aluno/comentário completo
no console (mesmo padrão de todo pipeline deste workspace que lida com
dado sensível).
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

from config import DADOS_FONTE_DIR, FONTE_PATH, INDEX_HTML_PATH, PAGINA_ENC_PATH, PIPELINE_DIR
from protecao import cifrar_texto, decifrar_texto, obter_senha
from publicar import INDEX_HTML, conferir, esvaziar_const, remover_tela_senha_antiga
from render_index import read_di_turma_map, upsert_all

# coord_mandic_teste/pipeline/publicar.py tem essa função extra (faixa
# vermelha "AMBIENTE DE TESTE"); coord_mandic_pgmed/pipeline/publicar.py
# (produção) não -- import condicional pra este mesmo atualizar_tudo.py
# servir os dois repositórios sem fork de código.
try:
    from publicar import inserir_faixa_teste
except ImportError:
    inserir_faixa_teste = None

import sources_atendimentos
import sources_csat
import sources_ocupacao

LOG_PATH = PIPELINE_DIR / "atualizacoes.log"


def _log(lines: list[str]) -> None:
    from datetime import datetime

    text = "\n".join(lines) + "\n"
    print(text)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} =====\n")
        f.write(text)


def _carregar_html_de_trabalho(senha: str, report: list[str]) -> str:
    if PAGINA_ENC_PATH.exists():
        return decifrar_texto(PAGINA_ENC_PATH.read_text(encoding="ascii"), senha)
    if FONTE_PATH.exists():
        report.append(
            f"  Aviso: {PAGINA_ENC_PATH.name} não existe ainda -- usando "
            f"{FONTE_PATH.relative_to(PIPELINE_DIR.parent)} (arquivo local) como semente da 1ª rodada."
        )
        return FONTE_PATH.read_bytes().decode("utf-8")
    raise RuntimeError(f"Nem {PAGINA_ENC_PATH.name} nem {FONTE_PATH.name} encontrados.")


def main() -> int:
    report: list[str] = []

    try:
        senha = obter_senha()
        html = _carregar_html_de_trabalho(senha, report)
        di_turma_map = read_di_turma_map(html)
    except Exception as e:
        report.append(f"FALHOU ao carregar o HTML de trabalho (senha errada/ausente?): {type(e).__name__} {e}")
        _log(report)
        return 1

    dados: dict[str, list[dict]] = {}
    todos_avisos: list[str] = []

    report.append("FONTE 1/3 -- CSAT por item + Comentários com nome (Indecx)")
    try:
        resultado = sources_csat.montar_dados(di_turma_map)
        todos_avisos.extend(resultado.get("warnings") or [])
        dados["DATA_GERAL"] = resultado["DATA_GERAL"]
        dados["DATA_ITENS"] = resultado["DATA_ITENS"]
        dados["DATA_TURMAS"] = resultado["DATA_TURMAS"]
        dados["DATA_FEEDBACK_FULL"] = resultado["DATA_FEEDBACK_FULL"]
        report.append(
            f"  OK -- planilha {resultado.get('arquivo')}: {len(dados['DATA_GERAL'])} respostas, "
            f"{len(dados['DATA_FEEDBACK_FULL'])} comentários."
        )
    except Exception as e:
        report.append(f"  FALHOU: {e}")

    report.append("\nFONTE 2/3 -- Ocupação de Agendas (checklist-captacao.xlsx)")
    checklist_path = DADOS_FONTE_DIR / "checklist-captacao.xlsx"
    if not checklist_path.exists():
        report.append(f"  Aviso: {checklist_path.name} não encontrado -- Ocupação de Agendas mantém o que já estava.")
    else:
        try:
            resultado = sources_ocupacao.montar_dados(checklist_path)
            todos_avisos.extend(resultado.get("warnings") or [])
            dados["DATA_OCUPACAO"] = resultado["DATA_OCUPACAO"]
            report.append(f"  OK -- {len(dados['DATA_OCUPACAO'])} linhas de prática.")
        except Exception as e:
            report.append(f"  FALHOU: {e}")

    report.append("\nFONTE 3/3 -- Atendimentos (ConsultaJá)")
    try:
        resultado = sources_atendimentos.montar_dados(checklist_path if checklist_path.exists() else None)
        todos_avisos.extend(resultado.get("warnings") or [])
        dados["DATA_ATD"] = resultado["DATA_ATD"]
        msg = f"  OK -- planilha {resultado.get('arquivo')}: {len(dados['DATA_ATD'])} combinações mês/dia/curso/turma/semana."
        if "DATA_ATD_SLOTS" in resultado:
            dados["DATA_ATD_SLOTS"] = resultado["DATA_ATD_SLOTS"]
            msg += f" {len(dados['DATA_ATD_SLOTS'])} combinações com slots previstos."
        else:
            msg += " DATA_ATD_SLOTS mantém o que já estava (sem checklist-captacao.xlsx)."
        report.append(msg)
    except Exception as e:
        report.append(f"  FALHOU: {e}")

    if todos_avisos:
        report.append("\nAvisos (revisar manualmente):")
        for w in todos_avisos:
            report.append(f"  - {w}")

    if not dados:
        report.append("\nNenhuma fonte produziu dado novo -- nada a publicar.")
        _log(report)
        return 1

    try:
        html = upsert_all(html, dados)
        html = remover_tela_senha_antiga(html)
        html = esvaziar_const(html, "DATA_INAD")
        html = esvaziar_const(html, "DATA_PDD")
        if inserir_faixa_teste is not None:
            html = inserir_faixa_teste(html)

        problemas = conferir(html)
        if problemas:
            report.append("\nNÃO publicado -- revise o HTML:")
            for p in problemas:
                report.append(f"  - {p}")
            _log(report)
            return 1

        PAGINA_ENC_PATH.write_text(cifrar_texto(html, senha), encoding="ascii")
        INDEX_HTML_PATH.write_text(INDEX_HTML, encoding="utf-8", newline="\n")
    except Exception:
        report.append("\nFALHOU: erro ao gravar/cifrar o resultado. Detalhes:")
        report.append(traceback.format_exc())
        _log(report)
        return 1

    report.append(
        f"\nOK -- {PAGINA_ENC_PATH.name} ({PAGINA_ENC_PATH.stat().st_size / 1e6:.1f} MB) e "
        f"{INDEX_HTML_PATH.name} atualizados.\n"
        "Próximos passos (revise antes de publicar):\n"
        "  git status\n"
        "  git add index.html pagina.enc\n"
        '  git commit -m "Atualiza dados do dashboard (Coordenação)"\n'
        "  git push"
    )
    _log(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
