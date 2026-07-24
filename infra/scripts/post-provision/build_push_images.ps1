#!/usr/bin/env pwsh
#Requires -Version 7.0

<#
.SYNOPSIS
    Builds chat-app and scenario-app container images inside Azure Container
    Registry using `az acr build`, then updates the four App Services to run
    those images.

.DESCRIPTION
    Uses `az acr build` so image build/push happens in ACR (no local Docker
    required). Values are read from the current `azd` environment when
    possible, otherwise from the last successful ARM deployment in the
    resource group. All parameters can be overridden on the command line.

    Four images are built:
      chat-backend      - repo-root context with chat-app/backend/Dockerfile
      chat-frontend     - chat-app/frontend/ context
      scenario-backend  - scenario-app/backend/ context
      scenario-frontend - repo-root context with scenario-app/frontend/Dockerfile

.PARAMETER ResourceGroup
    Azure resource group that contains ACR and the App Services.
.PARAMETER AcrName
    Azure Container Registry name (without the .azurecr.io suffix).
.PARAMETER ChatBackendAppName
    Chat backend App Service name.
.PARAMETER ChatFrontendAppName
    Chat frontend App Service name.
.PARAMETER ScenarioBackendAppName
    Scenario backend App Service name.
.PARAMETER ScenarioFrontendAppName
    Scenario frontend App Service name.
.PARAMETER ImageTag
    Tag to apply to all images. Defaults to a UTC timestamp.
.PARAMETER ChatBackendImage
    Chat backend image repository name. Defaults to "chat-backend".
.PARAMETER ChatFrontendImage
    Chat frontend image repository name. Defaults to "chat-frontend".
.PARAMETER ScenarioBackendImage
    Scenario backend image repository name. Defaults to "scenario-backend".
.PARAMETER ScenarioFrontendImage
    Scenario frontend image repository name. Defaults to "scenario-frontend".
.PARAMETER SkipChatBackend
    Skip building/updating the chat backend.
.PARAMETER SkipChatFrontend
    Skip building/updating the chat frontend.
.PARAMETER SkipScenarioBackend
    Skip building/updating the scenario backend.
.PARAMETER SkipScenarioFrontend
    Skip building/updating the scenario frontend.

.EXAMPLE
    ./infra/scripts/post-provision/build_push_images.ps1

.EXAMPLE
    ./infra/scripts/post-provision/build_push_images.ps1 -ResourceGroup rg-ccsa -ImageTag v1.2.3
#>

