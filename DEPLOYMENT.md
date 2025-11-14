# Deployment Guide

This guide will help you deploy the EVE Online Management Platform to production at `https://eveseat.tawfiqulbari.work`.

## Prerequisites

1. **Docker and Docker Compose** installed on the server
2. **Traefik** running on the server with:
   - Let's Encrypt certificate resolver configured (`le`)
   - Entrypoint `websecure` for HTTPS (port 443)
   - Network `traefik-proxy` created
3. **DNS** configured to point `eveseat.tawfiqulbari.work` to your server's IP
4. **EVE Online ESI Application** created at https://developers.eveonline.com/applications

## Step 1: Environment Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env
nano .env
```

Required environment variables:

```env
# Database Configuration
POSTGRES_USER=eve_user
POSTGRES_PASSWORD=<strong_random_password>
POSTGRES_DB=eve_db

# Security Keys (Generate strong random keys)
SECRET_KEY=<generate_with_openssl_rand_hex_32>
ENCRYPTION_KEY=<generate_with_openssl_rand_hex_32>

# EVE Online ESI Configuration
ESI_CLIENT_ID=<your_esi_client_id>
ESI_CLIENT_SECRET=<your_esi_client_secret>
ESI_CALLBACK_URL=https://eveseat.tawfiqulbari.work/api/v1/auth/callback
ESI_BASE_URL=https://esi.evetech.net/latest

# Application Configuration
DEBUG=False
ALLOWED_ORIGINS=https://eveseat.tawfiqulbari.work
CORS_ORIGINS=["https://eveseat.tawfiqulbari.work"]

# Frontend Build Configuration
VITE_API_URL=https://eveseat.tawfiqulbari.work/api/v1
VITE_WS_URL=wss://eveseat.tawfiqulbari.work/ws

# Optional: zKillboard
ZKILL_REDISQ_QUEUE_ID=
```

### Generate Security Keys

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate ENCRYPTION_KEY (must be 32 bytes base64-encoded for Fernet)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Step 2: Verify Traefik Network

Ensure the Traefik network exists:

```bash
docker network ls | grep traefik-proxy
```

If it doesn't exist, create it:

```bash
docker network create traefik-proxy
```

## Step 3: Deploy the Application

### Option A: Using the Deployment Script

```bash
./deploy.sh
```

### Option B: Manual Deployment

```bash
# Stop existing containers
docker-compose down

# Build images
docker-compose build --no-cache

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

## Step 4: Database Migrations

Run database migrations:

```bash
docker-compose exec api alembic upgrade head
```

## Step 5: Verify Deployment

1. **Check service health:**
   ```bash
   docker-compose ps
   ```

2. **Check logs:**
   ```bash
   docker-compose logs -f api
   docker-compose logs -f frontend
   ```

3. **Test endpoints:**
   - Frontend: https://eveseat.tawfiqulbari.work
   - API Health: https://eveseat.tawfiqulbari.work/api/v1/health
   - API Docs: https://eveseat.tawfiqulbari.work/api/v1/docs
   - Flower: https://flower.eveseat.tawfiqulbari.work

## Service Architecture

The application consists of:

- **frontend**: React app served by Nginx
- **api**: FastAPI backend
- **websocket**: WebSocket server for real-time updates
- **worker**: Celery worker for background tasks
- **scheduler**: Celery Beat for scheduled tasks
- **flower**: Celery monitoring UI
- **postgres**: PostgreSQL database
- **redis**: Redis cache and message broker

## Traefik Routing

Services are routed through Traefik:

- **Frontend**: `https://eveseat.tawfiqulbari.work/`
- **API**: `https://eveseat.tawfiqulbari.work/api/v1/`
- **WebSocket**: `wss://eveseat.tawfiqulbari.work/ws/`
- **Flower**: `https://flower.eveseat.tawfiqulbari.work/`

## Troubleshooting

### Services won't start

1. Check logs: `docker-compose logs [service-name]`
2. Verify `.env` file exists and has all required variables
3. Check Traefik network: `docker network inspect traefik-proxy`
4. Verify DNS is pointing to the server

### SSL Certificate Issues

1. Check Traefik logs: `docker logs [traefik-container]`
2. Verify Let's Encrypt resolver is configured in Traefik
3. Ensure port 80 and 443 are open in firewall

### Database Connection Issues

1. Verify PostgreSQL is running: `docker-compose ps postgres`
2. Check database credentials in `.env`
3. Test connection: `docker-compose exec postgres psql -U eve_user -d eve_db`

### Frontend Not Loading

1. Check frontend logs: `docker-compose logs frontend`
2. Verify build completed: `docker-compose exec frontend ls -la /usr/share/nginx/html`
3. Check Traefik labels on frontend service

## Maintenance

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart api
```

### Update Application

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose build --no-cache
docker-compose up -d

# Run migrations if needed
docker-compose exec api alembic upgrade head
```

### Backup Database

```bash
docker-compose exec postgres pg_dump -U eve_user eve_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore Database

```bash
docker-compose exec -T postgres psql -U eve_user eve_db < backup_file.sql
```

## Security Notes

1. **Never commit `.env` file** to version control
2. **Use strong passwords** for database and security keys
3. **Keep dependencies updated**: `docker-compose build --no-cache`
4. **Monitor logs** for suspicious activity
5. **Regular backups** of database

## Support

For issues or questions, check:
- Application logs: `docker-compose logs`
- Traefik dashboard: Check your Traefik configuration
- EVE ESI status: https://status.eveonline.com/

