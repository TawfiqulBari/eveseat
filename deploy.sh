#!/bin/bash

# EVE Online Management Platform - Deployment Script
# This script builds and deploys the application to production

set -e  # Exit on error

echo "🚀 Starting deployment of EVE Online Management Platform..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "📝 Please create a .env file based on .env.example"
    echo "   cp .env.example .env"
    echo "   Then edit .env with your actual configuration values"
    exit 1
fi

# Check if Traefik network exists
echo "🔍 Checking for Traefik network..."
if ! docker network ls | grep -q traefik-proxy; then
    echo "⚠️  Warning: traefik-proxy network not found!"
    echo "   Creating traefik-proxy network..."
    docker network create traefik-proxy || true
fi

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker compose down || true

# Build images
echo "🔨 Building Docker images..."
docker compose build --no-cache

# Start services
echo "🚀 Starting services..."
docker compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
docker compose ps

# Show logs
echo "📋 Recent logs:"
docker compose logs --tail=50

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Application should be available at:"
echo "   Frontend: https://eveseat.tawfiqulbari.work"
echo "   API: https://eveseat.tawfiqulbari.work/api/v1"
echo "   Flower: https://flower.eveseat.tawfiqulbari.work"
echo ""
echo "📊 To view logs:"
echo "   docker compose logs -f [service-name]"
echo ""
echo "🛑 To stop services:"
echo "   docker compose down"
echo ""

