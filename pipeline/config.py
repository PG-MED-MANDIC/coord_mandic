"""Caminhos do pipeline de automação do coord_mandic.

DADOS_FONTE_DIR aponta pra fora deste repositório, pra dados-fonte/ na raiz
do workspace (pasta NPS-PACIENTE, que contém este repositório como
subpasta) -- é a MESMA pasta compartilhada usada pelos pipelines vizinhos
(csat, agendas_pgmed, agendas-pac-real), tanto local quanto no GitHub
Actions (onde os 6 repositórios são clonados como subpastas de
automacao-dashboard). Só funciona com essa disposição de pastas -- se este
repositório for movido pra fora de NPS-PACIENTE, ajuste este caminho.
"""
from __future__ import annotations

from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PIPELINE_DIR.parent
FONTE_PATH = PROJECT_DIR / "fonte" / "index_aberto.html"
PAGINA_ENC_PATH = PROJECT_DIR / "pagina.enc"
INDEX_HTML_PATH = PROJECT_DIR / "index.html"
DADOS_FONTE_DIR = PROJECT_DIR.parent / "dados-fonte"

# Repositórios vizinhos (mesmo workspace, clonados como siblings tanto local
# quanto no Actions) cujos módulos de pipeline este script reaproveita direto
# via sys.path, em vez de duplicar código -- ver sources_csat.py/
# sources_ocupacao.py/sources_atendimentos.py.
CSAT_PIPELINE_DIR = PROJECT_DIR.parent / "csat" / "pipeline"
AGENDAS_PGMED_PIPELINE_DIR = PROJECT_DIR.parent / "agendas_pgmed" / "pipeline"
AGENDAS_PAC_REAL_PIPELINE_DIR = PROJECT_DIR.parent / "agendas-pac-real" / "pipeline"
