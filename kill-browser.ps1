Get-Process | Where-Object { $_.Name -match 'chrome|playwright|chromium' } | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\ms-playwright\mcp-chrome-*" -ErrorAction SilentlyContinue
Write-Host 'cleaned'
