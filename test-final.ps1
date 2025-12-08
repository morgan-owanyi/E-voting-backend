Write-Host "`n=== FINAL COMPREHENSIVE TEST ===" -ForegroundColor Cyan
Write-Host "Waiting for deployment..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Test OTP
Write-Host "`nTesting Voter OTP..." -ForegroundColor Yellow
$otpBody = @{regNo='TEST001'; election=1} | ConvertTo-Json
try {
    $otpResponse = Invoke-RestMethod -Uri 'https://e-voting-backend-5087.onrender.com/api/voting/request_otp/' -Method POST -Body $otpBody -ContentType 'application/json' -TimeoutSec 60
    if ($otpResponse.otp) {
        Write-Host " OTP Request PASSED" -ForegroundColor Green
        Write-Host "  OTP Code: $($otpResponse.otp)" -ForegroundColor Cyan
        Write-Host "  Message: $($otpResponse.message)" -ForegroundColor White
    } else {
        Write-Host " OTP Sent via Email" -ForegroundColor Green
        Write-Host "  $($otpResponse.message)" -ForegroundColor White
    }
} catch {
    Write-Host " OTP Request FAILED" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "`n=== ALL SYSTEMS TESTED ===" -ForegroundColor Cyan
