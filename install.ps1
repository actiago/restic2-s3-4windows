# Define variáveis de diretório e caminho
$UserHome = [System.Environment]::GetFolderPath("UserProfile")
$ProjectDir = "$UserHome\backup_win_s3"
$VenvDir = "$ProjectDir\venv"
$PythonExe = "$VenvDir\Scripts\python.exe"
$ScriptPath = "$ProjectDir\backup_restic.py"
$WorkingDirectory = "$ProjectDir"
$RequirementsPath = "$ProjectDir\requirements.txt"

# Cria o diretório do projeto se não existir
if (!(Test-Path -Path $ProjectDir)) {
    New-Item -ItemType Directory -Path $ProjectDir | Out-Null
    Write-Output "Diretório do projeto criado em $ProjectDir."
}

# Copia os arquivos do script para o diretório do projeto
Write-Output "Copiando arquivos do script para o diretório do projeto..."
Copy-Item -Path ".\backup_restic.py" -Destination $ProjectDir -Force
Copy-Item -Path ".\config.yaml" -Destination $ProjectDir -Force
Copy-Item -Path ".\requirements.txt" -Destination $ProjectDir -Force

# Cria e ativa o ambiente virtual
Write-Output "Criando ambiente virtual..."
python -m venv $VenvDir

# Instala as dependências
Write-Output "Instalando dependências..."
& "$PythonExe" -m pip install -r $RequirementsPath

# Configura a tarefa agendada
$TaskName = "ResticBackupTask2s3"
$Trigger = New-ScheduledTaskTrigger -Daily -At 1:00PM
$Action = New-ScheduledTaskAction -Execute "$PythonExe" -Argument "$ScriptPath backup" -WorkingDirectory $WorkingDirectory
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Verifica se a tarefa já existe
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Output "Removendo tarefa agendada existente '$TaskName'."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Cria a tarefa agendada
Write-Output "Criando nova tarefa agendada '$TaskName'."
Register-ScheduledTask -TaskName $TaskName -Trigger $Trigger -Action $Action -Settings $Settings -Description "Tarefa de backup automático com Restic"

Write-Output "Configuração concluída. O backup será executado diariamente às 1:00 PM."
Write-Output "Para executar o script manualmente, ative o ambiente com:"
Write-Output "    $VenvDir\Scripts\Activate.ps1"
Write-Output "e então execute:"
Write-Output "    & $PythonExe $ScriptPath <comando>"
