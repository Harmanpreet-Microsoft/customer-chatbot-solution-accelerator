#!/usr/bin/env pwsh
#Requires -Version 7.0

<#
.SYNOPSIS
    Builds the backend (src/api) and frontend (src/App) container images inside
    Azure Container Registry using `az acr build`, then updates the two App
    Services (api-<suffix> and app-<suffix>) to run those images.

.DESCRIPTION
    Uses `az acr build` so image build/push happens in ACR (no local Docker
    required). Values are read from the current `azd` environment when
    possible, otherwise from the last successful ARM deployment in the
    resource group. All parameters can be overridden on the command line.

.PARAMETER ResourceGroup
    Azure resource group that contains ACR and the App Services.
.PARAMETER AcrName
    Azure Container Registry name (without the .azurecr.io suffix).
.PARAMETER BackendAppName
    Backend App Service name (defaults to api-<solution suffix>).
.PARAMETER FrontendAppName
    Frontend App Service name (defaults to app-<solution suffix>).
.PARAMETER ImageTag
    Tag to apply to both images. Defaults to a UTC timestamp.
.PARAMETER BackendImage
    Backend image repository name. Defaults to "backend".
.PARAMETER FrontendImage
    Frontend image repository name. Defaults to "frontend".
.PARAMETER SkipBackend
    Skip building/updating the backend.
.PARAMETER SkipFrontend
    Skip building/updating the frontend.

.EXAMPLE
    ./build_push_images.ps1

.EXAMPLE
    ./build_push_images.ps1 -ResourceGroup rg-ccsa -ImageTag v1.2.3
#>

