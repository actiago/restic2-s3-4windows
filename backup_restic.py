import subprocess
import os
import sys
import yaml
import requests
from datetime import datetime
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import shutil

# Função para buscar parâmetros do AWS Parameter Store
def get_parameter_from_ssm(parameter_name, with_decryption=True):
    try:
        ssm_client = boto3.client("ssm")
        response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=with_decryption)
        return response["Parameter"]["Value"]
    except (BotoCoreError, ClientError) as e:
        print(f"Erro ao buscar o parâmetro '{parameter_name}': {e}")
        return None

# Função para enviar notificações via ntfy.sh
def send_notification(title, message, priority="default"):
    # Verifica se as configurações do ntfy estão definidas no config.yaml
    if "ntfy" not in config or "url" not in config["ntfy"] or "topic" not in config["ntfy"]:
        print("Configurações do ntfy não encontradas no config.yaml.")
        return

    # Recupera a URL e o tópico do ntfy do config.yaml
    ntfy_url = config["ntfy"]["url"]
    ntfy_topic = config["ntfy"]["topic"]

    # Monta a URL completa para enviar a notificação
    url = f"{ntfy_url}/{ntfy_topic}"
    headers = {
        "Title": title.encode("utf-8").decode("utf-8"),
        "Priority": priority
    }

    try:
        response = requests.post(url, data=message.encode("utf-8"), headers=headers)
        if response.status_code == 200:
            print(f"Notificação enviada: {title} - {message}")
        else:
            print(f"Falha ao enviar notificação: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Erro ao enviar notificação: {e}")

# Carregar configurações do YAML
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

# Configurações do script
restic_path = config["restic"]["path"]
bucket_url = config["restic"]["s3_bucket_url"]
log_dir = config["backup"]["log_dir"]
os.makedirs(log_dir, exist_ok=True)

# Configurações do ntfy
ntfy_topic = config["ntfy"]["topic"]

# Configurações do AWS Parameter Store
restic_password_param = config["aws_parameter_store"]["restic_password"]
s3_credentials_param = config["aws_parameter_store"]["s3_credentials"]

