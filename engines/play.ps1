# Plays an audio file with Windows' built-in MediaPlayer and waits until it ends.
param([Parameter(Mandatory = $true)][string]$File)
Add-Type -AssemblyName PresentationCore
$player = New-Object System.Windows.Media.MediaPlayer
$player.Open([Uri]$File)
$waited = 0
while (-not $player.NaturalDuration.HasTimeSpan -and $waited -lt 50) {
    Start-Sleep -Milliseconds 100
    $waited++
}
$player.Play()
if ($player.NaturalDuration.HasTimeSpan) {
    Start-Sleep -Milliseconds ([int]$player.NaturalDuration.TimeSpan.TotalMilliseconds + 300)
}
$player.Close()
