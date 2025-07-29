# TigerGraph Community Edition Setup Script (PowerShell)
# Automates the download, loading, and startup of TigerGraph Community Edition
# Part of the Hybrid AI Council project

# Set error action preference
$ErrorActionPreference = "Stop"

Write-Host "🚀 TigerGraph Community Edition Setup" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green

# Configuration
$TIGERGRAPH_IMAGE = "tigergraph/community:4.2.0"
$CONTAINER_NAME = "tigergraph"
$DOWNLOAD_URL = "https://dl.tigergraph.com/tigergraph-4.2.0-community-docker-image.tar.gz"
$TAR_FILE = "tigergraph-4.2.0-community-docker-image.tar.gz"
$PORT = "14240"

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

# Function to check if container exists and is running
function Check-ContainerStatus {
    $runningContainer = docker ps -q -f name=$CONTAINER_NAME
    if ($runningContainer) {
        Write-Host "✅ TigerGraph container is already running!" -ForegroundColor Green
        Write-Host "🌐 Access GraphStudio at: http://localhost:$PORT" -ForegroundColor Cyan
        Write-Host "🔑 Default credentials: tigergraph/tigergraph" -ForegroundColor Yellow
        return $true
    }
    
    $existingContainer = docker ps -a -q -f name=$CONTAINER_NAME
    if ($existingContainer) {
        Write-Host "🔄 TigerGraph container exists but is stopped. Starting..." -ForegroundColor Yellow
        docker start $CONTAINER_NAME
        Write-Host "✅ TigerGraph container started!" -ForegroundColor Green
        Write-Host "🌐 Access GraphStudio at: http://localhost:$PORT" -ForegroundColor Cyan
        return $true
    }
    
    return $false
}

# Check if already running
if (Check-ContainerStatus) {
    exit 0
}

# Check if image exists locally
$localImage = docker images -q $TIGERGRAPH_IMAGE
if ($localImage) {
    Write-Host "✅ TigerGraph Community Edition image found locally" -ForegroundColor Green
} else {
    Write-Host "📥 TigerGraph Community Edition image not found locally" -ForegroundColor Yellow
    
    # Check if tar.gz file exists
    if (-not (Test-Path $TAR_FILE)) {
        Write-Host "📥 Downloading TigerGraph Community Edition..." -ForegroundColor Yellow
        Write-Host "⚠️  This is a large file (2.4GB) - please be patient" -ForegroundColor Yellow
        Write-Host "🌐 Download URL: $DOWNLOAD_URL" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "⚠️  MANUAL DOWNLOAD REQUIRED:" -ForegroundColor Yellow
        Write-Host "   1. Visit: https://dl.tigergraph.com/" -ForegroundColor White
        Write-Host "   2. Download: tigergraph-4.2.0-community-docker-image.tar.gz" -ForegroundColor White
        Write-Host "   3. Place it in this project directory" -ForegroundColor White
        Write-Host "   4. Run this script again" -ForegroundColor White
        Write-Host ""
        exit 1
    }
    
    Write-Host "📦 Loading TigerGraph Community Edition image from $TAR_FILE..." -ForegroundColor Yellow
    docker load -i $TAR_FILE
    Write-Host "✅ Image loaded successfully!" -ForegroundColor Green
}

# Remove any existing container with the same name
$existingContainer = docker ps -a -q -f name=$CONTAINER_NAME
if ($existingContainer) {
    Write-Host "🧹 Removing existing container..." -ForegroundColor Yellow
    docker rm -f $CONTAINER_NAME
}

# Run TigerGraph Community Edition
Write-Host "🚀 Starting TigerGraph Community Edition container..." -ForegroundColor Green
docker run -d --init --name $CONTAINER_NAME -p "${PORT}:${PORT}" $TIGERGRAPH_IMAGE

# Wait for container to be ready
Write-Host "⏳ Waiting for TigerGraph to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check if container is running
$runningContainer = docker ps -q -f name=$CONTAINER_NAME
if ($runningContainer) {
    Write-Host ""
    Write-Host "🎉 SUCCESS! TigerGraph Community Edition is running!" -ForegroundColor Green
    Write-Host "======================================================" -ForegroundColor Green
    Write-Host "🌐 GraphStudio UI: http://localhost:$PORT" -ForegroundColor Cyan
    Write-Host "🔑 Username: tigergraph" -ForegroundColor Yellow
    Write-Host "🔑 Password: tigergraph" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "📋 Useful Commands:" -ForegroundColor White
    Write-Host "   Stop:    docker stop $CONTAINER_NAME" -ForegroundColor Gray
    Write-Host "   Start:   docker start $CONTAINER_NAME" -ForegroundColor Gray
    Write-Host "   Logs:    docker logs $CONTAINER_NAME" -ForegroundColor Gray
    Write-Host "   Shell:   docker exec -it $CONTAINER_NAME bash" -ForegroundColor Gray
    Write-Host ""
    Write-Host "📚 Next Steps:" -ForegroundColor White
    Write-Host "   1. Login to GraphStudio" -ForegroundColor Gray
    Write-Host "   2. Run: python scripts/init_tigergraph.py" -ForegroundColor Gray
    Write-Host "   3. Load your schema from schemas/schema.gsql" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "❌ Failed to start TigerGraph container" -ForegroundColor Red
    Write-Host "📋 Check logs: docker logs $CONTAINER_NAME" -ForegroundColor Yellow
    exit 1
} 