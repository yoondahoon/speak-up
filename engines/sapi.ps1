# Windows built-in speech (System.Speech / SAPI). Free and offline.
param(
    [Parameter(Mandatory = $true)][string]$TextFile,
    [string]$Lang = "en",
    [string]$Rate = "0",
    [string]$Voice = ""
)
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    if ($Voice) {
        $synth.SelectVoice($Voice)
    } else {
        $match = $synth.GetInstalledVoices() |
            Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -like "$Lang*" } |
            Select-Object -First 1
        if ($match) { $synth.SelectVoice($match.VoiceInfo.Name) }
    }
} catch { }  # fall back to the default system voice
$synth.Rate = [Math]::Max(-10, [Math]::Min(10, [int]$Rate))
try {
    $synth.Speak([IO.File]::ReadAllText($TextFile, [Text.Encoding]::UTF8))
} finally {
    Remove-Item -LiteralPath $TextFile -ErrorAction SilentlyContinue
    $synth.Dispose()
}
