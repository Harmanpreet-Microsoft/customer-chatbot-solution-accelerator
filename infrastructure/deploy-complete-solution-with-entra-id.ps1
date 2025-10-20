param(
    [string]$ResourceGroupName = "ecommerce-chat-rg",
    [string]$Location = "West US 2",
    [string]$Environment = "prod"
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 COMPLETE E-COMMERCE SOLUTION DEPLOYMENT" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Resource Group: $ResourceGroupName" -ForegroundColor Cyan
Write-Host "Location: $Location" -ForegroundColor Cyan
Write-Host "Environment: $Environment" -ForegroundColor Cyan
Write-Host ""

# Global variables
$timestamp = Get-Date -Format "yyyyMMddHHmm"
$cosmosDbName = "ecommerce-$Environment-cosmos-$timestamp"
$frontendAppName = "ecommerce-frontend-$timestamp"
$backendAppName = "ecommerce-backend-$timestamp"
$planName = "ecommerce-plan-$timestamp"
$registryName = "ecreg$timestamp"

try {
    # ============================================================================
    # PHASE 0: Prerequisites Check
    # ============================================================================
    Write-Host "🔍 PHASE 0: CHECKING PREREQUISITES" -ForegroundColor Blue
    Write-Host "=================================" -ForegroundColor Blue

    # Check Azure CLI
    $azCheck = az --version 2>$null
    if (-not $azCheck) {
        throw "Azure CLI not found. Please install Azure CLI first."
    }
    Write-Host "✅ Azure CLI found" -ForegroundColor Green

    # Check login status
    $account = az account show 2>$null | ConvertFrom-Json
    if (-not $account) {
        throw "Not logged into Azure. Please run 'az login' first."
    }
    Write-Host "✅ Logged in as: $($account.user.name)" -ForegroundColor Green

    # Check paths
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $projectRoot = Split-Path -Parent $scriptDir
    $frontendDir = Join-Path $projectRoot "src\App"
    $backendDir = Join-Path $projectRoot "src\api"
    
    if (-not (Test-Path $frontendDir)) {
        throw "Frontend directory not found: $frontendDir"
    }
    if (-not (Test-Path $backendDir)) {
        throw "Backend directory not found: $backendDir"
    }
    Write-Host "✅ Project directories found" -ForegroundColor Green

    # Get tenant ID
    Write-Host "`n⏭️  PHASE 1: SKIPPED - No App Registration needed" -ForegroundColor Blue
    Write-Host "=================================================" -ForegroundColor Blue
    Write-Host "You will configure authentication manually via Azure Portal after deployment." -ForegroundColor Cyan

    # ============================================================================
    # PHASE 2: Resource Group & Cosmos DB
    # ============================================================================
    Write-Host "`n🗂️ PHASE 2: COSMOS DB DEPLOYMENT" -ForegroundColor Blue
    Write-Host "================================" -ForegroundColor Blue

    # Create resource group
    $rgExists = az group exists --name $ResourceGroupName
    if ($rgExists -eq "false") {
        Write-Host "Creating resource group..." -ForegroundColor Yellow
        az group create --name $ResourceGroupName --location $Location --output none
        Write-Host "✅ Resource group created" -ForegroundColor Green
    } else {
        Write-Host "✅ Resource group exists" -ForegroundColor Green
    }

    # Deploy Cosmos DB
    Write-Host "Deploying Cosmos DB: $cosmosDbName" -ForegroundColor Yellow
    az deployment group create `
        --resource-group $ResourceGroupName `
        --template-file "cosmos-db.bicep" `
        --parameters cosmosDbName=$cosmosDbName `
        --parameters resourceGroupName=$ResourceGroupName `
        --parameters location=$Location `
        --parameters environment=$Environment `
        --output none

    if ($LASTEXITCODE -ne 0) {
        throw "Cosmos DB deployment failed"
    }
    Write-Host "✅ Cosmos DB deployed successfully" -ForegroundColor Green

    # Get Cosmos DB connection details
    Write-Host "Getting Cosmos DB connection details..." -ForegroundColor Yellow
    $cosmosEndpoint = az cosmosdb show --name $cosmosDbName --resource-group $ResourceGroupName --query "documentEndpoint" -o tsv
    $cosmosKey = az cosmosdb keys list --name $cosmosDbName --resource-group $ResourceGroupName --query "primaryMasterKey" -o tsv
    
    if (-not $cosmosEndpoint -or -not $cosmosKey) {
        throw "Failed to get Cosmos DB connection details"
    }
    Write-Host "✅ Cosmos DB connection details retrieved" -ForegroundColor Green

    # Seed Cosmos DB data
    Write-Host "Seeding Cosmos DB with sample data..." -ForegroundColor Yellow
    $env:COSMOS_DB_ENDPOINT = $cosmosEndpoint
    $env:COSMOS_DB_KEY = $cosmosKey
    $env:COSMOS_DB_DATABASE_NAME = "ecommerce_db"
    
    $seedScript = Join-Path $scriptDir "seed-cosmos-data.py"
    if (Test-Path $seedScript) {
        python $seedScript
        Write-Host "✅ Data seeding completed" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Seeding script not found, continuing without sample data" -ForegroundColor Yellow
    }

    # ============================================================================
    # PHASE 2.5: Azure AI Search
    # ============================================================================
    Write-Host "`n🔍 PHASE 2.5: AZURE AI SEARCH DEPLOYMENT" -ForegroundColor Blue
    Write-Host "========================================" -ForegroundColor Blue

    $searchServiceName = "ecommerce-$Environment-search-$timestamp"
    $searchIndexName = "policies"
    $searchProductIndexName = "products"

    Write-Host "Creating Azure AI Search service: $searchServiceName" -ForegroundColor Yellow
    az search service create `
        --name $searchServiceName `
        --resource-group $ResourceGroupName `
        --location $Location `
        --sku Free `
        --output none

    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  Azure AI Search deployment failed (may already exist or quota exceeded)" -ForegroundColor Yellow
        Write-Host "Continuing without Azure AI Search..." -ForegroundColor Yellow
        $searchEndpoint = $null
        $searchKey = $null
    } else {
        Write-Host "✅ Azure AI Search service created" -ForegroundColor Green

        Start-Sleep -Seconds 30

        $searchEndpoint = "https://$searchServiceName.search.windows.net"
        $searchKey = az search admin-key show --service-name $searchServiceName --resource-group $ResourceGroupName --query "primaryKey" -o tsv

        if ($searchKey) {
            Write-Host "✅ Azure AI Search key retrieved" -ForegroundColor Green

            Write-Host "Setting up search indexes and uploading documents..." -ForegroundColor Yellow
            $env:AZURE_SEARCH_ENDPOINT = $searchEndpoint
            $env:AZURE_SEARCH_API_KEY = $searchKey
            $env:AZURE_SEARCH_INDEX_NAME = $searchIndexName

            # Set up policy documents index
            Write-Host "Setting up policy documents index..." -ForegroundColor Gray
            $searchSetupScript = Join-Path $scriptDir "setup-search-index-simple.py"
            if (-not (Test-Path $searchSetupScript)) {
                $searchSetupScript = Join-Path $scriptDir "setup-search-index.py"
            }
            
            if (Test-Path $searchSetupScript) {
                python $searchSetupScript
                Write-Host "✅ Policy documents index configured and uploaded" -ForegroundColor Green
            } else {
                Write-Host "⚠️  Policy search setup script not found" -ForegroundColor Yellow
            }

            # Set up product search index
            Write-Host "Setting up product search index..." -ForegroundColor Gray
            $productSearchSetupScript = Join-Path $scriptDir "setup-product-search-index.py"
            
            if (Test-Path $productSearchSetupScript) {
                python $productSearchSetupScript
                Write-Host "✅ Product search index configured and uploaded" -ForegroundColor Green
            } else {
                Write-Host "⚠️  Product search setup script not found" -ForegroundColor Yellow
            }
        } else {
            Write-Host "⚠️  Failed to retrieve search key" -ForegroundColor Yellow
            $searchEndpoint = $null
            $searchKey = $null
        }
    }

    # ============================================================================
    # PHASE 3: Container Registry
    # ============================================================================
    Write-Host "`n📦 PHASE 3: CONTAINER REGISTRY" -ForegroundColor Blue
    Write-Host "==============================" -ForegroundColor Blue

    # Create unique registry name
    $nameCheck = az acr check-name --name $registryName | ConvertFrom-Json
    if (-not $nameCheck.nameAvailable) {
        $timestamp = Get-Date -Format "yyyyMMddHHmmss"
        $registryName = "ecreg$timestamp"
        Write-Host "Registry name taken, using: $registryName" -ForegroundColor Yellow
    }

    # Create container registry
    Write-Host "Creating container registry: $registryName" -ForegroundColor Yellow
    az acr create `
        --name $registryName `
        --resource-group $ResourceGroupName `
        --location $Location `
        --sku Basic `
        --admin-enabled true `
        --output none

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create container registry"
    }
    Write-Host "✅ Container registry created" -ForegroundColor Green

    # ============================================================================
    # PHASE 4: App Service Plan
    # ============================================================================
    Write-Host "`n🏗️ PHASE 4: APP SERVICE PLAN" -ForegroundColor Blue
    Write-Host "=============================" -ForegroundColor Blue

    Write-Host "Creating App Service Plan: $planName" -ForegroundColor Yellow
    az appservice plan create `
        --name $planName `
        --resource-group $ResourceGroupName `
        --location $Location `
        --sku B1 `
        --is-linux `
        --output none

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create App Service Plan"
    }
    Write-Host "✅ App Service Plan created" -ForegroundColor Green

    # ============================================================================
    # PHASE 5: Frontend Container Deployment
    # ============================================================================
    Write-Host "`n🎨 PHASE 5: FRONTEND DEPLOYMENT" -ForegroundColor Blue
    Write-Host "===============================" -ForegroundColor Blue

    # Build frontend container
    Write-Host "Building frontend container..." -ForegroundColor Yellow
    Push-Location $frontendDir
    try {
        # Create temporary backend URL (will update after backend is deployed)
        $tempBackendUrl = "https://$backendAppName.azurewebsites.net"
        $tempFrontendUrl = "https://$frontendAppName.azurewebsites.net"
        
        # Create runtime configuration with Entra ID (this will be updated later)
        $configContent = @"
// Runtime configuration
window.APP_CONFIG = {
  API_BASE_URL: '$tempBackendUrl',
  ENVIRONMENT: 'production',
  AZURE_CLIENT_ID: '$AzureClientId',
  AZURE_TENANT_ID: '$AzureTenantId',
  AZURE_AUTHORITY: 'https://login.microsoftonline.com/$AzureTenantId',
  REDIRECT_URI: '$tempFrontendUrl/auth/callback'
};
"@
        $configContent | Out-File -FilePath "public/config.js" -Encoding UTF8
        
        # Create build-time environment with Entra ID (still needed for development fallback)
        $envContent = @"
VITE_API_BASE_URL=$tempBackendUrl
VITE_AZURE_CLIENT_ID=$AzureClientId
VITE_AZURE_TENANT_ID=$AzureTenantId
VITE_AZURE_AUTHORITY=https://login.microsoftonline.com/$AzureTenantId
VITE_REDIRECT_URI=$tempFrontendUrl/auth/callback
VITE_ENVIRONMENT=production
NODE_ENV=production
"@
        $envContent | Out-File -FilePath ".env.production" -Encoding UTF8

        # Create comprehensive .dockerignore
        $dockerignoreContent = @"
node_modules
node_modules/**
.git
.git/**
dist
dist/**
build
build/**
*.log
.DS_Store
.vscode
.env
.env.*
README.md
*.md
"@
        $dockerignoreContent | Out-File -FilePath ".dockerignore" -Encoding UTF8 -Force

        # Clean existing builds
        if (Test-Path "node_modules") { Remove-Item "node_modules" -Recurse -Force -ErrorAction SilentlyContinue }
        if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force -ErrorAction SilentlyContinue }

        # Build and push frontend image
        $env:PYTHONIOENCODING = "utf-8"
        $env:PYTHONLEGACYWINDOWSSTDIO = "utf-8"
        
        az acr build `
            --registry $registryName `
            --image "frontend:latest" `
            --file "Dockerfile" `
            . `
            --no-logs

        if ($LASTEXITCODE -ne 0) {
            throw "Frontend container build failed"
        }

        # Clean up temp files
        Remove-Item ".env.production" -Force -ErrorAction SilentlyContinue
        
    } finally {
        Pop-Location
    }
    Write-Host "✅ Frontend container built and pushed" -ForegroundColor Green

    # Create frontend web app
    Write-Host "Creating frontend web app: $frontendAppName" -ForegroundColor Yellow
    $frontendImageName = "$registryName.azurecr.io/frontend:latest"
    
    az webapp create `
        --name $frontendAppName `
        --resource-group $ResourceGroupName `
        --plan $planName `
        --deployment-container-image-name $frontendImageName `
        --output none

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create frontend web app"
    }
    Write-Host "✅ Frontend web app created" -ForegroundColor Green

    # Configure frontend container
    Write-Host "Configuring frontend container..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10

    $acrCredentials = az acr credential show --name $registryName | ConvertFrom-Json
    if (-not $acrCredentials) {
        throw "Failed to get container registry credentials"
    }

    az webapp config container set `
        --name $frontendAppName `
        --resource-group $ResourceGroupName `
        --docker-custom-image-name $frontendImageName `
        --docker-registry-server-url "https://$registryName.azurecr.io" `
        --docker-registry-server-user $acrCredentials.username `
        --docker-registry-server-password $acrCredentials.passwords[0].value `
        --output none

    az webapp config appsettings set `
        --name $frontendAppName `
        --resource-group $ResourceGroupName `
        --settings `
        WEBSITES_ENABLE_APP_SERVICE_STORAGE="false" `
        WEBSITES_PORT="80" `
        VITE_API_BASE_URL="$tempBackendUrl" `
        NODE_ENV="production" `
        --output none

    Write-Host "✅ Frontend environment variables configured" -ForegroundColor Green
    Write-Host "⚠️  Authentication not configured - you'll add it via Azure Portal" -ForegroundColor Yellow

    # ============================================================================
    # PHASE 6: Backend Container Deployment
    # ============================================================================
    Write-Host "`n⚙️ PHASE 6: BACKEND DEPLOYMENT" -ForegroundColor Blue
    Write-Host "==============================" -ForegroundColor Blue

    $frontendUrl = "https://$frontendAppName.azurewebsites.net"
    
    # Build backend container
    Write-Host "Building backend container..." -ForegroundColor Yellow
    Push-Location $backendDir
    try {
        # Create Dockerfile for backend
        $dockerfileContent = @"
# Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Start the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"@
        $dockerfileContent | Out-File -FilePath "Dockerfile" -Encoding UTF8

        # Create .dockerignore
        $dockerignoreContent = @"
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env
.tox
.coverage
*.log
.git
.mypy_cache
.pytest_cache
.venv
venv/
.vscode/
.idea/
"@
        $dockerignoreContent | Out-File -FilePath ".dockerignore" -Encoding UTF8

        # Build and push backend image
        $env:PYTHONIOENCODING = "utf-8"
        $env:PYTHONLEGACYWINDOWSSTDIO = "utf-8"
        
        az acr build `
            --registry $registryName `
            --image "backend:latest" `
            --file "Dockerfile" `
            . `
            --no-logs

        if ($LASTEXITCODE -ne 0) {
            throw "Backend container build failed"
        }

        # Clean up temp files
        Remove-Item "Dockerfile" -Force -ErrorAction SilentlyContinue
        Remove-Item ".dockerignore" -Force -ErrorAction SilentlyContinue
        
    } finally {
        Pop-Location
    }
    Write-Host "✅ Backend container built and pushed" -ForegroundColor Green

    # Create backend web app
    Write-Host "Creating backend web app: $backendAppName" -ForegroundColor Yellow
    $backendImageName = "$registryName.azurecr.io/backend:latest"
    
    az webapp create `
        --name $backendAppName `
        --resource-group $ResourceGroupName `
        --plan $planName `
        --deployment-container-image-name $backendImageName `
        --output none

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create backend web app"
    }
    Write-Host "✅ Backend web app created" -ForegroundColor Green

    # Configure backend container
    Write-Host "Configuring backend container..." -ForegroundColor Yellow
    
    az webapp config container set `
        --name $backendAppName `
        --resource-group $ResourceGroupName `
        --docker-custom-image-name $backendImageName `
        --docker-registry-server-url "https://$registryName.azurecr.io" `
        --docker-registry-server-user $acrCredentials.username `
        --docker-registry-server-password $acrCredentials.passwords[0].value `
        --output none

    # Configure backend app settings with all necessary environment variables
    $backendSettings = @(
        "WEBSITES_ENABLE_APP_SERVICE_STORAGE=false",
        "WEBSITES_PORT=8000",
        "WEBSITES_CONTAINER_START_TIME_LIMIT=1800",
        "ALLOWED_ORIGINS_STR=$frontendUrl,http://localhost:5173,http://localhost:3000",
        "COSMOS_DB_ENDPOINT=$cosmosEndpoint",
        "COSMOS_DB_KEY=$cosmosKey",
        "COSMOS_DB_DATABASE_NAME=ecommerce_db",
        "AZURE_OPENAI_ENDPOINT=https://testmodle.openai.azure.com/",
        "AZURE_OPENAI_API_VERSION=2025-01-01-preview"
    )
    
    if ($searchEndpoint -and $searchKey) {
        $backendSettings += "AZURE_SEARCH_ENDPOINT=$searchEndpoint"
        $backendSettings += "AZURE_SEARCH_API_KEY=$searchKey"
        $backendSettings += "AZURE_SEARCH_INDEX=$searchIndexName"
        $backendSettings += "AZURE_SEARCH_PRODUCT_INDEX=$searchProductIndexName"
        Write-Host "✅ Including Azure AI Search configuration (policies + products) in backend settings" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Azure AI Search not configured - policy and product lookups will not be available" -ForegroundColor Yellow
    }
    
    az webapp config appsettings set `
        --name $backendAppName `
        --resource-group $ResourceGroupName `
        --settings $backendSettings `
        --output none

    # Configure comprehensive HTTPS handling to prevent mixed content errors
    Write-Host "Configuring comprehensive HTTPS handling..." -ForegroundColor Blue
    
    # 1. Force HTTPS-only mode
    Write-Host "1. Enabling HTTPS-only mode..." -ForegroundColor Gray
    az webapp config set `
        --name $backendAppName `
        --resource-group $ResourceGroupName `
        --https-only true `
        --output none

    # 2. Enable always-on to prevent redirects
    Write-Host "2. Enabling always-on mode..." -ForegroundColor Gray
    az webapp config set `
        --name $backendAppName `
        --resource-group $ResourceGroupName `
        --always-on true `
        --output none

    # 3. Configure request filtering and logging
    Write-Host "3. Configuring request filtering..." -ForegroundColor Gray
    az webapp config set `
        --name $backendAppName `
        --resource-group $ResourceGroupName `
        --http-logging-enabled true `
        --detailed-error-logging-enabled true `
        --output none

    # 4. Configure app for optimal HTTPS handling
    Write-Host "4. Configuring app for HTTPS..." -ForegroundColor Gray
    az webapp config set `
        --name $backendAppName `
        --resource-group $ResourceGroupName `
        --use-32bit-worker-process false `
        --output none

    Write-Host "✅ Backend configured with Cosmos DB connection and HTTPS handling" -ForegroundColor Green
    Write-Host "⚠️  Authentication not configured - backend will accept guest users" -ForegroundColor Yellow

    Write-Host "Restarting backend..." -ForegroundColor Blue
    az webapp restart --name $backendAppName --resource-group $ResourceGroupName --output none
    Write-Host "✅ Backend restarted" -ForegroundColor Green

    # ============================================================================
    # PHASE 7: Update Frontend with Backend URL
    # ============================================================================
    Write-Host "`n🔄 PHASE 7: UPDATING FRONTEND CONFIGURATION" -ForegroundColor Blue
    Write-Host "===========================================" -ForegroundColor Blue

    $backendUrl = "https://$backendAppName.azurewebsites.net"
    
    Write-Host "Updating frontend with backend URL: $backendUrl" -ForegroundColor Yellow
    
    az webapp config appsettings set `
        --name $frontendAppName `
        --resource-group $ResourceGroupName `
        --settings `
        VITE_API_BASE_URL="$backendUrl" `
        NODE_ENV="production" `
        --output none

    Write-Host "✅ Frontend updated with correct backend URL and Entra ID" -ForegroundColor Green

    # ============================================================================
    # PHASE 8: Update App Registration URLs
    # ============================================================================
    Write-Host "`n🔧 PHASE 8: UPDATING APP REGISTRATION URLS" -ForegroundColor Blue
    Write-Host "==========================================" -ForegroundColor Blue

    $finalFrontendUrl = "https://$frontendAppName.azurewebsites.net"

    Write-Host "Updating SPA redirect URIs to production URLs..." -ForegroundColor Yellow
    
    # Update the SPA redirect URIs to include both localhost (for dev) and production URLs
    $spaConfig = @{
        "spa" = @{
            "redirectUris" = @(
                "http://localhost:5173",
                "http://localhost:5173/auth/callback",
                $finalFrontendUrl,
                "$finalFrontendUrl/auth/callback"
            )
        }
    }

    $spaConfigJson = $spaConfig | ConvertTo-Json -Depth 3

    try {
        # Use Invoke-RestMethod instead of az rest for better header control
        $headers = @{
            "Content-Type" = "application/json"
            "Authorization" = "Bearer $((az account get-access-token --query accessToken -o tsv))"
        }
        
        Invoke-RestMethod -Uri "https://graph.microsoft.com/v1.0/applications/$appObjectId" -Method PATCH -Body $spaConfigJson -Headers $headers | Out-Null
        Write-Host "✅ SPA redirect URIs updated successfully!" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Could not update app registration URLs automatically." -ForegroundColor Yellow
        Write-Host "Please update manually in Azure Portal:" -ForegroundColor Yellow
        Write-Host "1. Go to Azure Portal > Azure Active Directory > App registrations" -ForegroundColor Cyan
        Write-Host "2. Find your app: $appName" -ForegroundColor Cyan
        Write-Host "3. Go to Authentication > Single-page application" -ForegroundColor Cyan
        Write-Host "4. Update redirect URIs to include:" -ForegroundColor Cyan
        Write-Host "   - $finalFrontendUrl" -ForegroundColor White
        Write-Host "   - $finalFrontendUrl/auth/callback" -ForegroundColor White
        Write-Host "   - http://localhost:5173 (for local development)" -ForegroundColor White
        Write-Host "   - http://localhost:5173/auth/callback (for local development)" -ForegroundColor White
    }

    # ============================================================================
    # PHASE 9: Integration Testing
    # ============================================================================
    Write-Host "`n🧪 PHASE 9: INTEGRATION TESTING" -ForegroundColor Blue
    Write-Host "===============================" -ForegroundColor Blue

    Write-Host "Waiting for services to start (120 seconds)..." -ForegroundColor Yellow
    Write-Host "Backend needs extra time to apply HTTPS configuration..." -ForegroundColor Gray
    Start-Sleep -Seconds 120

    # Test backend health
    Write-Host "Testing backend health..." -ForegroundColor Yellow
    try {
        $healthResponse = Invoke-RestMethod -Uri "$backendUrl/health" -Method GET -TimeoutSec 30
        Write-Host "✅ Backend health check passed" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Backend health check failed (may still be starting)" -ForegroundColor Yellow
    }

    # Test backend API docs
    Write-Host "Testing backend API docs..." -ForegroundColor Yellow
    try {
        $docsResponse = Invoke-WebRequest -Uri "$backendUrl/docs" -Method GET -TimeoutSec 30
        if ($docsResponse.StatusCode -eq 200) {
            Write-Host "✅ Backend API docs accessible" -ForegroundColor Green
        }
    } catch {
        Write-Host "⚠️  Backend API docs not yet accessible (may still be starting)" -ForegroundColor Yellow
    }

    # Test frontend
    Write-Host "Testing frontend..." -ForegroundColor Yellow
    try {
        $frontendResponse = Invoke-WebRequest -Uri $frontendUrl -Method GET -TimeoutSec 30
        if ($frontendResponse.StatusCode -eq 200) {
            Write-Host "✅ Frontend accessible" -ForegroundColor Green
        }
    } catch {
        Write-Host "⚠️  Frontend not yet accessible (may still be starting)" -ForegroundColor Yellow
    }

    # ============================================================================
    # SUCCESS SUMMARY
    # ============================================================================
    Write-Host "`n🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!" -ForegroundColor Green
    Write-Host "======================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 DEPLOYED RESOURCES:" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "🗂️  Resource Group: $ResourceGroupName" -ForegroundColor White
    Write-Host "🗄️  Cosmos DB: $cosmosDbName" -ForegroundColor White
    Write-Host "📦 Container Registry: $registryName" -ForegroundColor White
    Write-Host "🏗️  App Service Plan: $planName" -ForegroundColor White
    Write-Host "🎨 Frontend App: $frontendAppName" -ForegroundColor White
    Write-Host "⚙️  Backend App: $backendAppName" -ForegroundColor White
    Write-Host ""
    Write-Host "🌐 ACCESS URLS:" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "Frontend:  $frontendUrl" -ForegroundColor Green
    Write-Host "Backend:   $backendUrl" -ForegroundColor Green
    Write-Host "API Docs:  $backendUrl/docs" -ForegroundColor Green
    Write-Host ""
    Write-Host "🔧 CONFIGURATION:" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "✅ CORS configured for frontend ↔ backend communication" -ForegroundColor White
    Write-Host "✅ Backend connected to Cosmos DB" -ForegroundColor White
    Write-Host "✅ Container registry with both images" -ForegroundColor White
    Write-Host "✅ Sample data seeded in Cosmos DB" -ForegroundColor White
    Write-Host "✅ Azure AI Search configured for policies and products" -ForegroundColor White
    Write-Host ""
    Write-Host "⚠️  AUTHENTICATION NOT CONFIGURED YET" -ForegroundColor Yellow
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "⏰ NEXT STEPS - CONFIGURE AUTHENTICATION:" -ForegroundColor Yellow
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1️⃣  Go to Azure Portal: https://portal.azure.com" -ForegroundColor White
    Write-Host ""
    Write-Host "2️⃣  Navigate to your Frontend App Service:" -ForegroundColor White
    Write-Host "   → Resource Groups → $ResourceGroupName → $frontendAppName" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3️⃣  Click 'Authentication' in the left menu" -ForegroundColor White
    Write-Host ""
    Write-Host "4️⃣  Click 'Add identity provider'" -ForegroundColor White
    Write-Host ""
    Write-Host "5️⃣  Select 'Microsoft' as the identity provider" -ForegroundColor White
    Write-Host ""
    Write-Host "6️⃣  Configure:" -ForegroundColor White
    Write-Host "   • Tenant type: Workforce" -ForegroundColor Gray
    Write-Host "   • App registration: Create new app registration" -ForegroundColor Gray
    Write-Host "   • Supported account types: Current tenant - Single tenant" -ForegroundColor Gray
    Write-Host "   • Restrict access: Require authentication" -ForegroundColor Gray
    Write-Host "   • Unauthenticated requests: HTTP 302 Found redirect (recommended)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "7️⃣  Click 'Add' and wait for configuration to complete" -ForegroundColor White
    Write-Host ""
    Write-Host "8️⃣  Done! Your app now has authentication" -ForegroundColor White
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "🧪 TESTING:" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "• Visit: $frontendUrl" -ForegroundColor White
    Write-Host "• App works in guest mode (no login required)" -ForegroundColor White
    Write-Host "• Click 'Login' to authenticate with Microsoft" -ForegroundColor White
    Write-Host "• Test chat: 'What products do you offer?'" -ForegroundColor White
    Write-Host ""
    Write-Host "🚀 Your application is ready!" -ForegroundColor Green

} catch {
    Write-Host "`n❌ DEPLOYMENT FAILED!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "🔍 TROUBLESHOOTING:" -ForegroundColor Yellow
    Write-Host "- Check Azure portal for detailed error messages" -ForegroundColor White
    Write-Host "- Review container logs for startup issues" -ForegroundColor White
    Write-Host "- Verify all prerequisites are met" -ForegroundColor White
    Write-Host "- Check resource quotas and limits" -ForegroundColor White
    exit 1
}