param(
    [string]$ResourceGroup,
    [string]$AcrName,
    [string]$ChatBackendAppName,
    [string]$ChatFrontendAppName,
    [string]$ScenarioBackendAppName,
    [string]$ScenarioFrontendAppName,
    [string]$ImageTag,
    [string]$ChatBackendImage = 'chat-backend',
    [string]$ChatFrontendImage = 'chat-frontend',
    [string]$ScenarioBackendImage = 'scenario-backend',
    [string]$ScenarioFrontendImage = 'scenario-frontend',
    [switch]$SkipChatBackend,
    [switch]$SkipChatFrontend,
    [switch]$SkipScenarioBackend,
    [switch]$SkipScenarioFrontend,
    [switch]$ShowLogs
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot   = (Resolve-Path (Join-Path $scriptDir '..' '..' '..')).Path

# Build contexts and Dockerfiles
$chatBackendCtx             = $repoRoot
$chatBackendDockerfile      = Join-Path $repoRoot 'chat-app' 'backend' 'Dockerfile'
$chatFrontendCtx            = Join-Path $repoRoot 'chat-app' 'frontend'
$scenarioBackendCtx         = Join-Path $repoRoot 'scenario-app' 'backend'
$scenarioFrontendCtx        = $repoRoot
$scenarioFrontendDockerfile = Join-Path $repoRoot 'scenario-app' 'frontend' 'Dockerfile'

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
        [string]$Context,
        [string]$DockerfilePath = ''
    )
    Write-Host "Building $Registry/$Image`:$Tag from $Context" -ForegroundColor Cyan

    $fileArgs = if ($DockerfilePath) { @('--file', $DockerfilePath) } else { @() }

    if ($ShowLogs) {
        az acr build `
            --registry $Registry `
            --image "$Image`:$Tag" `
            --image "$Image`:latest" `
            --only-show-errors `
            @fileArgs `
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
        @fileArgs `
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
# ACR public-access helpers
# ---------------------------------------------------------------------------
$script:OriginalAcrPublicAccess  = $null
$script:OriginalAcrDefaultAction = $null
$script:AcrAccessModified        = $false

function Enable-AcrPublicAccess {
    param([string]$Name)
    Write-Host "Checking ACR public network access for '$Name'..." -ForegroundColor DarkGray

    $rawPublicAccess = az acr show --name $Name --query "publicNetworkAccess" -o tsv 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($rawPublicAccess)) {
        throw "Failed to read ACR public network access for '$Name' (exit $LASTEXITCODE). Ensure the registry exists and you have sufficient permissions."
    }
    $script:OriginalAcrPublicAccess = $rawPublicAccess.Trim()

    $rawDefaultAction = az acr show --name $Name --query "networkRuleSet.defaultAction" -o tsv 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to read ACR network rule set for '$Name' (exit $LASTEXITCODE)."
    }
    $script:OriginalAcrDefaultAction = if ([string]::IsNullOrWhiteSpace($rawDefaultAction)) { '' } else { $rawDefaultAction.Trim() }
    Write-Host "  Current: publicNetworkAccess=$($script:OriginalAcrPublicAccess)  defaultAction=$($script:OriginalAcrDefaultAction)" -ForegroundColor DarkGray

    if ($script:OriginalAcrPublicAccess -ne 'Enabled') {
        Write-Host "  Enabling ACR public network access..." -ForegroundColor Cyan
        az acr update --name $Name --public-network-enabled true --only-show-errors | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Failed to enable public network access for ACR '$Name'." }
        $script:AcrAccessModified = $true
    }

    if ($script:OriginalAcrDefaultAction -eq 'Deny') {
        Write-Host "  Setting ACR network default action to Allow..." -ForegroundColor Cyan
        az acr update --name $Name --default-action Allow --only-show-errors | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Failed to set default network action for ACR '$Name'." }
        $script:AcrAccessModified = $true
    }

    if ($script:AcrAccessModified) {
        Write-Host "  ACR network access updated. Waiting 15 s for changes to propagate..." -ForegroundColor DarkGray
        Start-Sleep -Seconds 15
    } else {
        Write-Host "  ACR public access already open - no changes needed." -ForegroundColor DarkGray
    }
    Write-Host ""
}

function Restore-AcrAccess {
    param([string]$Name)
    Write-Host ""
    Write-Host "=== Restoring original ACR network settings ===" -ForegroundColor DarkGray
    if (-not $script:AcrAccessModified) {
        Write-Host "  ACR unchanged - no restoration needed." -ForegroundColor DarkGray
        return
    }
    Write-Host "  Restoring ACR '$Name' to original settings..." -ForegroundColor Cyan
    $updateArgs = @('acr', 'update', '--name', $Name, '--only-show-errors')
    if ($script:OriginalAcrPublicAccess -ne 'Enabled') {
        $updateArgs += @('--public-network-enabled', 'false')
    }
    if ($script:OriginalAcrDefaultAction -eq 'Deny') {
        $updateArgs += @('--default-action', 'Deny')
    }
    az @updateArgs | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ACR settings restored (publicNetworkAccess=$($script:OriginalAcrPublicAccess), defaultAction=$($script:OriginalAcrDefaultAction))." -ForegroundColor Green
    } else {
        Write-Host "  WARNING: Failed to restore ACR network settings for '$Name'. Please restore manually." -ForegroundColor Yellow
        Write-Host "    Expected: publicNetworkAccess=$($script:OriginalAcrPublicAccess)  defaultAction=$($script:OriginalAcrDefaultAction)" -ForegroundColor Yellow
    }
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
if (-not (Test-CommandAvailable 'az')) {
    throw "Azure CLI ('az') is required but was not found on PATH."
}

az account show --only-show-errors 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "You are not signed in to the Azure CLI. Run 'az login' (or 'az login --use-device-code' in restricted environments) and try again."
}

# ---------------------------------------------------------------------------
# Resolve inputs
# ---------------------------------------------------------------------------
if (-not $ResourceGroup)           { $ResourceGroup           = Get-AzdEnvValue 'AZURE_RESOURCE_GROUP' }
if (-not $AcrName)                 { $AcrName                 = Get-AzdEnvValue 'AZURE_CONTAINER_REGISTRY_NAME' }
if (-not $AcrName)                 { $AcrName                 = Get-AzdEnvValue 'ACR_NAME' }
if (-not $ChatBackendAppName)      { $ChatBackendAppName      = Get-AzdEnvValue 'CHAT_API_APP_NAME' }
if (-not $ChatFrontendAppName)     { $ChatFrontendAppName     = Get-AzdEnvValue 'CHAT_WEB_APP_NAME' }
if (-not $ScenarioBackendAppName)  { $ScenarioBackendAppName  = Get-AzdEnvValue 'SCENARIO_API_APP_NAME' }
if (-not $ScenarioFrontendAppName) { $ScenarioFrontendAppName = Get-AzdEnvValue 'SCENARIO_WEB_APP_NAME' }
if (-not $ImageTag)                { $ImageTag                = Get-AzdEnvValue 'AZURE_ENV_IMAGETAG' }

# Fall back to deployment outputs for anything still missing
$needDeployment = -not ($ResourceGroup -and $AcrName -and $ChatBackendAppName -and $ChatFrontendAppName -and $ScenarioBackendAppName -and $ScenarioFrontendAppName)
if ($needDeployment) {
    if (-not $ResourceGroup) {
        throw "ResourceGroup is required. Pass -ResourceGroup or run inside an azd environment."
    }
    Write-Host "Fetching deployment outputs from resource group '$ResourceGroup'..." -ForegroundColor DarkGray
    $outputs = Get-DeploymentOutputs -Rg $ResourceGroup
    if (-not $AcrName)                 { $AcrName                 = Get-OutputValue $outputs @('AZURE_CONTAINER_REGISTRY_NAME','azureContainerRegistryName','ACR_NAME','acrName') }
    if (-not $ChatBackendAppName)      { $ChatBackendAppName      = Get-OutputValue $outputs @('CHAT_API_APP_NAME','chatApiAppName') }
    if (-not $ChatFrontendAppName)     { $ChatFrontendAppName     = Get-OutputValue $outputs @('CHAT_WEB_APP_NAME','chatWebAppName') }
    if (-not $ScenarioBackendAppName)  { $ScenarioBackendAppName  = Get-OutputValue $outputs @('SCENARIO_API_APP_NAME','scenarioApiAppName') }
    if (-not $ScenarioFrontendAppName) { $ScenarioFrontendAppName = Get-OutputValue $outputs @('SCENARIO_WEB_APP_NAME','scenarioWebAppName') }
}

if (-not $ImageTag) {
    $ImageTag = (Get-Date -Format 'yyyyMMddHHmmss')
}

if (-not $ResourceGroup)                                            { throw "Missing ResourceGroup." }
if (-not $AcrName)                                                  { throw "Missing AcrName." }
if (-not $SkipChatBackend      -and -not $ChatBackendAppName)       { throw "Missing ChatBackendAppName." }
if (-not $SkipChatFrontend     -and -not $ChatFrontendAppName)      { throw "Missing ChatFrontendAppName." }
if (-not $SkipScenarioBackend  -and -not $ScenarioBackendAppName)   { throw "Missing ScenarioBackendAppName." }
if (-not $SkipScenarioFrontend -and -not $ScenarioFrontendAppName)  { throw "Missing ScenarioFrontendAppName." }

$acrLoginServer = "$AcrName.azurecr.io"

Write-Host ""
Write-Host "Configuration" -ForegroundColor Green
Write-Host "  Resource group         : $ResourceGroup"
Write-Host "  ACR                    : $acrLoginServer"
Write-Host "  Chat backend app       : $ChatBackendAppName"
Write-Host "  Chat frontend app      : $ChatFrontendAppName"
Write-Host "  Scenario backend app   : $ScenarioBackendAppName"
Write-Host "  Scenario frontend app  : $ScenarioFrontendAppName"
Write-Host "  Image tag              : $ImageTag"
Write-Host ""

# ---------------------------------------------------------------------------
# Build & deploy
# ---------------------------------------------------------------------------
try {
    Enable-AcrPublicAccess -Name $AcrName

    if (-not $SkipChatBackend) {
        if (-not (Test-Path $chatBackendDockerfile)) {
            throw "Chat backend Dockerfile not found at $chatBackendDockerfile"
        }
        Invoke-AcrBuild -Registry $AcrName -Image $ChatBackendImage -Tag $ImageTag -Context $chatBackendCtx -DockerfilePath $chatBackendDockerfile
        Set-WebAppContainer -Rg $ResourceGroup -AppName $ChatBackendAppName -AcrLoginServer $acrLoginServer -Image $ChatBackendImage -Tag $ImageTag
    } else {
        Write-Host "Skipping chat backend (SkipChatBackend)." -ForegroundColor Yellow
    }

    Write-Host ""

    if (-not $SkipChatFrontend) {
        if (-not (Test-Path (Join-Path $chatFrontendCtx 'Dockerfile'))) {
            throw "Chat frontend Dockerfile not found at $chatFrontendCtx/Dockerfile"
        }
        Invoke-AcrBuild -Registry $AcrName -Image $ChatFrontendImage -Tag $ImageTag -Context $chatFrontendCtx
        Set-WebAppContainer -Rg $ResourceGroup -AppName $ChatFrontendAppName -AcrLoginServer $acrLoginServer -Image $ChatFrontendImage -Tag $ImageTag
    } else {
        Write-Host "Skipping chat frontend (SkipChatFrontend)." -ForegroundColor Yellow
    }

    Write-Host ""

    if (-not $SkipScenarioBackend) {
        if (-not (Test-Path (Join-Path $scenarioBackendCtx 'Dockerfile'))) {
            throw "Scenario backend Dockerfile not found at $scenarioBackendCtx/Dockerfile"
        }
        Invoke-AcrBuild -Registry $AcrName -Image $ScenarioBackendImage -Tag $ImageTag -Context $scenarioBackendCtx
        Set-WebAppContainer -Rg $ResourceGroup -AppName $ScenarioBackendAppName -AcrLoginServer $acrLoginServer -Image $ScenarioBackendImage -Tag $ImageTag
    } else {
        Write-Host "Skipping scenario backend (SkipScenarioBackend)." -ForegroundColor Yellow
    }

    Write-Host ""

    if (-not $SkipScenarioFrontend) {
        if (-not (Test-Path $scenarioFrontendDockerfile)) {
            throw "Scenario frontend Dockerfile not found at $scenarioFrontendDockerfile"
        }
        Invoke-AcrBuild -Registry $AcrName -Image $ScenarioFrontendImage -Tag $ImageTag -Context $scenarioFrontendCtx -DockerfilePath $scenarioFrontendDockerfile
        Set-WebAppContainer -Rg $ResourceGroup -AppName $ScenarioFrontendAppName -AcrLoginServer $acrLoginServer -Image $ScenarioFrontendImage -Tag $ImageTag
    } else {
        Write-Host "Skipping scenario frontend (SkipScenarioFrontend)." -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "`nDone. Images published with tag '$ImageTag'.`n" -ForegroundColor Green
}
finally {
    Restore-AcrAccess -Name $AcrName
}
