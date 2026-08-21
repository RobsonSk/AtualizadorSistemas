# Atualizador de Sistemas - GUI (NBS & Linx DMS) - v2.0.0

Aplicação Desktop profissional desenvolvida em Python com **PySide6 (Qt 6)** projetada para centralizar e automatizar o processo de atualização de dois dos principais ERPs: **NBS** e **Linx DMS**. A aplicação gerencia downloads assíncronos, descompactação inteligente, controle de serviços do Windows (iniciar/parar), execução elevada de instaladores, gerenciamento de licenças via REST API/Gatekeeper com trava HWID (SHA-256) e utilitários de limpeza de arquivos obsoletos.

O sistema possui arquitetura **Thread-Safe** baseada em Qt Signals/Slots e comportamento **Cross-Platform**: funciona plenamente no Windows e emula de forma segura no Linux as operações do sistema operacional Windows (como a elevação de privilégios UAC e comandos de serviços via `sc`) para testes em ambiente de desenvolvimento.

---

## 🛠️ Requisitos de Sistema

- **Python 3.10 ou superior** instalado.
- Dependências Python: `PySide6`, `pyinstaller`, `pillow`, `cryptography` (listadas em `requirements.txt`).
- Acesso à internet/rede para conexões FTP, downloads HTTP/HTTPS e validação de licença REST.
- Privilégios de Administrador no Windows (para gerenciamento de serviços, instaladores e scripts de banco).

---

## 📂 Estrutura do Projeto

*   `main.py`: Código-fonte principal que inicializa a aplicação PySide6, gerencia a tela de seleção de sistemas (NBS vs Linx DMS), navegação lateral e roteamento de views.
*   `ui_nbs.py`: Módulo que implementa a interface visual e lógica do **Sistema NBS** (downloads FTP por marca/interface, execução de scripts SQL/DB, distribuição remota em rede, CRM Web, aba utilitários, observações e configurações NBS).
*   `ui_apollo.py`: Módulo que implementa a interface visual e lógica do **Sistema Linx DMS / Apollo** (downloads HTTP de pacotes evolutivos, controle assíncrono de serviços do Windows, atualizações automatizadas, observações e configurações Apollo).
*   `ui_common.py`: Módulo com componentes e popups visuais compartilhados (limpeza interativa de diretórios por extensão e reinicialização remota de servidores via PowerShell).
*   `license_gatekeeper.py`: Módulo de controle de licenças via REST API online com validação de HWID (SHA-256), armazenamento criptografado no AppData e revalidação periódica em segundo plano.
*   `changelog.py`: Armazena as constantes de texto com o histórico completo de alterações (changelogs) das versões do NBS e Apollo.
*   `ftp_client.py`: Client FTP para o NBS com suporte a checagem de modificação (`MDTM`), listagem recursiva e callbacks de progresso.
*   `utils.py`: Funções utilitárias (detecção de datas de corte, backups zip, execução UAC elevada, cópia de rede e comandos PowerShell).
*   `config.py`: Gerencia a leitura, escrita e criptografia simétrica (XOR+Base64) do arquivo de configurações local (`config.enc`).
*   `requirements.txt`: Dependências do projeto.
*   `build.bat`: Script de lote automatizado para compilação do executável `AtualizadorSistemas.exe` via PyInstaller.
*   `.gitignore`: Arquivo de exclusão do Git configurado para ignorar caches, executáveis, ambientes virtuais (`venv/`) e temporários.

---

## 💻 Recursos e Funcionalidades da Versão 2.0.0

### 1. Central de Seleção de Sistemas (Tela Inicial)
*   Interface moderna em PySide6 com cards direcionando o usuário para a gerência de atualizações do **Sistema NBS** ou **Sistema Linx DMS**.

### 2. Sistema NBS (FTP & Distribuição)
*   **Downloads de Módulos (FTP)**: Consulta inteligente de datas de arquivos no servidor FTP usando o comando `MDTM` para baixar apenas módulos modificados após a data de corte.
*   **Monitoramento em Tempo Real**: Exibe progresso (%), velocidade (MB/s, KB/s) e status via Qt Signals sem travamento de UI.
*   **Instalação Inicial**: Força o download completo de todos os módulos oficiais e DLLs de apoio.
*   **Execução de Scripts SQL**: Identifica e executa scripts de banco de dados (`.sql` ou `.exe`) com elevação de privilégios (UAC).
*   **Distribuição de Rede**: Distribui de forma concorrente os arquivos atualizados para múltiplos servidores da rede local.
*   **Backup Automático (.zip)**: Compactação com progresso em tempo real, ETA e limpeza automática da pasta descompactada de origem.
*   **Aba Utilitários NBS**: Limpeza por extensão customizada (`.log`, `.tmp`, `.zip`), reinício remoto via PowerShell com monitoramento PING (ONLINE/OFFLINE) e tooltips informativos.
*   **Menu de Observações NBS**: Campo de anotações persistido no arquivo criptografado do sistema.

