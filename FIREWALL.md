# Firewall Configuration

## Overview

This document describes the firewall configuration for the EVE Online Management Platform host.

## Requirements

- **Ports 22, 80, 443**: Accessible from anywhere (0.0.0.0/0)
- **Database ports**: Only accessible from 217.216.111.194

## Database Ports to Secure

The following database ports are restricted:
- `5432` - PostgreSQL default
- `5433` - PostgreSQL alternate
- `6379` - Redis default
- `15432` - Salesapp PostgreSQL
- `15379` - Salesapp Redis
- `3306` - MySQL default
- `27017` - MongoDB default

## Configuration

### Automatic Configuration

Run the firewall configuration script:

```bash
sudo ./scripts/configure-firewall.sh
```

### Manual Configuration

If you prefer to configure manually:

```bash
# Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH, HTTP, HTTPS from anywhere
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Restrict database ports to specific IP
sudo ufw allow from 217.216.111.194 to any port 5432 proto tcp comment 'PostgreSQL from allowed IP'
sudo ufw allow from 217.216.111.194 to any port 5433 proto tcp comment 'PostgreSQL alternate from allowed IP'
sudo ufw allow from 217.216.111.194 to any port 6379 proto tcp comment 'Redis from allowed IP'
sudo ufw allow from 217.216.111.194 to any port 15432 proto tcp comment 'Salesapp PostgreSQL from allowed IP'
sudo ufw allow from 217.216.111.194 to any port 15379 proto tcp comment 'Salesapp Redis from allowed IP'
sudo ufw allow from 217.216.111.194 to any port 3306 proto tcp comment 'MySQL from allowed IP'
sudo ufw allow from 217.216.111.194 to any port 27017 proto tcp comment 'MongoDB from allowed IP'

# Enable UFW
sudo ufw enable
```

### Verify Configuration

Check firewall status:

```bash
sudo ufw status verbose
```

## Important Notes

1. **SSH Access**: Make sure you have SSH access before enabling the firewall, or you may lock yourself out!

2. **Existing Traefik**: There's already a Traefik instance running on ports 80/443. You have two options:
   - **Option A**: Use the existing Traefik and configure our services to work with it (recommended)
   - **Option B**: Stop the existing Traefik and use our own (requires coordination)

3. **Docker Networking**: Our application's databases (PostgreSQL and Redis) are configured to use internal Docker networking only - they are NOT exposed to the host, so they don't need firewall rules. Only databases from other containers that are exposed need firewall protection.

4. **Adding New Database Ports**: If you add new database containers with exposed ports, update the `DB_PORTS` array in `scripts/configure-firewall.sh` and run the script again.

## Troubleshooting

### Locked out of SSH

If you're locked out:
1. Access the server via console/KVM
2. Disable UFW: `sudo ufw disable`
3. Fix the rules and re-enable

### Check what ports are listening

```bash
sudo netstat -tuln | grep LISTEN
# or
sudo ss -tuln | grep LISTEN
```

### View detailed firewall rules

```bash
sudo ufw status numbered
```