# Função para executar comandos Restic
def run_restic_command(command_args, log_filename):
    log_file_path = os.path.join(log_dir, f"{log_filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    with open(log_file_path, "w") as log_file:
        process = subprocess.run(command_args, stdout=log_file, stderr=subprocess.STDOUT)
    if process.returncode == 0:
        print(f"Operação '{log_filename}' concluída com sucesso. Log salvo em: {log_file_path}")
        return True
    else:
        print(f"Erro ao executar a operação '{log_filename}'. Verifique o log.")
        return False
    
def run_restic_command(command_args, log_filename, env=None):
    log_file_path = os.path.join(log_dir, f"{log_filename}.log")  # Arquivo de log único
    try:
        # Abre o arquivo de log no modo append (adiciona ao final do arquivo)
        with open(log_file_path, "a") as log_file:
            # Adiciona um cabeçalho com a data e hora da execução
            log_file.write(f"\n{'=' * 50}\n")
            log_file.write(f"Execução em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write(f"Comando: {' '.join(command_args)}\n")
            log_file.write(f"{'=' * 50}\n")

            # Executa o comando e redireciona a saída para o arquivo de log
            process = subprocess.run(command_args, stdout=log_file, stderr=subprocess.STDOUT, text=True, env=env)

        # Verifica o resultado da execução
        if process.returncode == 0:
            print(f"Operação '{log_filename}' concluída com sucesso. Log salvo em: {log_file_path}")
            return True
        else:
            print(f"Erro ao executar a operação '{log_filename}'. Verifique o log.")
            print(f"Stderr: {process.stderr}")
            return False
    except Exception as e:
        print(f"Erro inesperado ao executar o comando: {e}")
        return False

# Função para realizar o backup
def backup():
    print("Iniciando backup para S3...")
    
    # Recuperar credenciais e senha do Parameter Store
    s3_credentials = get_parameter_from_ssm(s3_credentials_param)
    restic_password = get_parameter_from_ssm(restic_password_param)

    if not s3_credentials or not restic_password:
        send_notification("Erro no Backup", "Falha ao buscar parâmetros do AWS Parameter Store.", "high")
        return

    # Configurar variáveis de ambiente temporariamente
    env = os.environ.copy()
    env["AWS_ACCESS_KEY_ID"], env["AWS_SECRET_ACCESS_KEY"] = s3_credentials.split(":")
    env["RESTIC_PASSWORD"] = restic_password

    success = True
    for source in config["backup"]["sources"]:
        command = [restic_path, "-r", f"s3:{bucket_url}", "backup", source]
        if not run_restic_command(command, "backup", env=env):
            success = False

    if success:
        send_notification("Backup Finalizado", "Backup para S3 realizado com sucesso! 🚀", "high")
    else:
        send_notification("Erro no Backup", "Falha no backup para S3. Verifique os logs.", "high")

# Função para verificar a integridade do repositório
def check():
    print("Verificando a integridade do repositório...")
    
    restic_password = get_parameter_from_ssm("restic_password")
    if not restic_password:
        send_notification("Erro no Check S3", "Falha ao buscar senha do repositório.", "high")
        return

    os.environ["RESTIC_PASSWORD"] = restic_password
    command = [restic_path, "-r", f"s3:{bucket_url}", "check"]
    
    if run_restic_command(command, "check"):
        send_notification("Check S3 Finalizado", "Verificação do repositório bem-sucedida! ✅", "high")
    else:
        send_notification("Erro no Check S3", "Falha na verificação do repositório. ⚠️", "high")

# Função para remover snapshots antigos (purge)
def purge():
    print("Removendo snapshots antigos...")
    
    restic_password = get_parameter_from_ssm("restic_password")
    if not restic_password:
        send_notification("Erro no Purge S3", "Falha ao buscar senha do repositório.", "high")
        return

    os.environ["RESTIC_PASSWORD"] = restic_password

    # Configurar a política de retenção
    retention_policies = config["purge"]
    command = [
        restic_path, "-r", f"s3:{bucket_url}", "forget",
        "--keep-daily", str(retention_policies["keep_daily"]),
        "--keep-weekly", str(retention_policies["keep_weekly"]),
        "--keep-monthly", str(retention_policies["keep_monthly"]),
        "--prune"
    ]

    if run_restic_command(command, "purge"):
        send_notification("Purge Finalizado S3", "Snapshots antigos removidos com sucesso! 🗑️", "high")
    else:
        send_notification("Erro no Purge S3", "Falha ao remover snapshots antigos. ⚠️", "high")

def backup_config():
    # Verifica se o diretório de backup de configuração está definido no config.yaml
    if "config_backup" not in config or "dir" not in config["config_backup"]:
        print("Diretório de backup de configuração não definido no config.yaml.")
        return

    backup_dir = config["config_backup"]["dir"]
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")
    shutil.copy("config.yaml", backup_path)
    print(f"Backup do arquivo de configuração salvo em: {backup_path}")

def check_for_updates():
    try:
        response = requests.get("https://api.github.com/repos/seu_usuario/seu_repositorio/releases/latest")
        latest_version = response.json()["tag_name"]
        current_version = "v0.1.0"  # Substitua pela versão atual do script
        if latest_version != current_version:
            print(f"Nova versão disponível: {latest_version}")
            # Adicione lógica para baixar e aplicar a atualização
    except Exception as e:
        print(f"Erro ao verificar atualizações: {e}")

# Função principal
def main():
    check_for_updates()
    if len(sys.argv) < 2:
        print("Uso: python backup_restic.py <comando>")
        print("Comandos disponíveis: backup, check, purge, backup_config")
        sys.exit(1)

    command = sys.argv[1]
    if command == "backup":
        backup()
    elif command == "check":
        check()
    elif command == "purge":
        purge()
    elif command == "backup_config":
        backup_config()
    else:
        print(f"Comando desconhecido: {command}")
        print("Comandos disponíveis: backup, check, purge, backup_config")

if __name__ == "__main__":
    main()
