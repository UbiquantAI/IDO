# Installation Guide

This guide will help you download and install iDO on your computer.

## System Requirements

### Supported Platforms

- **macOS**: 13 (Ventura) or later
- **Windows**: 10 or later
- **Linux**: Ubuntu 20.04+ or equivalent

### Minimum Hardware

- **CPU**: 64-bit processor (Apple Silicon or Intel)
- **RAM**: 4 GB minimum, 8 GB recommended
- **Disk Space**: 500 MB for application, plus space for activity data
- **Display**: 1280x720 minimum resolution

## Download iDO

### Latest Release

Download the latest version from GitHub:

👉 **[Download iDO Latest Release](https://github.com/UbiquantAI/iDO/releases/latest)**

### Choose Your Platform

#### macOS

- Download `iDO_x.x.x_aarch64.dmg` (Apple Silicon - M1/M2/M3/M4)
- Download `iDO_x.x.x_x64.dmg` (Intel Mac)

#### Windows

- `iDO_x.x.x_x64_en-US.msi` - Windows installer

#### Linux

- `ido_x.x.x_amd64.deb` - Debian/Ubuntu
- `ido-x.x.x-1.x86_64.rpm` - Fedora/RHEL
- `ido_x.x.x_amd64.AppImage` - Universal Linux

## Installation Steps

### macOS

1. **Download** the appropriate `.dmg` file for your Mac
2. **Open** the downloaded `.dmg` file
3. **Drag** iDO to your Applications folder
4. **Launch** iDO from Applications

**First Launch Note**: macOS may show a security warning since the app is downloaded from the internet.

**To allow iDO to run**:

1. Go to **System Settings** → **Privacy & Security**
2. Scroll down to find "iDO was blocked from use"
3. Click **Open Anyway**
4. Confirm by clicking **Open**

**Unsigned build workaround**: If the downloaded build remains blocked after approving it in Privacy & Security, clear the quarantine flag:

```bash
xattr -cr /Applications/iDO.app
codesign -s - -f /Applications/iDO.app
```

### Windows

1. **Download** the `.msi` installer
2. **Double-click** the installer
3. **Follow** the installation wizard
4. **Launch** iDO from the Start Menu

### Linux

#### Debian/Ubuntu (.deb)

```bash
sudo dpkg -i ido_x.x.x_amd64.deb
sudo apt-get install -f  # Install dependencies
```

#### Fedora/RHEL (.rpm)

```bash
sudo rpm -i ido-x.x.x-1.x86_64.rpm
```

#### AppImage (Universal)

```bash
chmod +x ido_x.x.x_amd64.AppImage
./ido_x.x.x_amd64.AppImage
```

## First Run Setup

When you first launch iDO, you'll go through an initial setup wizard with 6 steps:

### 1. Welcome

Get started with iDO and learn about key features.

### 2. Screen Selection

Choose which monitors to capture:

- View all detected displays
- Enable/disable specific monitors
- By default, only the primary monitor is enabled

**Default Settings**:
- **Capture interval**: 0.2 seconds (5 screenshots per second per monitor)
- **Image quality**: 85%
- **Smart deduplication**: Enabled

### 3. LLM Provider Configuration

iDO uses an LLM (Large Language Model) to analyze your activities:

1. Enter your API endpoint and key
2. Select a model (default: gpt-4o-mini)
3. Test the connection

**Supported Providers**:

- OpenAI (GPT-4, GPT-3.5-Turbo)
- Anthropic (Claude)
- Local models (Ollama, LM Studio, etc.)
- Any OpenAI-compatible API

**Privacy Note**: Your API key is stored locally and used only to make LLM requests on your behalf. iDO does not send data to any iDO servers.

### 4. Grant System Permissions

#### macOS Permissions

iDO requires the following permissions:

**Accessibility Permission** (Required)

- Allows iDO to monitor keyboard and mouse events
- Go to **System Settings** → **Privacy & Security** → **Accessibility**
- Enable iDO in the list

**Screen Recording Permission** (Required)

- Allows iDO to capture screenshots
- Go to **System Settings** → **Privacy & Security** → **Screen Recording**
- Enable iDO in the list

The app will guide you through granting these permissions.

### 5. Set Goals (Optional)

Define your focus goals and preferences for AI-generated tasks.

### 6. Complete

You're ready to start using iDO!

## Data Storage

iDO stores all data locally on your device:

- **macOS**: `~/.config/ido/`
- **Windows**: `%APPDATA%\ido\`
- **Linux**: `~/.config/ido/`

This directory contains:

- `ido.db` - SQLite database (activities, events, settings)
- `screenshots/` - Captured screenshots
- `logs/` - Application logs

## Uninstallation

### macOS

1. **Quit** iDO
2. **Drag** iDO from Applications to Trash
3. **Remove data** (optional): Delete `~/.config/ido/`

### Windows

1. **Control Panel** → **Programs** → **Uninstall a program**
2. Select iDO and click **Uninstall**
3. **Remove data** (optional): Delete `%APPDATA%\ido\`

### Linux

```bash
# Debian/Ubuntu
sudo apt remove ido

# Fedora/RHEL
sudo rpm -e ido

# Remove data (optional)
rm -rf ~/.config/ido/
```

## Verify Installation

To verify iDO is working correctly:

1. **Complete the setup wizard**
2. **Grant permissions** when prompted
3. **Configure your LLM** model
4. **Start using your computer** for a few minutes
5. **Navigate to Insights** → **Knowledge** or **Todos**
6. **Check for AI-generated content** from your activities

## Troubleshooting

### App Won't Launch

**macOS**: Check System Settings → Privacy & Security for blocked apps

**Solution**: Click "Open Anyway" as described above

### No Activities Being Captured

**Issue**: Dashboard shows 0 events

**Solutions**:

1. Verify permissions are granted (Accessibility + Screen Recording)
2. Check that at least one monitor is enabled in Settings
3. Restart the app

### LLM Connection Failed

**Issue**: Model test connection fails

**Solutions**:

1. Verify your API key is correct
2. Check your internet connection
3. Verify the model endpoint is accessible
4. Try a different model

### High CPU/Memory Usage

**Issue**: iDO is using too many resources

**Solutions**:

1. Increase capture interval (Settings → 2-5 seconds instead of 0.2)
2. Lower image quality (Settings → 70% instead of 85%)
3. Disable unused monitors
4. Reduce number of monitors

For more troubleshooting help, see the [Troubleshooting Guide](./troubleshooting.md).

## Next Steps

- **[Learn about Features](./features.md)** - Discover what iDO can do
- **[Read FAQ](./faq.md)** - Common questions answered
- **[Get Help](./troubleshooting.md)** - Solve common issues

## Need Help?

- 🐛 **Report Issues**: [GitHub Issues](https://github.com/UbiquantAI/iDO/issues)
- 💬 **Ask Questions**: [GitHub Discussions](https://github.com/UbiquantAI/iDO/discussions)
- 📖 **Documentation**: [Full Docs](../README.md)

---

**Navigation**: [← Back to User Guide](./README.md) • [Next: Features →](./features.md)
