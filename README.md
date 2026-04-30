# HTML to Blogger Ver0.98

A desktop application that automatically processes local HTML files and images and posts them to Blogger.  
It performs HTML cleaning, adds watermarks to images, assigns keywords and location information, and uploads to Blogger.

## Qiita Article

[Explanation article for this tool (Qiita)](https://qiita.com/amekusa03/items/b8ac77cd3dd6e6cc65aa)

## Introduction Video

[![Introduction Video](https://img.youtube.com/vi/gFgYCVHIfW0/maxresdefault.jpg)](https://youtu.be/gFgYCVHIfW0?si=fby7oARRbfOy2K4K)

## Main Features

* **HTML Cleaning**: Removes unnecessary tags and normalizes formatting for posts.  
* **Image Processing**: Removes EXIF data and adds watermarks.  
* **Metadata Assignment**: Automatically adds keywords (`search` tags) and location information (`georss` tags) by analyzing the article content.  
* **Blogger Upload**: Uploads image links and articles as drafts using the Blogger API.  
* **GUI Operation**: User-friendly GUI with progress visualization and error recovery features.  

## Processing Flow

Processing is executed in the following order:

1. **`import_file.py`**: Imports files from the source folder to the working folder.  
2. **`serial_file.py`**: Converts file names into sequential numbering format.  
3. **`clean_html.py`**: Cleans up HTML for Blogger.  
4. **`find_keyword.py`**: Extracts keywords from the article body.  
5. **`find_location.py`**: Extracts place names and assigns location information.  
6. **`find_date.py`**: Parses dates in the article.  
7. **`mod_image.py`**: Processes images (resize, add watermark).  
8. **`upload_image.py`**: Prepares images for upload.  
9. **`import_media_manager.py`**: Cleans up the media manager folder.  
10. **`link_html.py`**: Updates image links in HTML.  
11. **`upload_art.py`**: Uploads the completed article to Blogger.  

## File Structure

### Main Files
* **`html_tobrogger.py`**: Main GUI application  
* **`main_process.py`**: Controls the processing flow  

### Processing Modules
* **`import_file.py`**: File import validation  
* **`serial_file.py`**: Sequential file naming  
* **`clean_html.py`**: HTML cleaning  
* **`find_keyword.py`**: Keyword extraction  
* **`find_location.py`**: Location assignment  
* **`find_date.py`**: Date extraction  
* **`mod_image.py`**: Image processing  
* **`upload_image.py`**: Image preparation  
* **`import_media_manager.py`**: Media manager cleanup  
* **`link_html.py`**: HTML link updates  
* **`upload_art.py`**: Article upload  

### Utilities
* **`file_class.py`**: File management class  
* **`parameter.py`**: Shared constants and configuration loading  
* **`auth_google.py`**: Google authentication processing  
* **`cons_progressber.py`**: Console progress bar display  

### Configuration Files (in the `data/` folder)
* **`config.json5`**: Overall application settings  
* **`log_config.json5`**: Logging configuration  
* **`serial.json5`**: Serial number counter (auto-managed)  
* **`keywords.xml`**: Meta keyword definitions  
* **`location.xml`**: Location information cache (auto-updated)  
* **`credentials.json`**: Google authentication info (must be placed by user, not included in GitHub)  
* **`token.pickle`**: Authentication token (auto-generated)  

### Others
* **`requirements.txt`**: List of required Python packages  
* **`pyproject.toml`**: Project configuration  

## System Requirements

* Python 3.8 or higher  
* Google Cloud Platform (GCP) project with Blogger API enabled  

## Installation

### 1. Place the Source Code
Place the entire toolset in any folder of your choice.

### 2. Install Dependencies
Run the following command to install the required Python libraries.  
Since `requirements.txt` is included, you can install them all at once:

```bash
pip install -r requirements.txt
# or pip install beautifulsoup4 google-api-python-client google-auth-oauthlib google-auth-httplib2 Pillow geopy janome
```

*If you are using Linux (Ubuntu, etc.), you may need to install Tkinter:*
```bash
sudo apt-get install python3-tk
```

## Initial Setup

### 1. Prepare Google API Credentials
1. Access Google Cloud Console and create a project.  
2. Go to "APIs & Services" > "Library", search for **Blogger API v3**, and enable it.  
3. Go to "APIs & Services" > "Credentials" and create an **OAuth 2.0 Client ID** (application type: "Desktop app").  
4. Download the JSON file and save it as **`credentials.json`** in the tool’s data folder.  

### 2. Launch the Application
Run the following command to start the GUI app:

```bash
python3 html_tobrogger.py
```

### 3. Set Blog ID
Save your blog ID in `config.json5`.  
*On first run only, a browser will open prompting you to log in to your Google account and grant permissions (OAuth authentication).*

## Usage

### Basic Workflow

1. **Prepare Files**:
   * Place the HTML files and images you want to post into the `reports` folder.  
   * You can open the folder using the "📄 Reports" button in the GUI.  

2. **Run Processing**:
   * Click the **Run** button at the bottom right of the GUI.  
   * Cleaning → Image processing → Keyword addition → Upload will run sequentially.  

3. **Upload Images**:
   * A guidance dialog will appear and open the processed images folder.  
   * In Blogger, create a new post and paste the images from the folder.  
   * Save the new post as a **draft**.  
   * Once done, click "Run" again in the tool.  

4. **Media Manager Parsing**:
   * A guidance dialog will appear and open the HTML save folder.  
   * Switch the Blogger post screen to "Media Manager" and save it in HTML format into the `media_man` folder.  
   * Save the copied code as a text file (e.g., `blogger.html`) in the save folder.  
   * Click "Run" again in the tool.  
   * The tool will parse image URLs and replace article links with Blogger URLs, then continue processing.  

4. **Article Upload**:
   * The article is automatically posted.  
   * Once completed, it will appear as a draft in Blogger—review it and **publish**.  

## Troubleshooting

* **If an error occurs**:
   * Error details will appear in red in the log window.  
   * If the issue is with the file itself (e.g., unknown character encoding), fix the file and rerun.  

* **To change settings**:
   * You can directly edit `config.json5` or `keywords.xml` from "Edit Settings" in the menu bar.  

## License / Credits

* © OpenStreetMap contributors  
* Follows the licenses of the libraries used  

## 📚 Documentation

- **[Quick Start](docs/QUICKSTART.md)** - Setup in 5 minutes  
- **[Setup Guide](docs/SETUP.md)** - Google Cloud & Blogger API configuration  
- **[Architecture](docs/ARCHITECTURE.md)** - Project structure details  
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions