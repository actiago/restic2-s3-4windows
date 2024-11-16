import subprocess
import os
import sys
import yaml
import requests
from datetime import datetime
import boto3
from botocore.exceptions import BotoCoreError, ClientError

# Função para buscar parâmetros do AWS Parameter Store
def get_parameter_from_ssm(parameter_name, with_decryption=True):
    try:
        ssm_client = boto3.client("ssm")
        response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=with_decryption)
        return response["Parameter"]["Value"]
    except (BotoCoreError, ClientError) as e:
        print(f"Erro ao buscar o parâmetro '{parameter_name}': {e}")
        return None


# Função para enviar notificações usando ntfy.sh
def send_notification(topic, title, message, priority="default"):
    url = f"https://ntfy.sh/{topic}"
    headers = {
        "Title": title,
        "Priority": priority
    }
    try:
        response = requests.post(url, data=message, headers=headers)
        if response.status_code == 200:
            print(f"Notificação enviada: {title} - {message}")
        else:
            print(f"Falha ao enviar notificação: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Erro ao enviar notificação: {e}")


# Carregar arquivo de configuração
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

# Configurações principais
restic_path = config["restic"]["path"]
bucket_url = config["restic"]["s3_bucket_url"]
log_dir = config["backup"]["log_dir"]
os.makedirs(log_dir, exist_ok=True)

# Função para executar comandos do Restic
def run_restic_command(command_args, log_filename):
    log_file_path = os.path.join(log_dir, f"{log_filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    with open(log_file_path, "w") as log_file:
        process = subprocess.run(command_args, stdout=log_file, stderr=subprocess.STDOUT)
    if process.returncode == 0:
        print(f"Operação '{log_filename}' concluída com sucesso. Log salvo em: {log_file_path}")
        return True
    else:
        print(f"Erro ao executar a operação '{log_filename}'. Verifique o log para mais detalhes.")
        return False

# Função para realizar o backup
def backup():
    print("Iniciando backup para S3...")
    
    # Recuperar credenciais e senha do Parameter Store
    s3_credentials = get_parameter_from_ssm("restic_s3_credentials")
    restic_password = get_parameter_from_ssm("restic_password")

    if not s3_credentials or not restic_password:
        send_notification("backup_topic", "Erro no Backup", "Falha ao buscar parâmetros do AWS Parameter Store.", "high")
        return

    # Configurar variáveis de ambiente para o Restic
    os.environ["AWS_ACCESS_KEY_ID"], os.environ["AWS_SECRET_ACCESS_KEY"] = s3_credentials.split(":")
    os.environ["RESTIC_PASSWORD"] = restic_password

    success = True
    for source in config["backup"]["sources"]:
        command = [
            restic_path,
            "-r", f"s3:{bucket_url}",
            "backup", source
        ]
        if not run_restic_command(command, "backup"):
            success = False

    if success:
        send_notification("backup_topic", "Backup Finalizado", "Backup para S3 realizado com sucesso!", "high")
    else:
        send_notification("backup_topic", "Erro no Backup", "Houve falhas no backup. Verifique os logs.", "high")

# Função principal
def main():
    if len(sys.argv) < 2:
        print("Uso: python backup_restic.py <comando>")
        print("Comandos disponíveis: backup")
        sys.exit(1)

    command = sys.argv[1]
    if command == "backup":
        backup()
    else:
        print(f"Comando desconhecido: {command}")
        print("Comandos disponíveis: backup")

if __name__ == "__main__":
    main()
