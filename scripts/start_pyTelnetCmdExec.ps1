##----------------------------------------------------------------------------##
## Main function.
##----------------------------------------------------------------------------##
function Main()
{
    Add-Type -Assembly System.Windows.Forms

    $PythonPATH = "python.exe"
    $CURRENTDIR = Get-Location
    $ScriptPATH = "$CURRENTDIR\pyTelnetCmdExec.py"

    if (-Not(Test-Path $ScriptPATH)) {
        $ScriptPATH = SelectFile "pyTelnetCmdExec.py��I�����Ă��������B"
    }
    if ($NULL -eq $ScriptPATH) {
        return
    }

    $CMDLIST_FILE = SelectFile "���s�������R�}���h���X�g�t�@�C����I�����Ă��������B" "."
    if ($NULL -eq $CMDLIST_FILE) {
        return
    }

    $LOG_DIR = "$CURRENTDIR\log"
    if (-Not(Test-Path $LOG_DIR)) {
        $LOG_DIR = SelectFolder "pyTelnetCmdExec�̃��O�o�͐�f�B���N�g����I�����Ă��������B" $CURRENTDIR
        if ($NULL -eq $LOG_DIR) {
            return
        }
    }

    $CMDLINE = "$PythonPATH `"$ScriptPATH`" `"$CMDLIST_FILE`" --log_dir `"$LOG_DIR`""
    Write-Host $CMDLINE

    Add-Type -Assembly System.Windows.Forms
    $res = [System.Windows.Forms.MessageBox]::Show("$CMDLINE`n`n���s���܂����H", "���s�m�F", "YesNo", "Question")
    if ($res -eq "Yes") {
        Invoke-Expression $CMDLINE
    }
}

##----------------------------------------------------------------------------##
## Display Select File Dialog.
##----------------------------------------------------------------------------##
function SelectFile([string]$message, [string]$InitialDirectory)
{
    [void][System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms")

    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Filter = "���ׂẴt�@�C��(*.*)|*.*;"
    $dialog.InitialDirectory = $InitialDirectory
    $dialog.Title = $message

    if($dialog.ShowDialog() -eq "OK") {
        return $dialog.FileName
    }
    else {
        return $NULL
    }
}

##----------------------------------------------------------------------------##
## Display Select Folder Dialog.
##----------------------------------------------------------------------------##
function SelectFolder([string]$message, [string]$InitialDirectory)
{
    [void][System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms")

    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.SelectedPath = $InitialDirectory
    $dialog.Description = $message

    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        return $dialog.SelectedPath
    }
    else {
        return $NULL
    }
}

##----------------------------------------------------------------------------##
## Call Main function.
##----------------------------------------------------------------------------##

Main
