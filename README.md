# Atualizador NBS - GUI

Aplicação Desktop desenvolvida em Python com **CustomTkinter** projetada para automatizar o download de módulos oficiais, instaladores (NFE), marcas (interfaces de marcas) e scripts do FTP, executar scripts de banco de dados como administrador (elevação UAC no Windows) e distribuir os arquivos atualizados localmente e para servidores da rede.

O sistema possui comportamento **Cross-Platform**: funciona plenamente no Windows e simula de forma segura no Linux as operações do sistema operacional Windows (como a elevação de privilégios e cópias UNC `\\IP\c$\NBS`) para permitir testes completos sem causar falhas de sistema no Linux.

---

## 🛠️ Requisitos de Sistema

- **Python 3.10 ou superior** instalado.
- Acesso à internet/rede para conexões FTP e cópias de rede.

---

## 📂 Estrutura do Projeto

*   `main.py`: Código-fonte principal que renderiza a interface gráfica moderna em CustomTkinter, gerencia as threads em background e manipula os componentes visuais.
*   `ftp_client.py`: Manipulador das conexões FTP. Implementa listagem de arquivos e subpastas (com fallback de detecção automática de diretórios) e downloads reportando progresso.
*   `utils.py`: Funções utilitárias como detecção de datas históricas, backups locais de arquivos `.exe`, execução de processos de forma elevada (UAC) e cópias de arquivos recursivas.
*   `config.py`: Gerencia a leitura, escrita e preenchimento de valores padrão no arquivo `config.json`.
*   `requirements.txt`: Dependências do projeto (`customtkinter` e `pyinstaller`).
*   `build.bat`: Script automatizado para compilação em lote do executável no Windows.

---

## ⚙️ Configurações (`config.json`)

Ao iniciar o aplicativo pela primeira vez, o arquivo `config.json` será criado automaticamente na mesma pasta do executável/script. Você pode pré-configurá-lo antes de distribuir a ferramenta:

```json
{
    "ftp_modules_url": "ftp://nbsi.com.br/sistemadelphi/modulos/oficiais",
    "ftp_scripts_url": "ftp://nbsi.com.br/sistemadelphi/scripts",
    "ftp_nfe_url": "ftp://nbsi.com.br/sistemadelphi/modulos/nfe",
    "ftp_interfaces_url": "ftp://nbsi.com.br/sistemadelphi/modulos/interfaces",
    "ftp_dll_url": "ftp://nbsi.com.br/sistemadelphi/modulos/dll",
    "ftp_user": "nbs",
    "ftp_password": "nbs",
    "atualizacao_path_win": "C:\\Atualizacao",
    "nbs_path_win": "C:\\NBS",
    "atualizacao_path_linux": "./Atualizacao",
    "nbs_path_linux": "./NBS_Local",
    "servers": [],
    "db_user": "nbs_db_user",
    "db_password": "nbs_db_password",
    "db_schema": "nbs_schema",
    "copy_local": true,
    "copy_servers": true,
    "download_nfe": false,
    "download_interfaces": false,
    "initial_installation": false,
    "selected_interfaces": [],
    "transition_year_enabled": false,
    "transition_year_value": "2025"
}
```

> 💡 **Dica**: Preencha as chaves `db_user`, `db_password` e `db_schema` com os dados padrão do banco do seu cliente no `config.json` antes de enviar o `.exe` a ele. O botão "Exibir Credenciais" na Aba 2 lerá essas chaves para facilitar a visualização da senha na hora da atualização.

---

## 🚀 Como Executar em Modo de Desenvolvimento/Testes

### No Linux

1. Instale as dependências no ambiente virtual (`venv`) da pasta do projeto:
   ```bash
   ./venv/bin/pip install -r requirements.txt
   ```
2. Execute o script principal:
   ```bash
   ./venv/bin/python main.py
   ```

### No Windows (Modo de Script)

1. Abra o Terminal/Prompt de Comando na pasta do projeto e crie o ambiente virtual:
   ```cmd
   python -m venv venv
   ```
2. Ative o ambiente virtual:
   ```cmd
   venv\Scripts\activate
   ```
3. Instale as dependências:
   ```cmd
   pip install -r requirements.txt
   ```
4. Execute o script principal:
   ```cmd
   python main.py
   ```

---

## 🧪 Processo de Validação de Fluxos (No Linux)

Como o atualizador foi projetado com suporte multiplataforma para testes locais, você pode criar uma estrutura simulada na pasta do projeto para verificar o comportamento:

1.  **Criação de Pastas de Simulação**:
    Crie subpastas e arquivos fictícios para o NBS rodando os seguintes comandos no terminal Linux dentro da pasta do projeto:
    ```bash
    mkdir -p Atualizacao/01072026
    mkdir -p Atualizacao/05072026
    mkdir -p NBS_Local
    touch NBS_Local/modulo1.exe
    touch NBS_Local/modulo2.exe
    ```
2.  **Validação dos Passos**:
    - **Aba 1 (Download)**: A "Data de Corte" autodetectada deve ser `01/07/2026` (a penúltima pasta anterior a `05072026`). Ao clicar em "Iniciar Processo", verifique se o backup de `modulo1.exe` e `modulo2.exe` é gerado dentro de `Atualizacao/<dataHoje>/backup/` e se os arquivos reais do FTP são baixados para `Atualizacao/<dataHoje>/Modulos/`.
    - **Aba 1 (Instalação Inicial)**: Marque "Instalação Inicial". O campo da data de corte ficará desabilitado (esmaecido). Ao iniciar o download, ele baixará todos os módulos oficiais sem limite de data e buscará todas as DLLs de `/modulos/dll`.
    - **Aba 2 (Scripts)**: O executável do script de banco baixado será auto-selecionado no campo superior. O botão de execução irá simular em tela a espera de conclusão do script (aguarda 2s).
    - **Aba 3 (Distribuição)**: Cadastre IPs de servidores (ex: `192.168.1.150`). Ao clicar em "Distribuir Atualização", a cópia para a sua máquina local (`NBS_Local`) será real e a distribuição de rede para os IPs será simulada exibindo relatórios de sucesso/falha individualmente.

---

## 📦 Como Buildar no Windows (.exe independente)

Para gerar um arquivo executável autônomo que **não exige a instalação do Python** na máquina do cliente final, siga estes passos em um computador rodando **Windows**:

1.  Garanta que o **Python** esteja instalado e a opção "Add Python to PATH" tenha sido marcada no instalador.
2.  Transfira a pasta do projeto completa para a máquina Windows.
3.  Dê dois cliques no arquivo **`build.bat`**.
4.  O console do Windows se abrirá e o script executará automaticamente:
    *   A instalação das dependências `customtkinter` e `pyinstaller`.
    *   O comando de empacotamento:
        `pyinstaller --noconsole --onefile --collect-all customtkinter --name="AtualizadorNBS" main.py`
        *(A flag `--collect-all customtkinter` garante que todas as fontes, temas e arquivos Tcl do CustomTkinter sejam empacotados dentro do .exe para evitar falhas visuais no Windows).*
5.  Quando o processo terminar, o arquivo compilado estará pronto para uso na pasta **`dist\AtualizadorNBS.exe`**.

Você só precisará distribuir o arquivo `AtualizadorNBS.exe` (e opcionalmente o `config.json` pré-configurado) para o usuário final!
