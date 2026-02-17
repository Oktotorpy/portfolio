# Connecting a Domain to the Portfolio

## Prerequisites

- Ubuntu VPS with a public IP address
- Domain purchased from a registrar (Namecheap, Cloudflare, GoDaddy, etc.)
- SSH access to the server

## Step 1: Point DNS to Your Server

At your domain registrar, add these DNS records:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | `@` | `YOUR_SERVER_IP` | 300 |
| A | `www` | `YOUR_SERVER_IP` | 300 |

Replace `YOUR_SERVER_IP` with your VPS public IP. You can find it with:

```bash
curl -4 ifconfig.me
```

DNS propagation takes 5 minutes to 48 hours (usually under 30 minutes).

Verify propagation:

```bash
dig +short yourdomain.com
# Should return your server IP
```

## Step 2: Configure the Environment

Edit `/opt/portfolio/.env` on the server:

```bash
nano /opt/portfolio/.env
```

Set these values:

```
DOMAIN=yourdomain.com
CORS_ORIGIN=https://yourdomain.com
```

## Step 3: Enable HTTPS in Caddy

The default `Caddyfile` uses `http://` which disables automatic HTTPS. To enable auto-HTTPS (via Let's Encrypt), remove the `http://` prefix.

Edit the Caddyfile:

```bash
nano /etc/caddy/Caddyfile
```

Change the first line from:

```
http://{$DOMAIN} {
```

To:

```
{$DOMAIN} {
```

Optionally add a `www` redirect block above it:

```
www.{$DOMAIN} {
    redir https://{$DOMAIN}{uri} permanent
}
```

## Step 4: Restart Services

```bash
# Reload Caddy to pick up new domain + obtain TLS certificate
sudo systemctl reload caddy

# Restart backend and frontend with new ORIGIN/CORS settings
sudo systemctl restart portfolio-backend
sudo systemctl restart portfolio-frontend
```

## Step 5: Verify

```bash
# Check Caddy is running and certificate was obtained
sudo systemctl status caddy
sudo journalctl -u caddy --since "5 minutes ago"

# Check the site responds
curl -I https://yourdomain.com
```

Visit `https://yourdomain.com` in your browser. You should see the portfolio with a valid HTTPS certificate.

## Troubleshooting

**Certificate not issued:**
- Ensure port 80 and 443 are open in your firewall: `sudo ufw allow 80 && sudo ufw allow 443`
- Ensure DNS is pointing to the correct IP: `dig +short yourdomain.com`
- Check Caddy logs: `sudo journalctl -u caddy -f`

**"Not authenticated" on admin:**
- Ensure the backend service uses `--preload` flag (check the service file)
- Restart: `sudo systemctl restart portfolio-backend`

**CORS errors:**
- Ensure `CORS_ORIGIN` in `.env` matches your domain exactly, including `https://`
- Restart both services after changing `.env`

**502 Bad Gateway:**
- Backend or frontend crashed. Check logs:
  ```bash
  sudo journalctl -u portfolio-backend -f
  sudo journalctl -u portfolio-frontend -f
  ```

## Firewall Checklist

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (Caddy redirect + ACME challenge)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
sudo ufw status
```
