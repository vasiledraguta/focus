# Focus Blocker

A DNS-based website blocker for macOS and Windows that helps you stay productive by blocking distracting sites (YouTube, X, Reddit, Instagram, TikTok, etc.) outside of allowed hours.

## How It Works

- Runs a local DNS server on `127.0.0.1:53`
- Blocks configured domains by returning `0.0.0.0` (IPv4) and `::` (IPv6)
- Allows access during a configurable time window (default: 8pm–10pm)
- Can be installed as a startup service to run automatically on boot

## Requirements

- macOS or Windows
- Python 3.11+

## Setup

### 1. Install dependencies

```bash
cd /path/to/focus
pip install -r requirements.txt
```

### 2. Run the blocker

**macOS:**
```bash
sudo python main.py start
```

**Windows (Administrator Command Prompt):**
```cmd
python main.py start
```

### 3. Configure DNS

**macOS:**
```bash
sudo networksetup -setdnsservers Wi-Fi 127.0.0.1
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

**Windows (Administrator Command Prompt):**
```cmd
netsh interface ip set dns "Wi-Fi" static 127.0.0.1
ipconfig /flushdns
```

## Commands

| Command | macOS | Windows (Admin) |
|---------|-------|-----------------|
| Start server | `sudo python main.py start` | `python main.py start` |
| Show status | `python main.py status` | `python main.py status` |
| Install startup | `sudo python main.py install` | `python main.py install` |
| Uninstall | `sudo python main.py uninstall` | `python main.py uninstall` |

## Configuration

Edit `config.py` to customize:

- **BLOCKED_DOMAINS**: List of domains to block
- **ALLOWED_START_HOUR**: Hour when blocking stops (default: 20 = 8pm)
- **ALLOWED_END_HOUR**: Hour when blocking resumes (default: 22 = 10pm)

## Installing as Startup Service

### macOS

```bash
sudo python main.py install
sudo networksetup -setdnsservers Wi-Fi 127.0.0.1
```

### Windows

Run as Administrator:
```cmd
python main.py install
netsh interface ip set dns "Wi-Fi" static 127.0.0.1
```

## Uninstalling

**macOS:**
```bash
sudo python main.py uninstall
```

**Windows (Administrator):**
```cmd
python main.py uninstall
```

This will:
- Remove the startup service
- Reset your DNS settings to default

## Troubleshooting

### Sites still loading (slowly)

Ensure `127.0.0.1` is the **only** DNS server.

**macOS:**
```bash
sudo networksetup -setdnsservers Wi-Fi 127.0.0.1
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

**Windows:**
```cmd
netsh interface ip set dns "Wi-Fi" static 127.0.0.1
ipconfig /flushdns
```

### Lost internet after stopping the script

Reset DNS to default:

**macOS:**
```bash
sudo networksetup -setdnsservers Wi-Fi Empty
```

**Windows:**
```cmd
netsh interface ip set dns "Wi-Fi" dhcp
```