### 3. Sistema Linx DMS (HTTP & Serviços)
*   **Downloads Modulares**: Pacotes evolutivos Delphi (Padrão), 3 Camadas Server, 3 Camadas Client, Instalador Web, DMS Comissões, Apoio e Linx DMS Integrador.
*   **Descompactação e Atualização Automatizada**: Roteamento dinâmico para `C:\Apollo\Atualiza`, `C:\3Camadas` e `C:\3Camadas\Atualiza`, além de execução elevada de instaladores `.exe`/`.msi`.
*   **Backup Automático Apollo**: Backup compactado com exclusão automatizada de arquivos `.zip` antigos após atualização bem-sucedida.
*   **Painel de Monitoramento de Serviços**: Monitora e gerencia serviços do Windows (`DFeServico`, `RedirecionaDatasnap`, `VerificaServer3Camadas`, `dmLDIServer`) em tempo real.
*   **Menu de Observações Linx**: Campo de anotações persistido localmente.

### 4. Licenciamento & Gatekeeper
*   **Validação REST API Configurável**: O aplicativo valida a licença via requisição HTTP POST para o servidor REST (`https://api.licenciamento.com.br/api/validate`).
*   **Modo Bypass / Sem Validação (Desenvolvimento / Uso Livre)**: Para desativar completamente a verificação de licença (ex: para testes locais ou publicar código no Git sem restrições), abra o arquivo `license_gatekeeper.py` e altere a constante para `BYPASS_LICENSE = True`.
*   **Trava por Hardware ID (HWID SHA-256)**: Combina o UUID da placa-mãe (`Win32_ComputerSystemProduct`) com o ID do processador (`Win32_Processor`) em um hash SHA-256 único para vincular a licença à máquina física.
*   **Pop-up Modal de Ativação**: Quando o bypass está desativado (`BYPASS_LICENSE = False`) e a licença não é encontrada ou é inválida, o arranque do aplicativo é bloqueado (`Gatekeeper`) e uma janela modal solicita o UUID e a chave `X-API-Key`.
*   **Revalidação Periódica em Segundo Plano**: Thread em segundo plano re-valida a licença a cada 15 minutos (quando ativa).
*   **Armazenamento Criptografado (`Fernet / AES-128`)**: As credenciais de licença são salvas criptografadas em `license.enc`.
---

## ⚙️ Configurações (Criptografia e Armazenamento)

* **Criptografia Simétrica (XOR + Base64)**: Configurações salvas em `%APPDATA%\AtualizadorSistemas\config.enc` (Windows) ou `~/.config/AtualizadorSistemas/config.enc` (Linux).
* **Migração Automática**: Migra automaticamente arquivos legados `config.json` para a nova estrutura criptografada.

---

## 🚀 Como Executar em Desenvolvimento

### No Windows
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### No Linux/macOS
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

---

## 📦 Como Buildar no Windows (Geração do `.exe` Único)

Para gerar o executável independente **`AtualizadorSistemas.exe`**:

1. Abra o prompt de comando na raiz do projeto no Windows.
2. Execute o arquivo **`build.bat`**.
3. O script instalará as dependências e executará o PyInstaller:
   ```cmd
   pyinstaller --clean --noconsole --onefile --collect-binaries PySide6 --collect-data PySide6 --exclude-module PySide6.Qt3DAnimation --exclude-module PySide6.Qt3DCore --exclude-module PySide6.Qt3DRender --exclude-module PySide6.Qt3DExtras --exclude-module PySide6.Qt3DInput --exclude-module PySide6.Qt3DLogic --exclude-module PySide6.QtQuick --exclude-module PySide6.QtQml --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtMultimedia --exclude-module PySide6.QtBluetooth --exclude-module PySide6.QtSensors --name="AtualizadorSistemas" main.py
   ```
4. O executável consolidado estará em **`dist\AtualizadorSistemas.exe`**.
