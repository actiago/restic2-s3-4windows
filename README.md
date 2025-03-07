# Backup Automático com Restic e S3 no Windows

Este projeto realiza backups automáticos de diretórios no Windows usando o [Restic](https://restic.net/) e armazena os backups em um bucket S3 da AWS. O script é agendado para execução diária, semanal e quinzenal, e inclui funcionalidades para verificação de integridade e remoção de snapshots antigos.

---

## **Funcionalidades**

- **Backup Diário**: Realiza o backup dos diretórios configurados diariamente.
- **Verificação Semanal**: Verifica a integridade do repositório de backups toda semana.
- **Purge Quinzenal**: Remove snapshots antigos a cada 15 dias, de acordo com a política de retenção.
- **Notificações**: Envia notificações via [ntfy.sh](https://ntfy.sh/) sobre o status das operações.
- **Backup de Configuração**: Faz backup do arquivo de configuração (`config.yaml`) em um diretório especificado.

---

## **Requisitos**

- **Python 3.x**: O script foi desenvolvido em Python.
- [**Restic**](https://restic.net/): O executável do Restic deve estar instalado e configurado.
- **Conta AWS**: Com permissões para acessar o S3 e o AWS Systems Manager Parameter Store.
- **AWS Cli**: [Instalado e configurado](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [**ntfy.sh**](https://ntfy.sh/): Para receber notificações (opcional).
- **Powershell 7**: O script de instalação foi desenvolvido baseado na versão 7 do powershell

---

## **Configuração**

### 1. **Instalação**

Antes de qualquer passo, certifique-se de que tenha realizado os seguintes passos:

1. Crie um repositório no AWS S3: [Passos neste documento](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html#amazon-s3).
   1. Lembre-se se salvar a senha criada para que seja adicionada ao parâmetro `restic_password` do Parameter Store.
2. Tenha criado os parâmetros do AWS Parameter Store conforme descrito na sessão [**3. AWS Parameter Store**](#3-aws-parameter-store).
3. Tenha o AWS Cli configurado em seu dispositivo

**Para instalar, siga os passos**:

1. Clone o repositório ou baixe os arquivos do projeto.
2. Edite o arquivo config.yaml de acordo com sua preferência.
3. Crie um ambiente virtual Python e instale as dependências:

   ```powershell
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. Execute o script de instalação para configurar as tarefas agendadas:

    ```powershell
    .\install.ps1
    ```

## 2. **Arquivo de Configuração** (config.yaml)

Edite o arquivo `config.yaml` para definir as configurações do projeto:

```yaml
restic:
  path: "C:\\restic\\restic.exe"  # Caminho para o executável do Restic
  s3_bucket_url: "s3.amazonaws.com/s3-bucket"  # URL do bucket S3

backup:
  sources:
    - "C:\\Users\\username\\Documents"  # Diretórios para backup
    - "C:\\Users\\username\\Books\\myBook.pdf" # Para backup de arquivo único
  log_dir: "C:\\Users\\username\\Temp\\logs\\restic_s3\\"  # Diretório de logs

purge:
  keep_daily: 7  # Número de snapshots diários a manter
  keep_weekly: 4  # Número de snapshots semanais a manter
  keep_monthly: 12  # Número de snapshots mensais a manter

ntfy:
  url: "https://ntfy.sh"  # URL do servidor ntfy
  topic: "my_ntfy_topic"  # Tópico do ntfy para notificações

aws_parameter_store:
  restic_password: "restic_password"  # Nome do parâmetro da senha do Restic
  s3_credentials: "restic_s3_credentials"  # Nome do parâmetro das credenciais S3

config_backup:
  dir: "C:\\Users\\username\\backup_win_s3\\config_backups"  # Diretório para backup do config.yaml
```

## 3. **AWS Parameter Store**

Certifique-se de que os seguintes parâmetros estão configurados no AWS Systems Manager Parameter Store:

**restic_password:** Senha do repositório Restic.

**restic_s3_credentials:** Credenciais da AWS no formato `AWS_ACCESS_KEY_ID:AWS_SECRET_ACCESS_KEY` .

---

## **Uso**

Uma vez instalado, o script pode ser executado manualmente com os seguintes comandos:

Primeiramente, ative o ambiente com:

```powershell
   C:\Users\username\backup_win_s3\venv\Scripts\Activate.ps1
```

Em seguida:

- **backup**: Realiza o backup dos diretórios configurados

```powershell
   & C:\Users\username\backup_win_s3\venv\Scripts\python.exe C:\Users\username\backup_win_s3\backup_restic.py backup
```

- **Check**: Verifica a integridade do repositório.

```powershell
   & C:\Users\username\backup_win_s3\venv\Scripts\python.exe C:\Users\username\backup_win_s3\backup_restic.py check
```

- **Purge**: Remove snapshots antigos de acordo com a política de retenção.

```powershell
   & C:\Users\username\backup_win_s3\venv\Scripts\python.exe C:\Users\username\backup_win_s3\backup_restic.py purge
```

- **Backup Config**: Faz backup do arquivo de configuração (config.yaml).

```powershell
   & C:\Users\username\backup_win_s3\venv\Scripts\python.exe C:\Users\username\backup_win_s3\backup_restic.py backup_config
```

## Tarefas Agendadas

O script de instalação (install.ps1) configura as seguintes tarefas agendadas:

1. **Backup Diário**: Executa o backup diariamente no horário especificado.
2. **Verificação Semanal**: Verifica a integridade do repositório toda segunda-feira às 2:00 AM.
3. **Purge Quinzenal**: Remove snapshots antigos a cada 15 dias, alternando entre segundas e quintas-feiras às 3:00 AM.

## Notificações

O script envia notificações via ntfy.sh sobre o status das operações. Certifique-se de configurar o tópico no arquivo `config.yaml`.

## Logs
Os logs das operações são salvos no diretório especificado em config.yaml (campo log_dir). Cada tipo de operação (backup, check, purge) tem seu próprio arquivo de log:

- backup.log
- check.log
- purge.log

## Contribuição
Se você quiser contribuir para este projeto, siga estas etapas:

1. Faça um fork do repositório.
2. Crie uma branch para sua feature (git checkout -b feature/nova-feature).
3. Commit suas mudanças (git commit -m 'Adicionando nova feature').
4. Faça push para a branch (git push origin feature/nova-feature).
5. Abra um pull request.

## Licença

Este projeto está licenciado sob a [MIT License](LICENSE).

## Versão

1.0.0