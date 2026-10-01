$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$audioDir = Join-Path $project 'artifacts\audio'
New-Item -ItemType Directory -Path $audioDir -Force | Out-Null
$segments = Get-Content (Join-Path $PSScriptRoot 'demo-narration.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$voice = New-Object -ComObject SAPI.SpVoice
$voice.Rate = 0
foreach ($segment in $segments) {
    $stream = New-Object -ComObject SAPI.SpFileStream
    try {
        $stream.Open((Join-Path $audioDir ($segment.id + '.wav')), 3, $false)
        $voice.AudioOutputStream = $stream
        $null = $voice.Speak($segment.text)
    } finally {
        $stream.Close()
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($stream)
    }
}
[void][Runtime.InteropServices.Marshal]::ReleaseComObject($voice)
Write-Output 'Generated narration with the installed system voice.'
