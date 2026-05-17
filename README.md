<h1 align="center">BigLinux Browser Selector</h1>
<img width="1050" height="830" alt="image" src="https://github.com/user-attachments/assets/d8c7452c-f876-4a03-9544-58e5e8af78f0" />

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#project-structure">Project Structure</a> •
  <a href="#contributing">Contributing</a> •
  <a href="#license">License</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/GTK-4-blue?logo=gnome&logoColor=white" alt="GTK4">
  <img src="https://img.shields.io/badge/Python-3.10%2B-yellow?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Adwaita-libadwaita-purple" alt="Adwaita">
  <img src="https://img.shields.io/badge/license-GPL-green" alt="License GPL">
</p>

---

## About

**BigLinux Browser Selector** is a modern, GTK4-based application for [BigLinux](https://www.biglinux.com.br) that allows users to choose and install their preferred web browser with an intuitive interface. It features real-time installation progress, integrated installer support, and accessibility for screen readers.

## Features

- **Modern GTK4/libadwaita interface** — Clean, native look and feel
- **Browser selection & install** — Choose from 10 supported browsers; install missing ones with real-time progress display
- **Real-time installation feedback** — Live log output during browser installation
- **Set default browser** — Configure your chosen browser as the system default
- **Accessibility support** — Screen reader compatible with ARIA roles and focus indicators
- **Multiple installation sources** — Supports both native packages and Flatpak installations

## Installation

### From BigLinux repositories (recommended)

```bash
sudo pacman -S biglinux-browser-selector
```

### Manual build (Arch-based distros)

```bash
cd pkgbuild
makepkg -si
```

### Dependencies

| Package        | Purpose                    |
|----------------|----------------------------|
| `gtk4`         | UI toolkit                 |
| `python`       | Runtime (≥ 3.10)           |
| `python-yaml`  | YAML page configuration    |
| `python-gobject`| GTK4 Python bindings      |
| `polkit`       | Privilege elevation        |
| `zenity`       | Auxiliary dialogs          |

## Project Structure

```
biglinux-browser-selector/
├── usr/
│   ├── bin/
│   │   └── biglinux-browser-selector     # launcher script
│   ├── share/
│   │   ├── applications/
│   │   │   └── org.biglinux.browser-selector.desktop
│   │   ├── browser_selector/
│   │   │   ├── main.py                   # entry point
│   │   │   ├── app.py                    # Adw.Application + CSS
│   │   │   ├── window.py                 # main window & browser logic
│   │   │   ├── widgets.py                # custom GTK4 widgets (BrowserCard, InstallPanel)
│   │   │   ├── utils.py                  # shared utilities
│   │   │   ├── style.css                 # Adwaita-based styles
│   │   │   ├── pages.yaml                # browser configuration
│   │   │   └── scripts/
│   │   │       ├── browser.sh            # browser management script
│   │   │       └── browserInstall.sh     # installation script (runs as root)
│   │   └── icons/hicolor/scalable/apps/
│   │       └── biglinux-browser-selector.svg
├── pkgbuild/
│   ├── PKGBUILD                          # Arch package build
├── README.md
└── LICENSE
```

## Supported Browsers

- Brave
- Chromium
- Chrome (Google)
- Falkon
- Firefox
- Librewolf
- Opera
- Vivaldi
- Edge (Microsoft)
- Zen Browser

Each browser supports both native package installation and Flatpak variants where available.

## Development

### Running locally

```bash
cd usr/share/biglinux/browser_selector
python main.py
```

### Code quality

```bash
pip install ruff
ruff check usr/share/biglinux/browser_selector/
ruff format usr/share/biglinux/browser_selector/
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests and code quality checks
5. Commit and push
6. Open a Pull Request

## Community

- 🌐 **Website:** [biglinux.com.br](https://www.biglinux.com.br)
- 💬 **Forum:** [forum.biglinux.com.br](https://forum.biglinux.com.br)
- 📺 **YouTube:** [@BigLinuxx](https://www.youtube.com/@BigLinuxx)
- ✈️ **Telegram:** [t.me/biglinux](https://t.me/biglinux)
- ❤️ **Donate:** [biglinux.com.br/doacao-financeira](https://www.biglinux.com.br/doacao-financeira/)

## License

This project is licensed under the **GPL** license. See the [PKGBUILD](pkgbuild/PKGBUILD) for details.
