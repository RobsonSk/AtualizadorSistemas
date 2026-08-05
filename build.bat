@echo off
echo =============================================================
echo Compilando o Atualizador de Sistemas para Windows (.exe)
echo =============================================================
echo 1. Instalando dependencias listadas em requirements.txt...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar dependencias. Verifique se o Python/pip esta no PATH.
    pause
    exit /b %errorlevel%
)

echo.
echo 2. Fechando instancias antigas do executavel em execucao (se houver)...
taskkill /f /im AtualizadorSistemas.exe >nul 2>&1

echo.
echo 3. Salvando backup do executavel anterior...
if exist "dist\AtualizadorSistemas.exe" (
    copy /y "dist\AtualizadorSistemas.exe" "dist\Old_AtualizadorSistemas.exe" >nul 2>&1
    echo [INFO] Backup da versao anterior salvo em: dist\Old_AtualizadorSistemas.exe
)

echo.
echo 4. Compilando com PyInstaller...
echo [INFO] Coletando todos os pacotes e recursos do customtkinter...
pyinstaller --noconsole --onefile --collect-all customtkinter --name="AtualizadorSistemas" main.py

if %errorlevel% neq 0 (
    echo [ERRO] Ocorreu uma falha durante a compilacao do executavel.
    pause
    exit /b %errorlevel%
)

echo.
echo =============================================================
echo Compilacao concluida com sucesso!
echo O arquivo independente esta em: dist\AtualizadorSistemas.exe
echo =============================================================
pause
