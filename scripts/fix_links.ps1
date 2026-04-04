$destDir = "d:\Project\nifty-reader\downloads\search-niftyarchives-org"
$idxPath = "$destDir\index.html"
$content = Get-Content $idxPath -Raw

# Replace specific parts FIRST (more specific matches)
$content = $content -replace 'stories/the-bus-stop-series/index.html/the-bus-stop-1', 'stories/the-bus-stop-series/the-bus-stop-1.txt'
$content = $content -replace 'stories/the-bus-stop-series/index.html/the-bus-stop-2', 'stories/the-bus-stop-series/the-bus-stop-2.txt'
$content = $content -replace 'stories/the-bus-stop-series/index.html/the-bus-stop-3', 'stories/the-bus-stop-series/the-bus-stop-3.txt'
$content = $content -replace 'stories/the-bus-stop-series/index.html/the-bus-stop-4', 'stories/the-bus-stop-series/the-bus-stop-4.txt'

$content = $content -replace 'stories/bred-in-secret/index.html/bred-in-secret-1', 'stories/bred-in-secret/bred-in-secret-1.txt'
$content = $content -replace 'stories/bred-in-secret/index.html/bred-in-secret-2', 'stories/bred-in-secret/bred-in-secret-2.txt'

# Also check if any were missed and still have the full original URL
$content = $content -replace 'https://www.nifty.org/nifty/gay/adult-youth/the-bus-stop-series/the-bus-stop-1', 'stories/the-bus-stop-series/the-bus-stop-1.txt'
$content = $content -replace 'https://www.nifty.org/nifty/gay/adult-youth/the-bus-stop-series/the-bus-stop-2', 'stories/the-bus-stop-series/the-bus-stop-2.txt'
$content = $content -replace 'https://www.nifty.org/nifty/gay/adult-youth/the-bus-stop-series/the-bus-stop-3', 'stories/the-bus-stop-series/the-bus-stop-3.txt'
$content = $content -replace 'https://www.nifty.org/nifty/gay/adult-youth/the-bus-stop-series/the-bus-stop-4', 'stories/the-bus-stop-series/the-bus-stop-4.txt'

$content = $content -replace 'https://www.nifty.org/nifty/gay/adult-friends/bred-in-secret/bred-in-secret-1', 'stories/bred-in-secret/bred-in-secret-1.txt'
$content = $content -replace 'https://www.nifty.org/nifty/gay/adult-friends/bred-in-secret/bred-in-secret-2', 'stories/bred-in-secret/bred-in-secret-2.txt'

Set-Content -Path $idxPath -Value $content
Write-Host "Links fixed!"
