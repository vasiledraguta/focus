# Focus Blocker

A DNS-based website blocker for macOS that helps you stay productive by blocking distracting sites (YouTube, X, Reddit, Instagram, TikTok, etc.) outside of allowed hours.

## How It Works

- Runs a local DNS server on `127.0.0.1:53`
- Blocks configured domains by returning `0.0.0.0` (IPv4) and `::` (IPv6)
- Allows access during a configurable time window (default: 8pm–10pm)
- Can be installed as a startup daemon to run automatically on boot

## Requirements

- macOS
- Python 3.11+
- Miniconda/Anaconda (recommended)

## Setup

### 1. Create conda environment

```bash
cd /path/to/focus
conda create -n focus python=3.11 -y
conda activate focus
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the blocker

```bash
sudo python main.py start
```

### 4. Configure your Mac to use the blocker

Set your DNS to `127.0.0.1`:

```bash
sudo networksetup -setdnsservers Wi-Fi 127.0.0.1
```

Flush DNS cache:

```bash
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

## Commands

| Command | Description |
|---------|-------------|
| `sudo python main.py start` | Run the DNS server (foreground) |
| `sudo python main.py status` | Show blocking status |
| `sudo python main.py install` | Install as startup daemon |
| `sudo python main.py uninstall` | Remove startup daemon + reset DNS |

## Configuration

Edit `config.py` to customize:

- **BLOCKED_DOMAINS**: List of domains to block
- **ALLOWED_START_HOUR**: Hour when blocking stops (default: 20 = 8pm)
- **ALLOWED_END_HOUR**: Hour when blocking resumes (default: 22 = 10pm)

## Installing as Startup Daemon

To have Focus Blocker run automatically on boot:

```bash
conda activate focus
sudo $(which python) main.py install
sudo networksetup -setdnsservers Wi-Fi 127.0.0.1
```

## Uninstalling

```bash
sudo python main.py uninstall
```

This will:
- Remove the startup daemon
- Reset your DNS settings to default

## Troubleshooting

### Sites still loading (slowly)

Your Mac may have multiple DNS servers configured. Ensure `127.0.0.1` is the **only** DNS server:

```bash
sudo networksetup -setdnsservers Wi-Fi 127.0.0.1
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

### Lost internet after stopping the script

Reset DNS to default:

```bash
sudo networksetup -setdnsservers Wi-Fi Empty
```