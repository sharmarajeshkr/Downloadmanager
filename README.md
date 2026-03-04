# WITTGrp Download Manager

A modern, high-performance download manager featuring Intelligent Dynamic File Segmentation, native desktop UI, and seamless browser integration.

## Features
- **V2 Dynamic Engine**: Accelerates downloads by dynamically splitting active chunks in half (similar to IDM) using HTTP Keep-Alive connection reuse.
- **Modern UI**: Dark-themed, frameless window design with SVG iconography and a sleek "Add Download" dialog.
- **Auto-Categorization**: Automatically saves files into designated user-profile folders (`Downloads/WITTGrp/Videos`, `Music`, `Documents`, etc.) based on file extensions.
- **Browser Interception**: Catches downloads instantly from the browser before the native "Save As..." popup can appear, routing them directly into the desktop app.

---

## Installation (Executable Version)

If you have already compiled the `.exe` (or received one), no Python installation is required.

1. Locate the standalone executable in the `dist/` folder (e.g., `dist/WITTGrp.exe`).
2. Double-click to run. The app will launch directly.
3. Keep the app open (or minimized to the system tray) when browsing to enable download interception.

---

## Installation (From Source)

To run or build the application from the Python source code:

### 1. Prerequisites
- Python 3.10 or higher.

### 2. Install Dependencies
Open your terminal or command prompt in the `idm` folder and run:
```bash
pip install -r requirements.txt
```

*(Note: If `requirements.txt` is missing, the core dependencies are `PyQt6`, `requests`, and `yt-dlp`)*

### 3. Run the App
Launch the desktop application directly:
```bash
python main.py
```

---

## Compiling Your Own Executable

You can compile the Python code into a standalone, single-file application for your specific operating system (Windows `.exe`, macOS `.app`, Linux binary).

1. Open a terminal in the project directory.
2. Run the build script:
   ```bash
   python build.py
   ```
3. PyInstaller will package the application, the UI assets, and the browser extensions.
4. Your native standalone executable will appear in the `dist/` folder.

> **Note on Cross-Compilation:** Python cannot cross-compile. To build a Mac application, run `build.py` on a Mac machine. To build a Windows `.exe`, run `build.py` on a Windows machine.

---

## Browser Integration (Installing the Extensions)

WITTGrp includes custom browser extensions for **Google Chrome**, **Microsoft Edge**, and **Opera** to automatically intercept native downloads and video streams. 

Since these extensions are not published on the Web Stores, they must be loaded manually via "Developer Mode".

### Option 1: Chrome / Brave / Other Chromium Browsers
1. Open Chrome and navigate to `chrome://extensions/`
2. **Turn ON** "Developer mode" (toggle switch usually in the top-right corner).
3. Click **"Load unpacked"** (top-left).
4. Navigate to your project folder: `idm/browser_extension/chrome/` and select that folder.
5. The WITTGrp extension should now appear and will immediately begin intercepting standard downloads while the desktop app is running.

### Option 2: Microsoft Edge
1. Open Edge and navigate to `edge://extensions/`
2. At the bottom left, **Turn ON** "Developer mode" and "Allow extensions from other stores".
3. Click **"Load unpacked"** (top-right).
4. Navigate to: `idm/browser_extension/edge/` and select that folder.

### Option 3: Opera
1. Open Opera and navigate to `opera://extensions/`
2. In the top right corner, **Turn ON** "Developer mode".
3. Click **"Load unpacked"**.
4. Navigate to: `idm/browser_extension/opera/` and select that folder.

---

## How it Works Together

1. **Start WITTGrp Desktop**: The desktop application runs a lightweight background server on port `9614`.
2. **Browse the Web**: The browser extension silently monitors for video streams and typical file downloads (e.g., clicking on a `.pdf` or `.mp4` link).
3. **Interception**: The moment you click a download link, the extension forces Chrome to instantly cancel its native download process, pulling the URL, Referer, and Cookies.
4. **Handoff**: The extension sends that data to the desktop app (port 9614), popping open the custom "Add Download" dialog automatically pre-filled with the exact save path and category.
