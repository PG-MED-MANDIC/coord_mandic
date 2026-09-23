@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python nao encontrado no PATH. Instale o Python antes de rodar este atalho.
    pause
    exit /b 1
)

echo ============================================================
echo  Atualizar dashboard da Coordenacao
echo  Antes de continuar, o HTML novo precisa estar salvo em:
echo    fonte\index_aberto.html
echo ============================================================
echo.

git pull --ff-only
if errorlevel 1 (
    echo Nao consegui baixar a versao mais recente do GitHub -- veja a mensagem acima.
    pause
    exit /b 1
)

python pipeline\publicar.py
if errorlevel 1 (
    echo.
    echo Nada foi publicado -- veja a mensagem acima.
    pause
    exit /b 1
)

echo.
git status --short
echo.
set /p RESPOSTA=Publicar no GitHub agora? (S/N): 
if /i not "%RESPOSTA%"=="S" (
    echo Nao publicado. Os arquivos gerados continuam na pasta.
    pause
    exit /b 0
)

for /f %%d in ('powershell -NoProfile -Command "Get-Date -Format dd.MM.yy"') do set HOJE=%%d
git add index.html pagina.enc
git commit -m "Atualiza dados do dashboard (%HOJE%)"
if errorlevel 1 (
    echo Nada novo pra publicar ^(o HTML era igual ao anterior?^).
    pause
    exit /b 0
)
git push
if errorlevel 1 (
    echo O envio pro GitHub falhou -- veja a mensagem acima. O commit ficou salvo no PC.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Publicado! O site atualiza em 1 a 2 minutos:
echo  https://pg-med-mandic.github.io/coord_mandic/
echo ============================================================
pause
