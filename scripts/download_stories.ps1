$destDir = "d:\Project\nifty-reader\downloads\search-niftyarchives-org"
$storiesDir = "$destDir\stories"

if (!(Test-Path $storiesDir)) { New-Item -ItemType Directory -Path $storiesDir }

# Stories to grab
$toGrab = @(
    # Single chapter
    @{ 
        name = "linda-becomes-a-prostitute"
        url = "https://www.nifty.org/nifty/lesbian/hookers/linda-becomes-a-prostitute"
        path = "linda-becomes-a-prostitute.txt"
    },
    # Series
    @{
        name = "the-bus-stop-series"
        url = "https://www.nifty.org/nifty/gay/adult-youth/the-bus-stop-series"
        path = "the-bus-stop-series/index.html"
        parts = @(
            @{ url = "https://www.nifty.org/nifty/gay/adult-youth/the-bus-stop-series/the-bus-stop-1"; path = "the-bus-stop-1.txt" },
            @{ url = "https://www.nifty.org/nifty/gay/adult-youth/the-bus-stop-series/the-bus-stop-2"; path = "the-bus-stop-2.txt" },
            @{ url = "https://www.nifty.org/nifty/gay/adult-youth/the-bus-stop-series/the-bus-stop-3"; path = "the-bus-stop-3.txt" },
            @{ url = "https://www.nifty.org/nifty/gay/adult-youth/the-bus-stop-series/the-bus-stop-4"; path = "the-bus-stop-4.txt" }
        )
    },
    # Another series
    @{
        name = "bred-in-secret"
        url = "https://www.nifty.org/nifty/gay/adult-friends/bred-in-secret"
        path = "bred-in-secret/index.html"
        parts = @(
            @{ url = "https://www.nifty.org/nifty/gay/adult-friends/bred-in-secret/bred-in-secret-1"; path = "bred-in-secret-1.txt" },
            @{ url = "https://www.nifty.org/nifty/gay/adult-friends/bred-in-secret/bred-in-secret-2"; path = "bred-in-secret-2.txt" }
        )
    }
)

foreach ($story in $toGrab) {
    Write-Host "Grabbing $($story.name)..."
    if ($story.parts) {
        $storyStoryDir = "$storiesDir\$($story.name)"
        if (!(Test-Path $storyStoryDir)) { New-Item -ItemType Directory -Path $storyStoryDir }
        Invoke-WebRequest -Uri $story.url -OutFile "$storyStoryDir\index.html"
        foreach ($part in $story.parts) {
            Write-Host "  Part $($part.url)..."
            Invoke-WebRequest -Uri $part.url -OutFile "$storyStoryDir\$($part.path)"
        }
        
        # Update series index internal relative links
        $sIdxPath = "$storyStoryDir\index.html"
        $siContent = Get-Content $sIdxPath -Raw
        foreach ($part in $story.parts) {
            $baseName = $part.path -replace '\.txt$', ''
            $siContent = $siContent -replace "href=`"$baseName`"", "href=`"$($part.path)`""
        }
        Set-Content -Path $sIdxPath -Value $siContent
    } else {
        Invoke-WebRequest -Uri $story.url -OutFile "$storiesDir\$($story.path)"
    }
}

# Update main index.html to use local story links
$idxPath = "$destDir\index.html"
$content = Get-Content $idxPath -Raw

# Replace links for the specific stories we grabbed
# Single
$content = $content -replace 'https://www.nifty.org/nifty/lesbian/hookers/linda-becomes-a-prostitute', 'stories/linda-becomes-a-prostitute.txt'
# Series indices
$content = $content -replace 'https://www.nifty.org/nifty/gay/adult-youth/the-bus-stop-series/', 'stories/the-bus-stop-series/index.html'
$content = $content -replace 'https://www.nifty.org/nifty/gay/adult-youth/the-bus-stop-series', 'stories/the-bus-stop-series/index.html'
$content = $content -replace 'https://www.nifty.org/nifty/gay/adult-friends/bred-in-secret/', 'stories/bred-in-secret/index.html'
$content = $content -replace 'https://www.nifty.org/nifty/gay/adult-friends/bred-in-secret', 'stories/bred-in-secret/index.html'

# Parts for the bus stop (in search results)
$content = $content -replace 'https://www.nifty.org/nifty/gay/adult-youth/the-bus-stop-series/the-bus-stop-1', 'stories/the-bus-stop-series/the-bus-stop-1.txt'
$content = $content -replace 'https://www.nifty.org/nifty/gay/adult-youth/the-bus-stop-series/the-bus-stop-2', 'stories/the-bus-stop-series/the-bus-stop-2.txt'
$content = $content -replace 'https://www.nifty.org/nifty/gay/adult-youth/the-bus-stop-series/the-bus-stop-3', 'stories/the-bus-stop-series/the-bus-stop-3.txt'
$content = $content -replace 'https://www.nifty.org/nifty/gay/adult-youth/the-bus-stop-series/the-bus-stop-4', 'stories/the-bus-stop-series/the-bus-stop-4.txt'

# Parts for bred in secret
$content = $content -replace 'https://www.nifty.org/nifty/gay/adult-friends/bred-in-secret/bred-in-secret-1', 'stories/bred-in-secret/bred-in-secret-1.txt'
$content = $content -replace 'https://www.nifty.org/nifty/gay/adult-friends/bred-in-secret/bred-in-secret-2', 'stories/bred-in-secret/bred-in-secret-2.txt'

Set-Content -Path $idxPath -Value $content

Write-Host "Done!"
