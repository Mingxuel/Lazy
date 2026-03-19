$repoPath = $PSScriptRoot

Set-Location $repoPath
git add .
Write-Host "git add .：$repoPath" -ForegroundColor Green
git commit -m "Updated"
Write-Host "git commit：$repoPath" -ForegroundColor Green
git push
Write-Host "git push：$repoPath" -ForegroundColor Green
