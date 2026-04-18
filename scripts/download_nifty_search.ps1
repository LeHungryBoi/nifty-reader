$baseUrl = "https://search.niftyarchives.org/"
$destDir = "d:\Project\nifty-reader\downloads\search-niftyarchives-org"

if (!(Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir }
if (!(Test-Path "$destDir\css")) { New-Item -ItemType Directory -Path "$destDir\css" }
if (!(Test-Path "$destDir\js")) { New-Item -ItemType Directory -Path "$destDir\js" }
if (!(Test-Path "$destDir\fonts")) { New-Item -ItemType Directory -Path "$destDir\fonts" }

# Download HTML
Invoke-WebRequest -Uri $baseUrl -OutFile "$destDir\index.html"

# Assets list
$assets = @(
    @{ url = "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css"; path = "css\bootstrap.min.css" },
    @{ url = "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap-theme.min.css"; path = "css\bootstrap-theme.min.css" },
    @{ url = "https://search.niftyarchives.org/css/search.css"; path = "css\search.css" },
    @{ url = "https://www.googletagmanager.com/gtag/js?id=G-EM5SLJVFFJ"; path = "js\gtag.js" },
    @{ url = "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/fonts/glyphicons-halflings-regular.woff2"; path = "fonts\glyphicons-halflings-regular.woff2" },
    @{ url = "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/fonts/glyphicons-halflings-regular.woff"; path = "fonts\glyphicons-halflings-regular.woff" },
    @{ url = "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/fonts/glyphicons-halflings-regular.ttf"; path = "fonts\glyphicons-halflings-regular.ttf" }
)

foreach ($asset in $assets) {
    Write-Host "Downloading $($asset.url)..."
    Invoke-WebRequest -Uri $asset.url -OutFile "$destDir\$($asset.path)"
}

# Update index.html to use local assets
$content = Get-Content "$destDir\index.html" -Raw
$content = $content -replace 'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css', 'css/bootstrap.min.css'
$content = $content -replace 'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap-theme.min.css', 'css/bootstrap-theme.min.css'
$content = $content -replace '/css/search.css', 'css/search.css'
$content = $content -replace 'https://www.googletagmanager.com/gtag/js\?id=G-EM5SLJVFFJ', 'js/gtag.js'

# Fix Bootstrap fonts path in local css files
$cssPath = "$destDir\css\bootstrap.min.css"
$cssContent = Get-Content $cssPath -Raw
$cssContent = $cssContent -replace '\.\./fonts/', '../fonts/' # Ensure it points correctly
Set-Content -Path $cssPath -Value $cssContent

Set-Content -Path "$destDir\index.html" -Value $content

Write-Host "Done!"
