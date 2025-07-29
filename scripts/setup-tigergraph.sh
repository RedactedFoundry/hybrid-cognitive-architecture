#!/bin/bash

# TigerGraph Community Edition Setup Script
# Automates the download, loading, and startup of TigerGraph Community Edition
# Part of the Hybrid AI Council project

set -e  # Exit on any error

echo "🚀 TigerGraph Community Edition Setup"
echo "======================================"

# Configuration
TIGERGRAPH_IMAGE="tigergraph/community:4.2.0"
CONTAINER_NAME="tigergraph"
DOWNLOAD_URL="https://dl.tigergraph.com/tigergraph-4.2.0-community-docker-image.tar.gz"
TAR_FILE="tigergraph-4.2.0-community-docker-image.tar.gz"
PORT="14240"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

# Function to check if container exists and is running
check_container_status() {
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        echo "✅ TigerGraph container is already running!"
        echo "🌐 Access GraphStudio at: http://localhost:$PORT"
        echo "🔑 Default credentials: tigergraph/tigergraph"
        return 0
    elif docker ps -a -q -f name="$CONTAINER_NAME" | grep -q .; then
        echo "🔄 TigerGraph container exists but is stopped. Starting..."
        docker start "$CONTAINER_NAME"
        echo "✅ TigerGraph container started!"
        echo "🌐 Access GraphStudio at: http://localhost:$PORT"
        return 0
    fi
    return 1
}

# Check if already running
if check_container_status; then
    exit 0
fi

# Check if image exists locally
if docker images -q "$TIGERGRAPH_IMAGE" | grep -q .; then
    echo "✅ TigerGraph Community Edition image found locally"
else
    echo "📥 TigerGraph Community Edition image not found locally"
    
    # Check if tar.gz file exists
    if [ ! -f "$TAR_FILE" ]; then
        echo "📥 Downloading TigerGraph Community Edition..."
        echo "⚠️  This is a large file (2.4GB) - please be patient"
        echo "🌐 Download URL: $DOWNLOAD_URL"
        echo ""
        echo "⚠️  MANUAL DOWNLOAD REQUIRED:"
        echo "   1. Visit: https://dl.tigergraph.com/"
        echo "   2. Download: tigergraph-4.2.0-community-docker-image.tar.gz"
        echo "   3. Place it in this project directory"
        echo "   4. Run this script again"
        echo ""
        exit 1
    fi
    
    echo "📦 Loading TigerGraph Community Edition image from $TAR_FILE..."
    docker load -i "$TAR_FILE"
    echo "✅ Image loaded successfully!"
fi

# Remove any existing container with the same name
if docker ps -a -q -f name="$CONTAINER_NAME" | grep -q .; then
    echo "🧹 Removing existing container..."
    docker rm -f "$CONTAINER_NAME"
fi

# Run TigerGraph Community Edition
echo "🚀 Starting TigerGraph Community Edition container..."
docker run -d \
    --init \
    --name "$CONTAINER_NAME" \
    -p "$PORT:$PORT" \
    "$TIGERGRAPH_IMAGE"

# Wait for container to be ready
echo "⏳ Waiting for TigerGraph to initialize..."
sleep 10

# Check if container is running
if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
    echo ""
    echo "🎉 SUCCESS! TigerGraph Community Edition is running!"
    echo "======================================================"
    echo "🌐 GraphStudio UI: http://localhost:$PORT"
    echo "🔑 Username: tigergraph"
    echo "🔑 Password: tigergraph"
    echo ""
    echo "📋 Useful Commands:"
    echo "   Stop:    docker stop $CONTAINER_NAME"
    echo "   Start:   docker start $CONTAINER_NAME"
    echo "   Logs:    docker logs $CONTAINER_NAME"
    echo "   Shell:   docker exec -it $CONTAINER_NAME bash"
    echo ""
    echo "📚 Next Steps:"
    echo "   1. Login to GraphStudio"
    echo "   2. Run: python scripts/init_tigergraph.py"
    echo "   3. Load your schema from schemas/schema.gsql"
    echo ""
else
    echo "❌ Failed to start TigerGraph container"
    echo "📋 Check logs: docker logs $CONTAINER_NAME"
    exit 1
fi 