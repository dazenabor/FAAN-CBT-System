Set-Location -LiteralPath 'c:\Users\Dublos shoprite\Documents\cbt_app'
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
try {
    $login = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/login' -Method Post -Body @{user_id='testuser'; pin='1234'} -WebSession $session -UseBasicParsing -ErrorAction Stop
    Write-Output 'Login response received'
} catch {
    Write-Output "Login failed: $($_.Exception.Message)"
    exit 1
}
try {
    $exam = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/exam' -Method Get -WebSession $session -UseBasicParsing -ErrorAction Stop
    if ($exam.Content -match 'Start Exam' -or $exam.Content -match 'Start') { Write-Output 'Start button appears on exam page' } else { Write-Output 'Start button not found on exam page' }
} catch {
    Write-Output "Exam GET failed: $($_.Exception.Message)"
    exit 1
}
try {
    $start = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/exam' -Method Post -Body @{action='start_exam'} -WebSession $session -UseBasicParsing -ErrorAction Stop
    Write-Output 'Posted start_exam'
} catch {
    Write-Output "Start POST failed: $($_.Exception.Message)"
}
try {
    $exam2 = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/exam' -Method Get -WebSession $session -UseBasicParsing -ErrorAction Stop
    if ($exam2.Content -match 'remaining' -or $exam2.Content -match 'Time') { Write-Output 'Exam running / remaining shown' } else { Write-Output 'Exam running check: content does not show remaining' }
} catch {
    Write-Output "Final exam GET failed: $($_.Exception.Message)"
    exit 1
}
Write-Output 'Smoke test finished'
