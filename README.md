# Atualizador de Sistemas - GUI (NBS & Linx DMS)

Aplicação Desktop desenvolvida em Python com **CustomTkinter** projetada para centralizar e automatizar o processo de atualização de dois dos principais ERPs: **NBS** e **Linx DMS**. A aplicação gerencia downloads assíncronos, descompactação inteligente, controle de serviços do Windows (iniciar/parar), execução elevada de instaladores e utilitários de limpeza de arquivos obsoletos.

O sistema possui comportamento **Cross-Platform**: funciona plenamente no Windows e simula de forma segura no Linux as operações do sistema operacional Windows (como a elevação de privilégios e consultas/comandos de serviços via `sc`) para permitir testes completos sem causar falhas no ambiente de desenvolvimento.

---

## 🛠️ Requisitos de Sistema

- **Python 3.10 ou superior** instalado.
- Acesso à internet/rede para conexões FTP e downloads HTTP/HTTPS.
- Privilégios de Administrador no Windows (caso precise iniciar/parar serviços ou executar scripts SQL/instaladores).

---

## 📂 Estrutura do Projeto

*   `main.py`: Código-fonte principal que inicializa o CustomTkinter, gerencia a tela de seleção de sistemas (NBS vs Linx DMS), navegação entre sidebars/frames e o loop principal da aplicação.
*   `ui_nbs.py`: Módulo que implementa a interface visual e lógica de negócios do **Sistema NBS** (downloads FTP por marca/interface, execução de scripts SQL/DB, distribuição remota em rede, CRM Web, aba utilitários e configurações NBS).
*   `ui_apollo.py`: Módulo que implementa a interface visual e lógica de negócios do **Sistema Linx DMS / Apollo** (downloads HTTP de pacotes evolutivos, controle de serviços do Windows, atualizações automatizadas e configurações Apollo).
*   `ui_common.py`: Módulo com componentes e popups visuais compartilhados por ambos os sistemas (ferramenta de limpeza interativa de diretórios por extensão e reinicialização remota de servidores via PowerShell).
*   `changelog.py`: Módulo que armazena as constantes de texto com o histórico de alterações (changelogs) das versões do NBS e Apollo.
*   `ftp_client.py`: Manipulador das conexões FTP para o NBS. Implementa listagem de arquivos e subpastas e downloads com progresso.
*   `utils.py`: Funções utilitárias como detecção de datas históricas, backups locais de arquivos `.exe`, execução de processos de forma elevada (UAC), cópias de arquivos recursivas e comandos remotos PowerShell.
*   `config.py`: Gerencia a leitura, escrita, criptografia XOR+Base64 e preenchimento de valores padrão do arquivo de configuração (`config.enc`).
*   `requirements.txt`: Dependências do projeto (`customtkinter` e `pyinstaller`).
*   `build.bat`: Script de lote para compilação automatizada do executável `AtualizadorSistemas.exe` no Windows via PyInstaller.
*   `.gitignore`: Arquivo de exclusão do Git configurado para ignorar caches, ambientes virtuais (`venv/`), pastas locais de atualização e arquivos temporários.

---

## 💻 Recursos e Funcionalidades

### 1. Central de Seleção de Sistemas (Tela Inicial)
*   Interface em formato de painel moderno com cards de largura ajustada (350px) para direcionar o usuário para a gerência de atualizações do **Sistema NBS** ou **Sistema Linx DMS**.

### 2. Sistema NBS (FTP & Distribuição)
*   **Downloads de Módulos (FTP)**: Consulta inteligente de datas de arquivos no servidor FTP usando o comando `MDTM` para baixar apenas os módulos modificados a partir da data de corte.
*   **Monitoramento em Tempo Real de Download**: Exibe a porcentagem exata (`.1f%`) de progresso e a velocidade instantânea em **MB/s**, **KB/s** ou **B/s** durante as transferências FTP.
*   **Instalação Inicial**: Opção para ignorar a data de corte e forçar o download completo de todos os módulos oficiais e DLLs de apoio.
*   **Execução de Scripts SQL**: Identifica e executa scripts de banco de dados (`.sql` ou `.exe` compilados) com elevação de privilégios (UAC).
*   **Distribuição de Rede**: Distribui de forma concorrente os arquivos atualizados para múltiplos servidores da rede local cadastrados na lista.
*   **Backup Automático**: Compacta a pasta de backup antiga no formato `.zip` com opção de excluir o diretório descompactado de origem para economizar espaço em disco.
*   **Aba Utilitários NBS**: Ferramentas de limpeza de executáveis (`.exe`), limpeza por extensão customizada (`.log`, `.tmp`, `.zip`) e reinício remoto com explicações exibidas através de **Tooltips** flutuantes ao passar o mouse sobre os botões.

