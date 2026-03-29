# HTML to Blogger

Get up and running with HTML to Blogger in just 5 minutes.

## ⚡ Quick Start (5 Minutes)

### Step 1: Clone the Repository
```bash
git clone https://github.com/amekusa03/html-blogger.git
cd html-blogger
```

### Step 2: Create a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Place Google Cloud Credentials File
Follow Step 4 in [SETUP.md](docs/SETUP.md) and copy `credentials.json` into the `data/` folder.

### Step 5: Launch the Application
```bash
python html_tobrogger.py
```

🖥️ **A GUI window will launch.** 

⚠️ **Startup Checklist**:
- [ ] GUI window appears
- [ ] “Open Folder” button responds
- [ ] `data/report/` folder opens

---

## 🧪 Initial Test Run (Important!)

**Before using it in production, be sure to test with a small HTML file:**

1. **Prepare a test file**
   ```
   reports/test/
   ├── test.html (small HTML under 100KB)
   └── test_image.jpg (1–2 small images)
   ```

2. **Click each button in order**
   - Check for errors
   - Review log messages

3. **If everything completes successfully, proceed to full use**
   - If issues occur during testing, refer to [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
   - If unresolved, report on [GitHub Issues](https://github.com/amekusa03/html-blogger/issues)

⚠️ **Warning**: Avoid processing large batches of files without testing first. Unexpected behavior may occur.

---

## 📋 Basic Usage

### 1. Prepare HTML Files
```
reports/
├── 0205tai/
│   ├── index.html  ← Place your HTML file here
│   ├── photo01.jpg
│   └── photo02.jpg
```

### 2. Click Buttons in the GUI in Order

```
[Open Folder]
    ↓ Displays reports folder
    
[Start]
    ↓ Executes keywording, geolocation, cleaning, and image processing
    ↓ Check progress in the log window
    
[Upload Images]
    ↓ Manually upload processed images

[Get Image Links]
    ↓ Manually download Blogger media manager info
    ↓ Create image links for the article    
    
[Upload]
    ↓ Starts automatic posting via Google Blogger API
```

### 3. Confirm Completion

```
If it appears as a draft post on your Blogger site, it’s complete.
```

---

## ⚙️ Required Configuration

### 1. Edit `data/config.json5`
```json5
{
    // Image processing settings
    mod_image: {
        watermark_text: 'Sample',     // Watermark text
    },
    // Article upload settings
    upload_art: {
        blog_id: 1234567890123456789,   // Blog ID
    }
}
```

### 2. Edit `data/keywords.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<root>
    <Mastkeywords>
        <word>Keyword1</word>
        <word>Keyword2</word>
    </Mastkeywords>
</root>
```

---

## 🆘 If Things Don’t Work

### ❌ Module errors occur
```bash
pip install -r requirements.txt
```

### ❌ Authentication errors occur
1. Re-read [SETUP.md](docs/SETUP.md)
2. Check that `credentials.json` is correctly placed
3. Ensure Blogger API v3 is enabled in Google Cloud

### ❌ Other issues
Refer to [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

---

## 📚 Detailed Documentation

| Document | Description |
|------------|------|
| [README.md](../README.md) | Project overview and feature list |
| [SETUP.md](SETUP.md) | Detailed Google Cloud API setup |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design and file structure |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Troubleshooting guide |

---

## 💡 Common Issues During Testing

**Q: The GUI launches, but buttons don’t respond**  
A: Check your Python version and ensure the virtual environment is activated. Refer to [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

**Q: An error message appears**  
A: Copy the error message and search for it in [TROUBLESHOOTING.md](TROUBLESHOOTING.md). If not found, report it on [GitHub Issues](https://github.com/amekusa03/html-blogger/issues).

**Q: Processing completes, but no files are generated**  
A: Check the contents of the `data/work/` folder.

---

## 🚀 Next Steps

1. ✅ Handle exception cases  
2. ✅ Convert to data classes and optimize threading  

---

**Last Updated**: February 12, 2026

**Sharing your test results will help improve the project!**