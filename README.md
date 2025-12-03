# LocalServers 🌐

**Menubar app to monitor local development servers and tunnels**

![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)
![Python](https://img.shields.io/badge/python-3.14-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

✨ **Auto-detect local servers**
- Scans all listening TCP ports (>1000)
- Identifies server type (Next.js, Node.js, Python, etc.)
- Click to open in browser
- Updates every 5 seconds

🚇 **Detect active tunnels**
- Cloudflare tunnels
- Tailscale Funnel
- ngrok
- Custom integrations (Warelay)

🎯 **Zero configuration**
- Works out of the box
- No setup required
- Compatible with any project

## Installation

### Option 1: Run directly (Development)

```bash
cd ~/Projects/LocalServers
python3 local_servers.py
```

### Option 2: Install as macOS app

```bash
pip3 install py2app --break-system-packages
python3 setup.py py2app
open dist/LocalServers.app
```

## Usage

1. **Run the app** - Icon appears in menubar: 🌐
2. **Click icon** - See all running servers and tunnels
3. **Click server** - Opens localhost:PORT in browser
4. **Auto-updates** - Refreshes every 5 seconds

## Menu Example

```
🌐 3
├─ 📡 Servers Running (3)
│  ├─ localhost:3000 (Next.js)
│  ├─ localhost:3001 (Next.js)
│  └─ localhost:4020 (VibeTunnel)
├─ 🚇 Tunnels Active (2)
│  ├─ → Cloudflare: audio.medigui.app
│  └─ → Tailscale Funnel: mac-mini.tail*.ts.net
└─ Refresh
```

## Requirements

- macOS 10.14+
- Python 3.8+
- rumps (`pip3 install rumps`)

## How it works

**Server detection:**
- Uses `lsof -iTCP -sTCP:LISTEN` to find listening ports
- Filters ports >1000 to exclude system services
- Identifies server type by process name and port

**Tunnel detection:**
- Scans running processes with `ps aux`
- Looks for cloudflared, tailscale, ngrok, etc.
- Extracts configuration from config files

## Development

```bash
# Install dependencies
pip3 install rumps pyobjc --break-system-packages

# Run
python3 local_servers.py

# Build standalone app
python3 setup.py py2app
```

## License

MIT

## Author

Created by [@ignaciogonzalezbautista](https://github.com/ignaciogonzalezbautista)

---

**Made with ❤️ for developers who run too many servers**
