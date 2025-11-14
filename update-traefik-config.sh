#!/bin/bash
# Script to update Traefik file-based configuration with current container IPs

set -e

echo "🔄 Updating Traefik configuration with current container IPs..."

# Get network ID
NETWORK_ID=$(docker network inspect traefik-proxy --format '{{.Id}}')

# Get container IPs
FRONTEND_IP=$(docker inspect eve-frontend --format "{{range .NetworkSettings.Networks}}{{if eq .NetworkID \"$NETWORK_ID\"}}{{.IPAddress}}{{end}}{{end}}")
API_IP=$(docker inspect eve-api --format "{{range .NetworkSettings.Networks}}{{if eq .NetworkID \"$NETWORK_ID\"}}{{.IPAddress}}{{end}}{{end}}")

echo "Frontend IP: $FRONTEND_IP"
echo "API IP: $API_IP"

# Create configuration file
cat > /tmp/traefik-routers.yml <<EOF
http:
  routers:
    eve-frontend:
      rule: "Host(\`eveseat.tawfiqulbari.work\`) && !PathPrefix(\`/api\`)"
      entryPoints:
        - websecure
      service: eve-frontend
      tls:
        certResolver: le
      priority: 10
      middlewares:
        - security-headers
        - compression
    
    eve-frontend-http:
      rule: "Host(\`eveseat.tawfiqulbari.work\`) && !PathPrefix(\`/api\`)"
      entryPoints:
        - web
      service: eve-frontend
      priority: 10
      middlewares:
        - redirect-to-https
    
    eve-api:
      rule: "Host(\`eveseat.tawfiqulbari.work\`) && PathPrefix(\`/api\`)"
      entryPoints:
        - websecure
      service: eve-api
      tls:
        certResolver: le
      middlewares:
        - eve-api-stripprefix
        - security-headers
    
    eve-api-http:
      rule: "Host(\`eveseat.tawfiqulbari.work\`) && PathPrefix(\`/api\`)"
      entryPoints:
        - web
      service: eve-api
      middlewares:
        - eve-api-stripprefix
        - security-headers

  services:
    eve-frontend:
      loadBalancer:
        servers:
          - url: "http://$FRONTEND_IP:80"
    
    eve-api:
      loadBalancer:
        servers:
          - url: "http://$API_IP:8000"

  middlewares:
    eve-api-stripprefix:
      stripPrefix:
        prefixes:
          - "/api"
    
    redirect-to-https:
      redirectScheme:
        scheme: https
        permanent: true
    
    security-headers:
      headers:
        frameDeny: true
        sslRedirect: true
        browserXssFilter: true
        contentTypeNosniff: true
        forceSTSHeader: true
        stsIncludeSubdomains: true
        stsPreload: true
        stsSeconds: 31536000
    
    compression:
      compress: {}
EOF

# Copy to Traefik container
docker cp /tmp/traefik-routers.yml traefik-traefik-1:/etc/traefik/dynamic/routers.yml

echo "✅ Configuration updated"
echo "⏳ Traefik will reload automatically (file watching enabled)"

