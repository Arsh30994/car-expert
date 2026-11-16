# Run Car Expert AI V2 on a private LAN

This guide is for a trusted home or college LAN during development. It is not a production deployment recipe.

## 1. Prepare the Windows host

Install Python 3.12+ and Git. Clone the preview branch:

```powershell
git clone --branch v2-internal-preview https://github.com/Arsh30994/car-expert.git
cd car-expert
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks virtual-environment activation, run this once in the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

## 2. Configure environment

Copy `.env.example` to `.env`. Set a unique local `SECRET_KEY`. Add your host PC's private IPv4 address to `ALLOWED_HOSTS`, for example:

```env
DEBUG=true
SECRET_KEY=replace-with-a-long-random-local-secret
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.25
```

Replace `192.168.1.25` with the actual private IPv4 address of the host PC. Add the AI provider key only if you want live AI responses. Never commit `.env`.

The current Django settings already read `ALLOWED_HOSTS` from the environment. Keep `DEBUG=true` only for a trusted local development network.

## 3. Initialize and start

```powershell
python manage.py check
python manage.py migrate
python manage.py test chatbot garage diagnostics
python manage.py runserver 0.0.0.0:8000
```

On the host PC, open `http://127.0.0.1:8000/`.

On another device connected to the same private Wi-Fi/LAN, open `http://192.168.1.25:8000/`, replacing the example address with the host PC's actual IPv4 address.

To find the address on Windows:

```powershell
ipconfig
```

Use the IPv4 Address under the active Wi-Fi or Ethernet adapter.

## 4. Windows Firewall

If another device cannot connect, allow inbound TCP port 8000 on the **Private** network profile only. Do not expose this development server to public networks or the internet.

## 5. Important limitations

- Django's `runserver` is for development, not production or public hosting.
- SQLite is suitable for a single-host demo, but not a multi-user production deployment.
- Keep the host PC awake and connected to the same LAN.
- Uploaded media and the SQLite database live on the host PC.
- Live AI responses require a valid provider API key and internet connectivity.
- Do not use real customer records or sensitive vehicle documents in a shared demo.
- Stop the server with Ctrl+C.
