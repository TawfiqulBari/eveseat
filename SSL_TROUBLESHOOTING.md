# SSL Certificate Troubleshooting

## Issue: SSL Certificate Not Ready

If you're seeing SSL certificate errors, here are the steps to resolve:

### 1. Check Traefik Configuration

The Traefik container needs to be configured with Let's Encrypt. Verify your Traefik configuration includes:

```yaml
certificatesResolvers:
  le:
    acme:
      email: your-email@example.com
      storage: /letsencrypt/acme.json
      httpChallenge:
        entryPoint: web
```

### 2. Verify DNS

Ensure DNS is properly configured:
```bash
dig eveseat.tawfiqulbari.work
# Should return your server's IP address
```

### 3. Check Ports

Ensure ports 80 and 443 are open:
```bash
sudo ufw status
# Ports 80 and 443 should be open
```

### 4. Check Traefik Logs

```bash
docker logs traefik-traefik-1 | grep -i "certificate\|acme\|error"
```

### 5. Force Certificate Renewal

If certificates aren't generating:
1. Check Traefik dashboard: http://your-server-ip:8080
2. Look for certificate errors in the dashboard
3. Restart Traefik if needed: `docker restart traefik-traefik-1`

### 6. Manual Certificate Check

```bash
# Check if certificate file exists
docker exec traefik-traefik-1 ls -la /letsencrypt/

# Check certificate status
curl -vI https://eveseat.tawfiqulbari.work
```

### Common Issues

1. **DNS not propagated**: Wait 5-10 minutes after DNS changes
2. **Port 80 blocked**: Let's Encrypt needs port 80 for HTTP challenge
3. **Rate limiting**: Let's Encrypt has rate limits (50 certs/week per domain)
4. **Traefik not detecting containers**: Ensure containers are on `traefik-proxy` network

### Temporary Workaround

If SSL isn't working immediately, you can temporarily access via HTTP:
- http://eveseat.tawfiqulbari.work (Traefik should redirect to HTTPS)

Note: SSL certificates typically take 1-5 minutes to generate after first access.

