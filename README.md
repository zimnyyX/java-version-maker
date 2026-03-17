# Minecraft Java Port Launcher

A portable Minecraft launcher system designed for use on PCs where Minecraft or Java might not be installed (e.g., school PCs).

## Features
- **Main Launcher**: Allows selecting and downloading any Minecraft version.
- **Sub-Launcher**: Bundled with each downloaded version, allows independent launching.
- **Offline Mode**: Play without a Microsoft account (local username only).
- **Online Mode**: Secure Microsoft Authentication via device code.
- **Portable JRE**: Option to download and include a local Java Runtime Environment (JRE) so Minecraft can run without a system-wide Java installation.

## How to Use
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the Main Launcher:
   ```bash
   python "Java port/main_launcher.py"
   ```
3. Select a version and click "Download & Launch".
4. Once downloaded, a folder named after the version will be created. This folder contains the full game and the `sub_launcher.py`.
5. You can zip this version folder and take it anywhere!

## Creating Executables (.exe)
To create `.exe` files for Windows, you can use `PyInstaller`:

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Build the Main Launcher:
   ```bash
   pyinstaller --noconsole --onefile "Java port/main_launcher.py"
   ```
3. Build the Sub-Launcher:
   ```bash
   pyinstaller --noconsole --onefile "Java port/sub_launcher.py"
   ```
   *Note: When distributing a version folder, make sure the `sub_launcher.exe` is inside that folder.*

## Directory Structure
- `Java port/`
  - `main_launcher.py`: The primary interface for downloading versions.
  - `sub_launcher.py`: The script that gets copied into each version folder.
  - `1.18.2/` (Example version folder)
    - `versions/`, `assets/`, `libraries/`: Minecraft game files.
    - `runtime/`: Local JRE (if selected).
    - `sub_launcher.py`: Copy of the sub-launcher for this specific version.
