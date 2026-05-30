#!/bin/bash
set -e
cd /opt/apex-v4/apex_v4_binance
sudo chown -R $(whoami):$(id -gn) .
sudo chmod -R u+rwX .
python3 -m py_compile app/admin/service.py app/admin/routes.py app/admin/web.py app/dashboard/web.py app/main.py

git add .
git commit -m "Fix v5.2 admin services and modern dashboard" || true
git push origin main || true

docker compose down
docker compose up -d --build
docker compose ps
docker compose logs --tail=80
