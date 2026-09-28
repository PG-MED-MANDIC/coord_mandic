"""Executa um trecho de código Python num subprocesso com `cwd` apontando
pra dentro do repositório vizinho cujo pipeline queremos reaproveitar.

Por quê: csat/agendas_pgmed/agendas-pac-real todos têm um módulo próprio
chamado `config.py` (e `fetch_*.py`/`transform_*.py` fazem `from config
import ...` de forma implícita, esperando o `config.py` DAQUELE
repositório). Importar dois desses pipelines no MESMO processo Python (via
sys.path.insert) faz o segundo import de "config" reaproveitar o módulo já
cacheado em sys.modules do primeiro -- um bug de cross-contaminação
silencioso. Rodar cada fonte em subprocesso isolado, com `cwd` no diretório
certo, evita o problema por completo: `python -c` adiciona o diretório
atual ao início de sys.path, então cada subprocesso enxerga só o
`config.py` do repositório vizinho em questão, exatamente como o
`atualizar_tudo.py` daquele repositório já roda sozinho todo dia.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def rodar_em(pipeline_dir: Path, codigo: str, entrada: dict | None = None, timeout: int = 900) -> dict:
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        entrada_path = tmp / "entrada.json"
        saida_path = tmp / "saida.json"
        entrada_path.write_text(json.dumps(entrada or {}, ensure_ascii=False), encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, "-c", codigo, str(entrada_path), str(saida_path)],
            cwd=pipeline_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"Subprocesso falhou (cwd={pipeline_dir}):\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
            )
        if not saida_path.exists():
            raise RuntimeError(
                f"Subprocesso terminou sem gravar saida.json (cwd={pipeline_dir}):\n{proc.stdout}\n{proc.stderr}"
            )
        return json.loads(saida_path.read_text(encoding="utf-8"))


__all__ = ["rodar_em"]