### 3. Sistema Linx DMS (HTTP & Serviços)
*   **Downloads Modulares**: Baixa pacotes evolutivos Delphi (Padrão), 3 Camadas Server, 3 Camadas Client, Instalador Web, DMS Comissões, Apoio (Troca Fornecedor, Troca Série, Verifica Diária) e o **Linx DMS Integrador**.
*   **Monitoramento em Tempo Real de Download**: Exibe a porcentagem exata (`.1f%`) de progresso e a velocidade instantânea em **MB/s**, **KB/s** ou **B/s** durante os downloads de pacotes HTTP/HTTPS.
*   **Descompactação e Atualização Automatizada**:
    *   **Arquivos Normais (Delphi)**: Extraídos e copiados diretamente para `C:\Apollo\Atualiza`.
    *   **Servidor 3 Camadas**: Extraídos e copiados diretamente para `C:\3Camadas`.
    *   **Cliente 3 Camadas**: Extraídos e copiados diretamente para `C:\3Camadas\Atualiza`.
    *   **Instalador Web / Integrador**: Após o download do `LinxDMS.zip` ou `LinxDMSIntegrador.zip`, a ferramenta varre a pasta extraída, encontra o instalador nativo (`.exe` ou `.msi`) e o executa com **privilégios elevados como Administrador**.
*   **Backup Automático Apollo (Compactação & Limpeza Automática)**:
    *   Copia executáveis e DLLs de `C:\Apollo\atualiza` antes da aplicação dos novos pacotes.
    *   Compacta automaticamente a pasta em arquivo `.zip` e deleta o diretório descompactado temporário com os arquivos copiados.
    *   Ao finalizar com sucesso a atualização, identifica e exclui automaticamente o arquivo `.zip` de backup anterior registrado no arquivo de configurações (`config.enc`).
*   **Painel de Monitoramento de Serviços**:
    *   Exibe o status em tempo real de até 4 serviços cruciais no Windows: `DFeServico`, `RedirecionaDatasnap`, `VerificaServer3Camadas` e `dmLDIServer` (Serviço Integrador).
    *   Fornece botões para **Iniciar** ou **Parar** cada serviço de forma totalmente assíncrona, evitando travamentos na tela.
*   **Aba Utilitários Linx (Interface com Tooltips)**:
    *   Exibição das explicações detalhadas de cada ferramenta através de **Tooltips** flutuantes ao passar o mouse sobre os botões.
    *   Limpeza por executáveis/DLLs e por extensão customizada (.log, .tmp, .zip) com suporte a Glob e Regex.
    *   Reinício remoto via PowerShell com monitoramento por PING e atalho para o Agendador de Tarefas do Windows (`taskschd.msc`).
*   **Menu de Observações (NBS & Linx DMS)**: Campo de texto livre sem limite de caracteres e com suporte a quebras de linha para anotações, lembretes e históricos locais, persistido automaticamente no arquivo de configuração criptografado (`config.enc`).

### 4. Configurações Dinâmicas e Tema Sincronizado
*   **Templates de URL**: Permite configurar e salvar todas as URLs HTTP utilizadas no download do Linx através de curingas dinâmicos de `{version}` e `{package}`.
*   **Nomes de Serviços customizados**: Permite alterar o nome de sistema dos serviços de cada cliente diretamente no painel.
*   **Tema Visual Unificado**: Seletor de modo de aparência ("Dark", "Light", "System") integrado e sincronizado em tempo real entre as configurações do NBS e as do Linx.

---

## ⚙️ Configurações (Criptografia e Armazenamento)

O atualizador utiliza um sistema seguro e centralizado para gerenciar parâmetros locais de configuração:
* **Criptografia Simétrica (XOR + Base64)**: O arquivo de configurações é criptografado e salvo sob o formato `.enc` (com extensão `config.enc`), ocultando dados de banco de dados e credenciais de FTP contra visualização/edição acidental em editores comuns (como Bloco de Notas).
* **Diretório Padrão por S.O.**:
  * **Windows**: `%APPDATA%\AtualizadorSistemas\config.enc` (normalmente mapeado em `AppData\Roaming\AtualizadorSistemas\config.enc`).
  * **Linux/macOS**: `~/.config/AtualizadorSistemas/config.enc`.
* **Migração Automática**: Caso exista um arquivo legado `config.json` em texto plano na mesma pasta do executável, a aplicação lerá os parâmetros dele, salvará no formato criptografado no novo diretório do S.O., e excluirá o arquivo legado `.json` para proteção dos dados do usuário.

---

## 🚀 Como Executar em Desenvolvimento

### No Linux/macOS
1. Crie e ative o ambiente virtual:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Execute o atualizador:
   ```bash
   python main.py
   ```

### No Windows
1. Abra o CMD ou PowerShell na pasta do projeto e configure o ambiente virtual:
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```
2. Instale as dependências:
   ```cmd
   pip install -r requirements.txt
   ```
3. Execute a aplicação:
   ```cmd
   python main.py
   ```

---

## 📦 Como Buildar no Windows (Geração do `.exe` Único)

Para gerar o executável independente **`AtualizadorSistemas.exe`** para distribuição aos clientes:

1. Transfira a pasta do projeto para um computador com sistema operacional **Windows**.
2. Dê dois cliques no arquivo **`build.bat`**.
3. O script instalará as dependências listadas e executará o empacotamento com o PyInstaller:
   ```cmd
   pyinstaller --noconsole --onefile --collect-all customtkinter --name="AtualizadorSistemas" main.py
   ```
4. Após a conclusão, o executável consolidado estará localizado em **`dist\AtualizadorSistemas.exe`**.
