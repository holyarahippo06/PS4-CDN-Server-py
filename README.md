# PS4 CDN Server py

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A powerful, self-hosted web server that turns your PC into a personal Content Delivery Network (CDN) for your PS4. This tool scans your collection of PKG files (games, updates, DLC, themes), organizes them into a browsable library, and serves them directly to your jailbroken PS4 through the Homebrew (HB) Store.

It features a user-friendly web interface to view your library, manage server settings, and even update the HB-Store's CDN address on your PS4 automatically via FTP.

![Server Screenshot](https://github.com/user-attachments/assets/83402d4c-67b9-43ef-9218-d2710e8783ee) <!-- It's highly recommended to add a screenshot of your web UI here -->

## Key Features

*   **PKG Library Management**: Recursively scans a designated folder for all your `.pkg` files.
*   **Intelligent Metadata Extraction**: Automatically reads `param.sfo` and `icon0.png` from each PKG to extract titles, Title IDs, content IDs, versions, and icons.
*   **Smart Categorization**: Automatically categorizes content into Apps, Games, Patches, DLC, and Themes.
*   **Automatic Patch/DLC Enhancement**: Intelligently associates patches and DLC with their base games, automatically applying the correct title and icon if they are missing.
*   **Paired Theme Handling**: Correctly processes paired theme files (`_1.pkg` and `_2.pkg`), cloning metadata and naming them appropriately.
*   **Web-Based UI**: A clean and modern control panel to view and filter your entire game library.
*   **On-the-Fly Database Generation**: Creates a `store.db` file compatible with the PS4 HB-Store.
*   **PS4 FTP Integration**: Remotely update the CDN URL in your PS4's HB-Store `settings.ini` to point to your server with a single click.
*   **Automatic HB-Store Binary Updates**: Keeps the required HB-Store server binaries (e.g., `homebrew.elf`) up-to-date by fetching the latest releases from the official GitHub repository.
*   **Persistent Configuration**: Saves your folder path and PS4 IP address settings locally, so you don't have to re-enter them every time.

## How It Works

1.  **Scan**: The Python backend (powered by FastAPI) scans the directory you specify. It uses custom PKG parsers to read metadata and icons from each file.
2.  **Process**: It performs post-processing passes to clean up metadata, linking DLC/patches to their base games and handling special cases like themes.
3.  **Format**: The processed package list is formatted into a structure that the HB-Store can understand.
4.  **Build Database**: When you first access the web UI, the server builds a `store.db` SQLite database from your library.
5.  **Serve**: The server hosts the `store.db`, package icons, update binaries, and the PKG files themselves. When the HB-Store on your PS4 points to this server's IP, it will display and allow you to download from your local collection.

## Getting Started

### Prerequisites

*   A jailbroken PS4 with the **HB-Store** installed.
*   An FTP server running on the PS4 (usually included with HEN/GoldHEN).
*   Python 3.8+ installed on your PC.

### Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/holyarahippo06/PS4-CDN-Server-py.git
    cd PS4-CDN-Server-py
    ```

2.  **Set up a Python Virtual Environment:**
    *   On Windows:
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```
    *   On macOS/Linux:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Running the Server

You can run the server using the provided startup scripts. These will activate the virtual environment and start the Uvicorn server.

*   On Windows:
    ```bash
    .\src\start_server.bat
    ```
*   On macOS/Linux:
    ```bash
    chmod +x ./src/start_server.sh
    ./src/start_server.sh
    ```

The server will be accessible at `http://0.0.0.0:8000` by default. Open this address in your web browser.

## Usage

1.  **Initial Configuration:**
    *   Open your web browser and navigate to your PC's local IP address on port 8000 (e.g., `http://192.168.1.10:8000`).
    *   In the "Server Configuration" panel, enter the full path to the folder containing your PKG files (e.g., `D:\PS4\Games`).
    *   Click **"Scan Folder"**. The server will process all your files. This may take some time on the first run.
    *   Once the scan is complete, enter your PS4's IP address and FTP port (usually 2121) in the "HB-Store Management" panel.
    *   Click **"Save Settings"** to store your configuration.

2.  **Pointing Your PS4 to the Server:**
    *   With your PS4's IP entered, click the **"Set My Server as CDN"** button.
    *   This will connect to your PS4 via FTP and automatically change the CDN URL in the HB-Store's `settings.ini` file.
    *   You can use the **"Restore Official CDN"** button to revert this change at any time.

3.  **Accessing Your Library on the PS4:**
    *   Launch the HB-Store on your PS4.
    *   It should now load the library directly from your PC. You can browse and download your games and apps over your local network.

## Contributing

Contributions are welcome! If you have ideas for new features, improvements, or bug fixes, please feel free to:
1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Acknowledgments

*   The developers of the [PS4-Store](https://github.com/LightningMods/PS4-Store) for the Homebrew Store application.
*   The creators of the various PKG parsing libraries that inspired the internal tools.
*   The FastAPI and Uvicorn teams for the excellent web framework.
