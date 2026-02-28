# WITTGrp Download Manager

A modern, high-performance, multi-threaded download manager written in PyQt6 and Python. Built with thread-safety and dynamic video streaming support in mind, capable of replacing standard browser downloaders with faster, chunk-based acceleration.

## 🚀 Features

- **Multi-Threaded Acceleration**: Splits files into multiple 4KB chunks and downloads them simultaneously using up to 16 connections for maximum bandwidth utilization.
- **Dynamic Video Extraction**: Integrates `yt-dlp` natively to extract direct raw video and audio streams from YouTube, Vimeo, and other DASH/HLS streaming sites.
- **Safe Re-Entrant Architecture**: Architected with advanced Re-Entrant Locks (`threading.RLock`) bounding the PyQt event loop to the background downloader threads to ensure the UI stays buttery smooth at 50,000+ calculations per second.
- **Smart Pause & Resume**: Safely pause downloads mid-chunk and resume them without data corruption.
- **Browser Integration**: Includes an extension server and native Chrome/Edge/Brave/Opera browser extensions to automatically inject "Download" buttons directly onto website video players.
- **Auto-Categorization**: Automatically sorts downloaded files into `Videos`, `Music`, `Documents`, `Programs`, or `Archives` based on their extension.

## 📦 Requirements

- Python 3.10+
- `PyQt6`
- `requests`
- `yt-dlp`

## ⚙️ Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/sharmarajeshkr/Downloadmanager.git
   cd Downloadmanager
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python main.py
   ```
   Or use the included batch file:
   ```bash
   Launch_WITTGrp.bat
   ```

## 🔌 Browser Extension Setup

To enable the "Download with WITTGrp" button natively in your browser:

1. Open your browser's extension manager (`chrome://extensions/` or `edge://extensions/`).
2. Turn on **Developer Mode**.
3. Click **Load Unpacked**.
4. Select the `browser_extension/chrome` (or your respective browser) folder inside this repository.

## 📄 Architecture Notes
WITTGrp prevents classic Python GIL deadlocks during concurrent signaling by carefully throttling the `pyqtSignal` event emissions down to a maximum of 5 frames per second within its windowed interval chunks, separating calculation threads entirely from the UI renderer.

---
*Created by the WITTGrp Development Team*
