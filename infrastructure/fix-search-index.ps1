param(
    [Parameter(Mandatory=$true)]
    [string]$SearchEndpoint,
    
    [Parameter(Mandatory=$true)]
    [string]$SearchKey,
    
    [string]$IndexName = "policies"
)

Write-Host "🔍 Fixing Azure AI Search Index" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host "Endpoint: $SearchEndpoint" -ForegroundColor Cyan
Write-Host "Index: $IndexName" -ForegroundColor Cyan
Write-Host ""

$env:AZURE_SEARCH_ENDPOINT = $SearchEndpoint
$env:AZURE_SEARCH_KEY = $SearchKey
$env:AZURE_SEARCH_INDEX_NAME = $IndexName

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Step 1: Deleting existing index (if exists)..." -ForegroundColor Yellow
try {
    az search index delete `
        --name $IndexName `
        --service-name ($SearchEndpoint -replace 'https://', '' -replace '.search.windows.net', '') `
        --yes `
        2>$null
    Write-Host "✅ Old index deleted" -ForegroundColor Green
} catch {
    Write-Host "⚠️  No existing index to delete" -ForegroundColor Gray
}

Start-Sleep -Seconds 5

Write-Host "`nStep 2: Creating new index with corrected schema..." -ForegroundColor Yellow
$setupScript = Join-Path $scriptDir "setup-search-index-simple.py"

if (Test-Path $setupScript) {
    python $setupScript
    Write-Host "✅ Search index recreated successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Setup script not found: $setupScript" -ForegroundColor Red
    exit 1
}

Write-Host "`n✅ Fix completed!" -ForegroundColor Green
Write-Host "You can now test policy queries in your chat application." -ForegroundColor Cyan