param(
    [string]$ResourceGroup,
    [string]$AcrName,
    [string]$BackendAppName,
    [string]$FrontendAppName,
    [string]$ImageTag,
    [string]$BackendImage = 'backend',
    [string]$FrontendImage = 'frontend',
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [switch]$ShowLogs
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot   = Resolve-Path (Join-Path $scriptDir '..' '..')
$backendCtx = Join-Path $repoRoot 'src/api'
$frontendCtx = Join-Path $repoRoot 'src/App'

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Test-CommandAvailable {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-AzdEnvValue {
    param([string]$Key)
    if (-not (Test-CommandAvailable 'azd')) { return $null }
    $value = azd env get-value $Key 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    if ([string]::IsNullOrWhiteSpace($value)) { return $null }
    # Newer azd may print a "key not found" error to stdout for missing keys.
    if ($value -match 'ERROR:' -or $value -match 'not found in environment') { return $null }
    return $value.Trim()
}

function Get-DeploymentOutputs {
    param([string]$Rg)
    $deploymentName = az group show --name $Rg --query 'tags.DeploymentName' -o tsv 2>$null
    if ([string]::IsNullOrWhiteSpace($deploymentName)) {
        # Fall back to most recent deployment
        $deploymentName = az deployment group list --resource-group $Rg --query '[0].name' -o tsv 2>$null
    }
    if ([string]::IsNullOrWhiteSpace($deploymentName)) { return $null }
    $json = az deployment group show --resource-group $Rg --name $deploymentName --query 'properties.outputs' -o json 2>$null
    if ([string]::IsNullOrWhiteSpace($json)) { return $null }
    return ($json | ConvertFrom-Json)
}

function Get-OutputValue {
    param($Outputs, [string[]]$Keys)
    if ($null -eq $Outputs) { return $null }
    foreach ($k in $Keys) {
        $prop = $Outputs.PSObject.Properties[$k]
        if ($prop -and -not [string]::IsNullOrWhiteSpace($prop.Value.value)) {
            return $prop.Value.value.ToString().Trim()
        }
    }
    return $null
}

function Invoke-AcrBuild {
    param(
        [string]$Registry,
        [string]$Image,
        [string]$Tag,
        [string]$Context
    )
    Write-Host "Building $Registry/$Image`:$Tag from $Context" -ForegroundColor Cyan

    if ($ShowLogs) {
        az acr build `
            --registry $Registry `
            --image "$Image`:$Tag" `
            --image "$Image`:latest" `
            --only-show-errors `
            $Context
        if ($LASTEXITCODE -ne 0) { throw "az acr build failed for image $Image" }
        return
    }

    # Quiet mode: no log stream, no CLI warnings, no JSON dump. Only run ID + result.
    Write-Host "  (streaming logs suppressed; pass -ShowLogs to see full output)" -ForegroundColor DarkGray
    $jsonRaw = az acr build `
        --registry $Registry `
        --image "$Image`:$Tag" `
        --image "$Image`:latest" `
        --no-logs `
        --only-show-errors `
        -o json `
        $Context 2>&1
    $exit = $LASTEXITCODE

    $runObj = $null
    try { $runObj = ($jsonRaw | Out-String) | ConvertFrom-Json -ErrorAction Stop } catch { }

    if ($exit -ne 0) {
        # Success path emits JSON with .runId; failure path emits only
        # `ERROR: The run with ID 'caXX' finished with unsuccessful status ...`
        $runId = if ($runObj) { $runObj.runId } else { $null }
        if (-not $runId) {
            $text = ($jsonRaw | Out-String)
            $m = [regex]::Match($text, "run with ID '([^']+)'")
            if ($m.Success) { $runId = $m.Groups[1].Value }
        }

        if ($runId) {
            Write-Host ""
            Write-Host "Build failed (runId: $runId). Fetching logs..." -ForegroundColor Red
            az acr task logs --registry $Registry --run-id $runId --only-show-errors
        } else {
            $jsonRaw | ForEach-Object { Write-Host $_ }
        }
        throw "az acr build failed for image $Image"
    }

    if ($runObj) {
        Write-Host "  Succeeded (runId: $($runObj.runId))" -ForegroundColor Green
    }
}

function Set-WebAppContainer {
    param(
        [string]$Rg,
        [string]$AppName,
        [string]$AcrLoginServer,
        [string]$Image,
        [string]$Tag
    )
    $fullImage = "$AcrLoginServer/$Image`:$Tag"
    Write-Host "Updating web app '$AppName' -> $fullImage" -ForegroundColor Cyan
    az webapp config container set `
        --name $AppName `
        --resource-group $Rg `
        --container-image-name $fullImage `
        --only-show-errors | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to update container config for $AppName" }

    Write-Host "Restarting '$AppName'..." -ForegroundColor Cyan
    az webapp restart --name $AppName --resource-group $Rg --only-show-errors | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to restart $AppName" }
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
if (-not (Test-CommandAvailable 'az')) {
    throw "Azure CLI ('az') is required but was not found on PATH."
}

# ---------------------------------------------------------------------------
# Resolve inputs
# ---------------------------------------------------------------------------
if (-not $ResourceGroup)   { $ResourceGroup   = Get-AzdEnvValue 'AZURE_RESOURCE_GROUP' }
if (-not $AcrName)         { $AcrName         = Get-AzdEnvValue 'AZURE_CONTAINER_REGISTRY_NAME' }
if (-not $AcrName)         { $AcrName         = Get-AzdEnvValue 'ACR_NAME' }
if (-not $BackendAppName)  { $BackendAppName  = Get-AzdEnvValue 'API_APP_NAME' }
$solutionSuffix = Get-AzdEnvValue 'SOLUTION_NAME'
if (-not $FrontendAppName -and $solutionSuffix) { $FrontendAppName = "app-$solutionSuffix" }
if (-not $ImageTag)        { $ImageTag        = Get-AzdEnvValue 'AZURE_ENV_IMAGETAG' }

# Fall back to deployment outputs for anything still missing
$needDeployment = -not ($ResourceGroup -and $AcrName -and $BackendAppName -and $FrontendAppName)
if ($needDeployment) {
    if (-not $ResourceGroup) {
        throw "ResourceGroup is required. Pass -ResourceGroup or run inside an azd environment."
    }
    Write-Host "Fetching deployment outputs from resource group '$ResourceGroup'..." -ForegroundColor DarkGray
    $outputs = Get-DeploymentOutputs -Rg $ResourceGroup
    if (-not $AcrName)        { $AcrName        = Get-OutputValue $outputs @('AZURE_CONTAINER_REGISTRY_NAME','azureContainerRegistryName','ACR_NAME','acrName') }
    if (-not $BackendAppName) { $BackendAppName = Get-OutputValue $outputs @('API_APP_NAME','apiAppName') }
    if (-not $solutionSuffix) { $solutionSuffix = Get-OutputValue $outputs @('SOLUTION_NAME','solutionName') }
    if (-not $FrontendAppName -and $solutionSuffix) { $FrontendAppName = "app-$solutionSuffix" }
}

if (-not $ImageTag) {
    $ImageTag = (Get-Date -Format 'yyyyMMddHHmmss')
}

if (-not $ResourceGroup)                        { throw "Missing ResourceGroup." }
if (-not $AcrName)                              { throw "Missing AcrName." }
if (-not $SkipBackend  -and -not $BackendAppName)  { throw "Missing BackendAppName." }
if (-not $SkipFrontend -and -not $FrontendAppName) { throw "Missing FrontendAppName." }

$acrLoginServer = "$AcrName.azurecr.io"

Write-Host ""
Write-Host "Configuration" -ForegroundColor Green
Write-Host "  Resource group : $ResourceGroup"
Write-Host "  ACR            : $acrLoginServer"
Write-Host "  Backend app    : $BackendAppName"
Write-Host "  Frontend app   : $FrontendAppName"
Write-Host "  Image tag      : $ImageTag"
Write-Host ""

# ---------------------------------------------------------------------------
# Build & deploy
# ---------------------------------------------------------------------------
if (-not $SkipBackend) {
    if (-not (Test-Path (Join-Path $backendCtx 'Dockerfile'))) {
        throw "Backend Dockerfile not found at $backendCtx/Dockerfile"
    }
    Invoke-AcrBuild -Registry $AcrName -Image $BackendImage -Tag $ImageTag -Context $backendCtx
    Set-WebAppContainer -Rg $ResourceGroup -AppName $BackendAppName -AcrLoginServer $acrLoginServer -Image $BackendImage -Tag $ImageTag
} else {
    Write-Host "Skipping backend (SkipBackend)." -ForegroundColor Yellow
}

if (-not $SkipFrontend) {
    if (-not (Test-Path (Join-Path $frontendCtx 'Dockerfile'))) {
        throw "Frontend Dockerfile not found at $frontendCtx/Dockerfile"
    }
    Invoke-AcrBuild -Registry $AcrName -Image $FrontendImage -Tag $ImageTag -Context $frontendCtx
    Set-WebAppContainer -Rg $ResourceGroup -AppName $FrontendAppName -AcrLoginServer $acrLoginServer -Image $FrontendImage -Tag $ImageTag
} else {
    Write-Host "Skipping frontend (SkipFrontend)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done. Images published with tag '$ImageTag'." -ForegroundColor Green
