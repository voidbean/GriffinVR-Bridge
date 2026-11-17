param([ValidateSet('install','uninstall')] [string]$Action = 'install')
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
[Windows.Forms.Application]::EnableVisualStyles()
$folder = New-Object Windows.Forms.FolderBrowserDialog
$folder.Description = '选择 Modern Warfare Remastered 游戏目录（包含 h1_sp64_ship.exe）'
$folder.ShowNewFolderButton = $false
if ($folder.ShowDialog() -ne 'OK') { exit 0 }
$game = $folder.SelectedPath
$arguments = @($Action, '--game', $game)
if ($Action -eq 'install') {
    $archive = New-Object Windows.Forms.OpenFileDialog
    $archive.Title = '选择原作者发布的 h1-mod-gfl.zip'
    $archive.Filter = 'GFL 1.0 ZIP (*.zip)|*.zip'
    if ($archive.ShowDialog() -ne 'OK') { exit 0 }
    $arguments += @('--gfl', $archive.FileName)
}
& (Join-Path $PSScriptRoot 'runtime\python.exe') (Join-Path $PSScriptRoot 'manage.py') @arguments
exit $LASTEXITCODE
