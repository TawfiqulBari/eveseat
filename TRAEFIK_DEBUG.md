# Traefik Debugging Guide

## Check if Traefik is detecting services

```bash
# Get Traefik container name
docker ps | grep traefik

# Check HTTP routers (replace CONTAINER_NAME)
docker exec CONTAINER_NAME wget -qO- http://localhost:8080/api/http/routers | python3 -m json.tool

# Check services
docker exec CONTAINER_NAME wget -qO- http://localhost:8080/api/http/services | python3 -m json.tool

# Check entrypoints
docker exec CONTAINER_NAME wget -qO- http://localhost:8080/api/http/entrypoints | python3 -m json.tool
```

## Verify container labels

```bash
# Check frontend labels
docker inspect eve-frontend --format '{{json .Config.Labels}}' | python3 -m json.tool

# Check API labels
docker inspect eve-api --format '{{json .Config.Labels}}' | python3 -m json.tool
```

## Verify network connectivity

```bash
# Check if containers are on traefik-proxy network
docker network inspect traefik-proxy | grep -A 3 "eve-frontend"
docker network inspect traefik-proxy | grep -A 3 "eve-api"
```

## Common Issues

### 1. Traefik not detecting containers
- Ensure containers are on `traefik-proxy` network
- Check that `traefik.enable=true` label is present
- Restart Traefik: `docker restart traefik-traefik-1`

### 2. Routing conflicts
- Check router priorities (higher number = higher priority)
- Ensure frontend has higher priority than API
- Use `!PathPrefix` to exclude API routes from frontend

### 3. SSL certificate issues
- Check Traefik logs: `docker logs traefik-traefik-1 | grep -i cert`
- Verify DNS is pointing to server
- Ensure port 80 is open for HTTP challenge

### 4. 404 errors
- Verify service is running: `docker compose ps`
- Test service directly: `docker compose exec frontend curl http://localhost/`
- Check Traefik routing rules match your domain

## Test routing manually

```bash
# Test frontend directly
docker compose exec frontend curl -s http://localhost/ | head -5

# Test API directly
docker compose exec api curl -s http://localhost:8000/health

# Test through Traefik (if accessible)
curl -H "Host: eveseat.tawfiqulbari.work" http://localhost/
```

