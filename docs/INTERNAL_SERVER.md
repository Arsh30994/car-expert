# Run Car Expert AI V2 on a private LAN

This guide is for a trusted home or college LAN during development. It is not a production deployment recipe.

## Option A: Docker Desktop (recommended)

Install Docker Desktop and make sure its engine is running. Clone the preview branch:

```powershell
git clone --branch v2-internal-preview https://github.com/Arsh30994/car-expert.git
cd car-expert
Copy-Item .env.example .env
```

Open `.env`, set a unique local `SECRET_KEY`, and add your AI provider key if you want live AI responses. Never commit `.env`.

Find the host PC's private IPv4 address with `ipconfig`. In `.env`, add it to `ALLOWED_HOSTS`, for example:

```env
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.25
```

Replace the example IP with the actual IPv4 address of the active Wi-Fi or Ethernet adapter. Then build and start both containers:

```powershell
docker compose up --build
```

The web container waits for PostgreSQL to become healthy, applies migrations, and starts Django on port 8000. Open `http://127.0.0.1:8000/` on the host PC. Other devices on the same private LAN can open `http://192.168.1.25:8000/`, using the host PC's actual IPv4 address.

Useful Docker commands:

```powershell
# Run in the background
docker compose up --build -d

# Follow Django logs
docker compose logs -f web

# Stop containers (database data remains in its named volume)
docker compose down

# Stop and DELETE the local PostgreSQL data volume
docker compose down -v
```

The PostgreSQL database and uploaded media are stored in Docker named volumes. Do not run `docker compose down -v` unless you intentionally want to erase the local demo database and media.

## Option B: Python virtual environment

Install Python 3.12+ and Git. Clone the preview branch:

```powershell
git clone --branch v2-internal-preview https://github.com/Arsh30994/car-expert.git
cd car-expert
py -3.12 -m venv .venv
.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks virtual-environment activation, run this once in the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\\Scripts\\Activate.ps1
```

Copy `.env.example` to `.env`. Set a unique local `SECRET_KEY`, set `DEBUG=true`, and add your host PC's private IPv4 address to `ALLOWED_HOSTS`. Add the AI provider key only if you want live AI responses. Never commit `.env`.

Initialize, test, and start:

```powershell
python manage.py check
python manage.py migrate
python manage.py test chatbot garage diagnostics
python manage.py runserver 0.0.0.0:8000
```

Open `http://127.0.0.1:8000/` on the host PC or `http://<HOST-PC-IP>:8000/` from another device on the same LAN.

## Windows Firewall

If another device cannot connect, allow inbound TCP port 8000 on the **Private** network profile only. Do not expose this development server to public networks or the internet.

## Important limitations

- Django's `runserver` is for development, not production or public hosting.
- Docker mode uses PostgreSQL; direct Python mode uses the local SQLite database unless `DATABASE_URL` is configured.
- Keep the host PC awake and connected to the same LAN.
- Live AI responses require a valid provider API key and internet connectivity.
- Do not use real customer records or sensitive vehicle documents in a shared demo.
- Stop the Python server with Ctrl+C; stop Docker with `docker compose down`.
