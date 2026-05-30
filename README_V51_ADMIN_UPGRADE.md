# APEX v5.1 Admin Panel Upgrade

Upload/merge these files into your GitHub repo, then on Google VM run:

```bash
cd /opt/apex-v4/apex_v4_binance
git pull
docker compose down
docker compose up -d --build
```

Open:

```text
http://34.24.22.108:8000/admin
```

## Included

- `/admin` web admin panel
- `/api/admin/status`
- `/api/admin/bot/start`
- `/api/admin/bot/stop`
- `/api/admin/exchanges`
- `/api/admin/ai`
- `/api/admin/risk`
- Database models for admin settings and exchange credentials

## Security note

This MVP uses lightweight reversible secret storage with `APEX_SECRET_KEY`.
Before live/paid SaaS release, move secrets to Google Secret Manager or KMS-backed encryption.
