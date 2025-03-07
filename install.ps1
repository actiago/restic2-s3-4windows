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

# Configura a tarefa agendada diária para backup
$TaskName = "ResticBackupTask2s3"
$TriggerTime = Read-Host "Digite o horário para o agendamento (formato HH:MM)"
$Trigger = New-ScheduledTaskTrigger -Daily -At $TriggerTime
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

# Tarefa semanal para verificação do repositório (check)
$CheckTaskName = "ResticCheckTask"
$CheckTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 2:00AM
$CheckAction = New-ScheduledTaskAction -Execute "$PythonExe" -Argument "$ScriptPath check" -WorkingDirectory $WorkingDirectory
$CheckSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Verifica se a tarefa já existe
if (Get-ScheduledTask -TaskName $CheckTaskName -ErrorAction SilentlyContinue) {
    Write-Output "Removendo tarefa agendada existente '$CheckTaskName'."
    Unregister-ScheduledTask -TaskName $CheckTaskName -Confirm:$false
}

# Cria a tarefa agendada
Write-Output "Criando nova tarefa agendada '$CheckTaskName'."
Register-ScheduledTask -TaskName $CheckTaskName -Trigger $CheckTrigger -Action $CheckAction -Settings $CheckSettings -Description "Tarefa de verificação semanal do repositório Restic"

# Tarefa quinzenal para remoção de snapshots antigos (purge)
$PurgeTaskName = "ResticPurgeTask"
$PurgeAction = New-ScheduledTaskAction -Execute "$PythonExe" -Argument "$ScriptPath purge" -WorkingDirectory $WorkingDirectory
$PurgeSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Cria dois triggers semanais para simular a execução quinzenal
$Trigger1 = New-ScheduledTaskTrigger -Weekly -WeeksInterval 2 -DaysOfWeek Monday -At 3:00AM
$Trigger2 = New-ScheduledTaskTrigger -Weekly -WeeksInterval 2 -DaysOfWeek Thursday -At 3:00AM

# Combina os triggers em uma única tarefa
$PurgeTriggers = @($Trigger1, $Trigger2)

# Verifica se a tarefa já existe
if (Get-ScheduledTask -TaskName $PurgeTaskName -ErrorAction SilentlyContinue) {
    Write-Output "Removendo tarefa agendada existente '$PurgeTaskName'."
    Unregister-ScheduledTask -TaskName $PurgeTaskName -Confirm:$false
}

# Cria a tarefa agendada
Write-Output "Criando nova tarefa agendada '$PurgeTaskName'."
Register-ScheduledTask -TaskName $PurgeTaskName -Trigger $PurgeTriggers -Action $PurgeAction -Settings $PurgeSettings -Description "Tarefa de remoção quinzenal de snapshots antigos do Restic"

Write-Output "Configuração concluída. O backup será executado diariamente às $TriggerTime."
Write-Output "Para executar o script manualmente, ative o ambiente com:"
Write-Output "    $VenvDir\Scripts\Activate.ps1"
Write-Output "e então execute:"
Write-Output "    & $PythonExe $ScriptPath <comando>"