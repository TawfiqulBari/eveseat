#!/bin/bash
# Firewall configuration script for EVE Online App
# This script configures UFW to:
# - Allow SSH (22), HTTP (80), HTTPS (443) from anywhere
# - Restrict database ports to only 217.216.111.194

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Configuring firewall rules...${NC}"

# Reset UFW to defaults (be careful in production!)
# Uncomment the next line only if you want to reset everything
# sudo ufw --force reset

# Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH, HTTP, HTTPS from anywhere
echo -e "${YELLOW}Allowing SSH (22), HTTP (80), HTTPS (443) from anywhere...${NC}"
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Database ports to restrict (add all database ports found on the host)
DB_PORTS=(
    "5432"   # PostgreSQL default
    "5433"   # PostgreSQL alternate
    "6379"   # Redis default
    "15432"  # Salesapp PostgreSQL
    "15379"  # Salesapp Redis
    "3306"   # MySQL default
    "27017"  # MongoDB default
)

ALLOWED_IP="217.216.111.194"

echo -e "${YELLOW}Restricting database ports to ${ALLOWED_IP}...${NC}"
for port in "${DB_PORTS[@]}"; do
    # Delete existing rules for this port if any
    sudo ufw delete allow $port/tcp 2>/dev/null || true
    # Allow only from specific IP
    sudo ufw allow from $ALLOWED_IP to any port $port proto tcp comment "Database port $port from $ALLOWED_IP"
    echo -e "${GREEN}  ✓ Port $port restricted to $ALLOWED_IP${NC}"
done

# Enable UFW
echo -e "${YELLOW}Enabling UFW...${NC}"
sudo ufw --force enable

# Show status
echo -e "${GREEN}Firewall configuration complete!${NC}"
echo -e "${YELLOW}Current firewall status:${NC}"
sudo ufw status verbose

echo -e "${GREEN}Firewall rules configured successfully!${NC}"
echo -e "${YELLOW}Note: Make sure you have SSH access before running this script!${NC}"

