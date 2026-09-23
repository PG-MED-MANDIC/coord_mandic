# CSAT Pós Med — Coordenação

Dashboard da coordenação médica: CSAT, NPS, rankings, One Page por turma, ocupação de agendas e de
turmas. Publicado no GitHub Pages. **Protegido por senha com criptografia de verdade**: o repositório
só tem a página cifrada (`pagina.enc`), e o navegador decifra com a senha digitada.

Migrado da conta antiga (`TCM-18/coord_mandic`) em 23/09/2026, **sem o histórico de lá**. Antes, o
`index.html` era substituído direto no GitHub, sem commit, e a senha ficava escrita no JavaScript
(só escondia a tela: os dados, com nome de aluno, já estavam no código-fonte).

## Como atualizar

1. Salve o HTML novo (aberto) em `fonte/index_aberto.html`. Essa pasta **nunca** vai pro git.
2. `python pipeline/publicar.py` e digite a senha do dashboard.
3. `git add index.html pagina.enc`, depois commit com mensagem descritiva e push.

Dependência: `pip install -r pipeline/requirements.txt`.

`publicar.py` remove a tela de senha antiga, esvazia a Inadimplência (`DATA_INAD`/`DATA_PDD`: não tem
botão no menu e carregava nome de aluno e valores) e **para sem publicar** se sobrar senha antiga,
lista de inadimplentes ou endereço de e-mail.

## Senha

- Fica **só** no secret `COORD_SENHA` do GitHub e com quem acessa. Nunca em arquivo, nem no código.
- Pra trocar: rode `publicar.py` com a senha nova, faça o push e atualize o secret.
- Esqueceu? Os dados não se recuperam a partir do `pagina.enc`. Gere de novo a partir do HTML aberto.

## Arquivos

| Arquivo | O que é |
|---|---|
| `index.html` | Só a tela de senha (gerado por `publicar.py`) |
| `pagina.enc` | A página inteira, cifrada (AES-256-GCM, chave PBKDF2-SHA256) |
| `protecao.js` | Tela de senha e decifragem no navegador (mesmo arquivo do repo `csat`) |
| `pipeline/protecao.py` | Criptografia do lado Python (mesmo módulo do `csat`, variável `COORD_SENHA`) |
| `pipeline/publicar.py` | Limpa, confere e cifra o HTML aberto |
