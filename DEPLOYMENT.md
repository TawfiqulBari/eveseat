# EVE Seat - Production Deployment Guide

**Server IP**: 217.216.111.197
**Domain**: eveseat.tawfiqulbari.work
**Traefik**: External (already running on ports 80/443)
**SSL**: Let's Encrypt (email: tawfiqulbari@gmail.com)

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Server Setup](#initial-server-setup)
3. [Deployment Methods](#deployment-methods)
   - [Method A: GitHub Actions (Recommended)](#method-a-github-actions-recommended)
   - [Method B: Manual Deployment](#method-b-manual-deployment)
4. [Post-Deployment](#post-deployment)
5. [Troubleshooting](#troubleshooting)
6. [Maintenance](#maintenance)

---

## Prerequisites

### On Your Server (217.216.111.197)

1. **Docker** installed
   ```bash
   docker --version  # Should be 20.10+
   ```

2. **Docker Compose** installed
   ```bash
   docker-compose --version  # Should be 1.29+ or docker compose version 2.0+
   ```

3. **Traefik** running with external network
   ```bash
   docker network ls | grep traefik-proxy  # Should exist
   docker ps | grep traefik  # Should be running
   ```

4. **Git** installed
   ```bash
   git --version
   ```

5. **Firewall** configured (ports 80, 443 open)
   ```bash
   sudo ufw status
   ```

### On Your Local Machine

1. **SSH access** to server
   ```bash
   ssh root@217.216.111.197  # Using id_rsa key
   ```

2. **GitHub account** with repository access

---

## Initial Server Setup

### 1. Create Deployment Directory

```bash
# SSH into your server
ssh root@217.216.111.197

# Create application directory
sudo mkdir -p /opt/eveseat
cd /opt/eveseat

# Clone the repository
git clone https://github.com/TawfiqulBari/eveseat.git .

# Or if you've already cloned, just navigate
cd /opt/eveseat
```

### 2. Create Environment File

```bash
# Copy the example environment file
cp .env.production.example .env

# Edit the file
nano .env
```

**IMPORTANT: Fill in these values:**

```bash
# Required values:
POSTGRES_PASSWORD=<generate-strong-password>
SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_urlsafe(32))">
ENCRYPTION_KEY=<generate-with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">

# EVE Online ESI credentials (from https://developers.eveonline.com/applications):
ESI_CLIENT_ID=<your-esi-client-id>
ESI_CLIENT_SECRET=<your-esi-client-secret>

# Optional but recommended:
ZKILL_REDISQ_QUEUE_ID=<generate-with: python -c "import uuid; print(str(uuid.uuid4()))">
```

Save and exit (`Ctrl+X`, then `Y`, then `Enter`).

### 3. Verify Traefik Network

```bash
# Check if traefik-proxy network exists
docker network ls | grep traefik-proxy

# If it doesn't exist, create it:
docker network create traefik-proxy
```

### 4. Verify Domain DNS

Ensure `eveseat.tawfiqulbari.work` and `flower.eveseat.tawfiqulbari.work` point to `217.216.111.197`:

```bash
# Test DNS resolution
nslookup eveseat.tawfiqulbari.work
nslookup flower.eveseat.tawfiqulbari.work

# Should both return 217.216.111.197
```

---

## Deployment Methods

### Method A: GitHub Actions (Recommended)

**Automated deployment on every push to main branch**

#### Setup Steps:

##### 1. Add Secrets to GitHub Repository

Go to: `https://github.com/TawfiqulBari/eveseat/settings/secrets/actions`

Click **"New repository secret"** and add:

| Secret Name | Secret Value |
|------------|-------------|
| `SERVER_IP` | `217.216.111.197` |
| `SSH_USER` | `root` |
| `SSH_PRIVATE_KEY` | *Contents of your id_rsa file* |
| `DEPLOYMENT_PATH` | `/opt/eveseat` |

To get your private key:
```bash
# On your local machine (where you have the key that connects to 217.216.111.197)
cat ~/.ssh/id_rsa
# Copy everything including "-----BEGIN OPENSSH PRIVATE KEY-----" and "-----END OPENSSH PRIVATE KEY-----"
```

##### 2. Deploy

```bash
# On your local machine
git push origin main

# GitHub Actions will automatically:
# 1. SSH into your server
# 2. Pull latest code
# 3. Rebuild containers
# 4. Run database migrations
# 5. Restart services
```

##### 3. Monitor Deployment

- Check workflow: `https://github.com/TawfiqulBari/eveseat/actions`
- Watch logs in real-time
- Get notified of failures

---

### Method B: Manual Deployment

**Traditional SSH deployment**

#### Initial Deployment:

```bash
# SSH into server
ssh root@217.216.111.197
cd /opt/eveseat

# Pull latest code
git pull origin main

# Build and start services
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Run database migrations
docker-compose exec api alembic upgrade head

# Check service status
docker-compose ps
```

#### Updating After Code Changes:

```bash
# SSH into server
ssh root@217.216.111.197
cd /opt/eveseat

# Pull latest code
git pull origin main

# Rebuild and restart (minimal downtime)
docker-compose up -d --build

# Run new migrations (if any)
docker-compose exec api alembic upgrade head

# Check health
curl https://eveseat.tawfiqulbari.work/api/v1/health
```

---

## Post-Deployment

### 1. Verify Services Are Running

```bash
# Check all containers
docker-compose ps

# Should show:
# - eve-postgres (healthy)
# - eve-redis (healthy)
# - eve-api (running)
# - eve-websocket (running)
# - eve-worker (running)
# - eve-scheduler (running)
# - eve-flower (running)
# - eve-frontend (running)
```

### 2. Check Application Health

```bash
# Test API health endpoint
curl https://eveseat.tawfiqulbari.work/api/v1/health

# Should return:
# {"status": "healthy", "database": "healthy"}

# Test frontend
curl -I https://eveseat.tawfiqulbari.work

# Should return HTTP/2 200
```

### 3. Verify Traefik Routing

```bash
# Check if Traefik detects services (if you have access to Traefik dashboard)
# Or test routes:

curl -H "Host: eveseat.tawfiqulbari.work" http://localhost/
curl -H "Host: eveseat.tawfiqulbari.work" http://localhost/api/v1/health
```

### 4. Check Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f frontend

# Check for errors
docker-compose logs | grep -i error
```

### 5. Access Monitoring

- **Frontend**: https://eveseat.tawfiqulbari.work
- **API Docs**: https://eveseat.tawfiqulbari.work/api/v1/docs
- **Flower (Celery)**: https://flower.eveseat.tawfiqulbari.work

### 6. Test EVE Online Login

1. Go to https://eveseat.tawfiqulbari.work
2. Click "Login with EVE Online"
3. Authorize the application
4. Verify successful login and character loading

---

## Troubleshooting

### Services Not Starting

```bash
# Check for port conflicts
sudo netstat -tulpn | grep LISTEN

# Note: EVE Seat uses NO host ports - all routing through Traefik
# Only Traefik needs ports 80/443

# Check Docker daemon
sudo systemctl status docker

# Restart Docker if needed
sudo systemctl restart docker
```

### Database Connection Issues

```bash
# Check PostgreSQL logs
docker-compose logs postgres | tail -50

# Test database connection
docker-compose exec postgres psql -U eve_user -d eve_db -c "SELECT 1;"

# Check database exists
docker-compose exec postgres psql -U eve_user -l
```

### Migration Errors

```bash
# Check migration status
docker-compose exec api alembic current

# View migration history
docker-compose exec api alembic history

# Rollback one migration
docker-compose exec api alembic downgrade -1

# Re-run migrations
docker-compose exec api alembic upgrade head

# Force rebuild if schema is corrupt (DESTRUCTIVE)
# WARNING: This deletes all data!
docker-compose down -v  # Removes volumes
docker volume rm eveseat_postgres_data eveseat_redis_data
docker-compose up -d
docker-compose exec api alembic upgrade head
```

### Traefik Not Routing

```bash
# Check if containers are on traefik-proxy network
docker network inspect traefik-proxy | grep eve-

# Verify container labels
docker inspect eve-frontend --format '{{json .Config.Labels}}' | python3 -m json.tool
docker inspect eve-api --format '{{json .Config.Labels}}' | python3 -m json.tool

# Restart services
docker-compose restart frontend api websocket

# Restart Traefik (find your Traefik container name first)
docker ps | grep traefik
docker restart <traefik-container-name>
```

### SSL Certificate Issues

```bash
# Check Traefik logs for certificate errors
docker logs <traefik-container-name> | grep -i cert

# Common issues:
# 1. DNS not pointing to server → Fix DNS
# 2. Port 80 blocked → Open firewall
# 3. Rate limit hit → Wait 1 hour, use staging LE

# Force certificate renewal (in Traefik config)
# Delete certificate and restart Traefik
```

### 502 Bad Gateway

```bash
# Service is not responding - check if it's running
docker-compose ps

# Check service logs
docker-compose logs api
docker-compose logs frontend

# Restart the service
docker-compose restart api

# Check service health internally
docker-compose exec api curl http://localhost:8000/health
```

### WebSocket Connection Fails

```bash
# Check WebSocket service
docker-compose logs websocket

# Test WebSocket internally
docker-compose exec websocket curl http://localhost:8001/health

# Verify Traefik WebSocket routing
# Check browser console for WebSocket errors
```

### High Resource Usage

```bash
# Check resource usage
docker stats

# If worker is using too much CPU/memory:
# Reduce concurrency in docker-compose.yml:
# command: celery -A app.tasks worker --loglevel=info --concurrency=2

# If PostgreSQL is using too much memory:
# Adjust PostgreSQL config in .env
```

---

## Maintenance

### View Logs

```bash
# Real-time logs (all services)
docker-compose logs -f

# Last 100 lines from specific service
docker-compose logs --tail=100 api

# Logs since specific time
docker-compose logs --since=2h api

# Save logs to file
docker-compose logs > eveseat_logs_$(date +%Y%m%d).txt
```

### Database Backup

```bash
# Create backup
docker-compose exec postgres pg_dump -U eve_user eve_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Create compressed backup
docker-compose exec postgres pg_dump -U eve_user eve_db | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Restore from backup
docker-compose exec -T postgres psql -U eve_user eve_db < backup_20250115_120000.sql
```

### Update Application

```bash
# Pull latest code
cd /opt/eveseat
git pull origin main

# Rebuild and restart
docker-compose up -d --build

# Run new migrations
docker-compose exec api alembic upgrade head

# Verify health
curl https://eveseat.tawfiqulbari.work/api/v1/health
```

### Clean Up Docker Resources

```bash
# Remove unused containers
docker container prune -f

# Remove unused images
docker image prune -a -f

# Remove unused volumes (CAREFUL - this can delete data)
docker volume prune -f

# Remove unused networks
docker network prune -f

# Full cleanup (CAREFUL)
docker system prune -a --volumes -f
```

### Monitor Celery Tasks

Access Flower dashboard:
```
https://flower.eveseat.tawfiqulbari.work
```

Or via CLI:
```bash
# List active tasks
docker-compose exec worker celery -A app.tasks inspect active

# List scheduled tasks
docker-compose exec scheduler celery -A app.tasks inspect scheduled

# View task stats
docker-compose exec worker celery -A app.tasks inspect stats
```

### Update Environment Variables

```bash
# Edit .env file
nano .env

# Restart services to apply changes
docker-compose down
docker-compose up -d

# Or restart specific service
docker-compose restart api
```

---

## Security Checklist

- [ ] Strong PostgreSQL password set
- [ ] SECRET_KEY is random and secure
- [ ] ENCRYPTION_KEY is properly generated
- [ ] ESI credentials are kept secret
- [ ] Firewall configured (only 22, 80, 443 open)
- [ ] SSH key authentication enabled (password auth disabled)
- [ ] Regular backups configured
- [ ] Traefik SSL certificates working (Let's Encrypt)
- [ ] Debug mode disabled (DEBUG=False)
- [ ] CORS origins properly configured

---

## Network & Port Configuration

**NO Port Conflicts!** All services use internal Docker networking:

- PostgreSQL: Internal only (no host port)
- Redis: Internal only (no host port)
- API: Internal port 8000 (routed via Traefik)
- WebSocket: Internal port 8001 (routed via Traefik)
- Flower: Internal port 5555 (routed via Traefik)
- Frontend: Internal port 80 (routed via Traefik)

**Only Traefik** uses host ports 80/443 (already running externally).

---

## Support

### Documentation
- GitHub: https://github.com/TawfiqulBari/eveseat
- EVE ESI Docs: https://docs.esi.evetech.net/
- Traefik Docs: https://doc.traefik.io/traefik/

### Logs Location
- Application: `docker-compose logs`
- Traefik: `docker logs <traefik-container>`
- System: `/var/log/syslog`

### Health Check URLs
- API: https://eveseat.tawfiqulbari.work/api/v1/health
- Frontend: https://eveseat.tawfiqulbari.work
- Flower: https://flower.eveseat.tawfiqulbari.work

---

**Deployment Complete!** 🚀

Access your application at: **https://eveseat.tawfiqulbari.work**
