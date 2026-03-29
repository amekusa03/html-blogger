# Troubleshooting Guide

⚠️ **This document is for troubleshooting the development version** – functionality has not been fully verified yet.

If your issue is not resolved by this document, please try the following:
1. Search for known issues on [GitHub Issues](https://github.com/amekusa03/html-blogger/issues)
2. Create a new issue and report it to the development team

This guide summarizes common problems and solutions when using HTMLtoBlogger.

## Common Issues

### 1. Installation & Setup

#### Q: I get a `ModuleNotFoundError: No module named 'xxx'` error

**Cause**: Required Python packages are not installed

**Solution**:
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install packages
pip install -r requirements.txt

# Check versions (optional)
pip list
```

---

#### Q: `command not found: python3` or `python: command not found`

**Cause**: Python is not installed or not set in PATH

**Solution**:

**Linux/Mac:**
```bash
# Check Python installation
python3 --version

# If not installed
brew install python3  # Mac
# or
apt-get install python3 python3-venv  # Ubuntu/Debian
```

**Windows:**
1. Download from [python.org](https://www.python.org/downloads/)
2. Check “Add Python to PATH” during installation
3. Restart Command Prompt after installation

---

#### Q: Virtual environment won’t activate

**Cause**: Virtual environment was not created properly

**Solution**:
```bash
# Remove existing virtual environment
rm -rf venv

# Create a new one
python3 -m venv venv

# Activate
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Confirm ((venv) should appear in prompt)
```

---

### 2. Google Authentication

#### Q: `FileNotFoundError: credentials.json not found`

**Cause**: `credentials.json` is not placed in the project folder

**Solution**:
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Download OAuth Client ID from “APIs & Services” → “Credentials”
3. Rename the downloaded file to `credentials.json`
4. Place it in the `data/` folder

📝 **Details**: See Step 4 in [SETUP.md](SETUP.md)

---

#### Q: `403 Permission Denied` error

**Cause**: One of the following:
- Blogger API is not enabled
- OAuth consent screen is not configured correctly
- Test user is not added

**Solution**:

1. Check if Blogger API v3 is enabled in Google Cloud Console
   ```
   APIs & Services → Library → Search "Blogger API"
   ```

2. Check OAuth consent screen
   ```
   APIs & Services → OAuth consent screen → Edit
   ```

3. Check if your email is added as a test user
   ```
   APIs & Services → OAuth consent screen → Test users
   ```

📝 **Details**: See Steps 2–4 in [SETUP.md](SETUP.md)

---

#### Q: `token.pickle` is not generated

**Cause**: Initial authentication flow has not completed

**Solution**:
1. Run `python html_tobrogger.py` to launch GUI
2. Click “Next” and proceed to upload stage
3. Complete Google authentication in browser
4. Wait for `token.pickle` to be generated automatically

⚠️ **Note**: Internet connection is required

---

#### Q: I want to reset `token.pickle`

**Solution**:
```bash
# Delete token
rm data/token.pickle

# You will be prompted to re-authenticate next time
```

---

### 3. HTML File Processing

#### Q: HTML files are not processed

**Cause**:
- No HTML files in `reports/` folder
- Files do not have `.html` extension

**Solution**:

1. Check files
```
report/
├── 0205tai/          
│   └── index.html    
├── 0209nori/
│   └── index.html
```

2. About links  
# Ensure image links stay within the report directory

---

#### Q: Keywords are not added

**Cause**: `keywords.xml` not found or incorrectly formatted

**Solution**:

1. Check `data/keywords.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<keywords>
    <Mastkeywords>
        <word>Keyword1</word>
        <word>Keyword2</word>
    </Mastkeywords>
    <Hitkeywords>
        <word>Keyword3</word>
    </Hitkeywords>
</keywords>
```

2. Check `data/location.xml` format
```xml
<?xml version='1.0' encoding='utf-8'?>
<root>
    <location>
        <name>Thailand</name>
        <latitude>15.8700</latitude>
        <longitude>100.9925</longitude>
    </location>
</root>
```

3. Ensure file encoding is UTF-8

---

#### Q: Geotags are not added

**Cause**:
- Region name not included in HTML title or headings
- `location.xml` format incorrect
- OpenStreetMap (Nominatim) cannot recognize the region

**Solution**:

1. Check HTML title
```html
<title>Tourist attractions in Thailand</title>
```

2. Check `data/location.xml`
```xml
<?xml version='1.0' encoding='utf-8'?>
<root>
    <location>
        <name>Thailand</name>
        <latitude>15.8700</latitude>
        <longitude>100.9925</longitude>
    </location>
</root>
```

3. Add location manually  
- Open `data/location.xml` in text editor  
- Add required location data  

4. Verify with OpenStreetMap  
- Search region at https://www.openstreetmap.org/search  
- Add coordinates to `data/location.xml`

---

#### Q: `<georss:point>` tag is removed

**Cause**: Removed during HTML cleaning

**Solution**:
1. Include region name in title (auto re-fetch)
2. Add location manually in `data/location.xml`
3. Re-run processing

---

### 4. Image Processing

#### Q: Images are not uploaded

**Cause**:
- No image files in `image/` folder
- Filename mapping incorrect
- Blogger media manager HTML file missing

**Solution**:

1. Check file structure
```bash
image/
├── 0205taiphoto01.jpg
├── 0205taiphoto02.jpg
└── ...
```

2. Check media manager HTML  
- Blogger → Media → Open file  
- Ensure HTML file was downloaded  

3. Check renaming rules
```
Original: reports/0205tai/photo01.jpg  
Renamed: image/0205taiphoto01.jpg  
```

---

#### Q: EXIF data is not removed

**Cause**: Unsupported image format

**Solution**:
- Supported: JPEG, PNG, GIF only  
- Others are skipped  

---

#### Q: Watermark not displayed

**Cause**:
- Watermark disabled in `config.json5`
- Font not installed

**Solution**:

1. Check `data/config.json5`
```json5
mod_image: {
  watermark_text: 'Sample',
},
```

2. Install fonts (Linux)
```bash
sudo apt-get install fonts-liberation
```

3. Shorten watermark text

---

### 5. Upload Issues

#### Q: Posts are not published

**Cause**:
- BLOG_ID not set
- Invalid credentials
- API quota exceeded

**Solution**:

1. Check BLOG_ID
```bash
# https://www.blogger.com/blog/posts/{BLOG_ID}
```

2. Reset credentials
```bash
rm data/token.pickle
```

3. Check API quota in Google Cloud Console

---

#### Q: `Quota exceeded` error

**Cause**: Blogger API quota reached

**Solution**:
- Retry after 17:00 JST (quota resets)
- Request quota increase

---

#### Q: `Invalid request` error

**Cause**: Incorrect feed format

**Solution**:
1. Check `data/upload/` HTML
2. Open in browser
3. Ensure required tags:
   - `<html>`
   - `<head>`

---

### 6. GUI Issues

#### Q: Clicking buttons does nothing

**Cause**: Background processing

**Solution**:
- Wait for completion
- Check logs

---

#### Q: Window freezes

**Cause**: Heavy processing

**Solution**:
```bash
Ctrl+C
python html_tobrogger.py
```

---

#### Q: Text is garbled

**Cause**: Terminal encoding not UTF-8

**Solution**:

**Linux/Mac:**
```bash
export LANG=ja_JP.UTF-8
python html_tobrogger.py
```

**Windows:**
```powershell
$env:PYTHONIOENCODING = "utf-8"
python html_tobrogger.py
```

---

### 7. Performance Issues

#### Q: Processing is slow

**Cause**:
- Large HTML files
- Many images
- Slow internet
- Nominatim rate limit

**Solution**:
- Split HTML files
- Reduce image resolution
- Improve connection
- Process in batches

---

#### Q: MemoryError

**Cause**: Very large files

**Solution**:
- Split files
- Increase virtual memory
- Close unused processes

---

## Advanced Troubleshooting

### Enable debug logs

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug(f"Debug: {variable}")
logger.error(f"Error: {error}")
```

### Save terminal output

```bash
python html_tobrogger.py > debug.log 2>&1
```

### Validate XML

```bash
xmllint --noout data/keywords.xml
xmllint --noout data/location.xml
```

---

## Need More Help?

1. Search on GitHub Issues  
2. Create a new issue with:
   - OS and version  
   - Python version  
   - Steps to reproduce  
   - Screenshots/logs  

---

**Last updated**: February 23, 2026