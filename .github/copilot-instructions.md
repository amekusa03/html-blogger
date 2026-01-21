# Blogger HTML Upload Pipeline - AI Development Guide

## Architecture Overview
This is a **local desktop tool** that converts HTML reports into Blogger-compatible posts with automated image processing. The pipeline consists of 4 sequential stages launched from a Tkinter GUI (`html_tobrogger.py`):

```
reports/ → add_keywords.py → cleaner.py → image_preparer.py → uploader.py
  ↓          ↓                ↓             ↓                   ↓
input       addKeyword_      ready_to_     ready_to_upload_  Blogger
HTML       upload/           upload/       images/           (Google API)
```

## Data Flow & Folder Structure

### Input Stage
- **`reports/`**: Source folder structure `reports/XXXX/index.htm` (one HTML per location folder with photos)
- Each folder named with location code (e.g., `0205tai`, `0209nori`) contains `index.htm` and image files

### Processing Stages
1. **add_keywords.py**: Reads `keywords.xml`, injects `<meta name="keywords">` tags into HTML
2. **cleaner.py**: Extracts title/date/keywords from HTML, removes formatting, outputs to `ready_to_upload/`
3. **image_preparer.py**: Renames images from `old_photos/` using folder name prefix (e.g., `0205tai_photo01.jpg`)
4. **uploader.py**: Uses Google Blogger API v3 to publish posts with resized images

## Critical Implementation Patterns

### HTML Processing (cleaner.py, add_keywords.py)
- **Remove all newlines/tabs first**: `re.sub(r'[\r\n\t]+', '', html)` prevents parsing issues
- **Extract metadata before cleanup**: Title from `<title>` or `<h1-9>`, keywords from `<meta name="keywords">`, dates from `<time datetime="">` tags
- **Meta tag format**: Exact order required: `<meta name="keywords" content="word1,word2">`
- **Regex flags**: Always use `re.IGNORECASE | re.DOTALL` for HTML parsing (accounts for tag variations)

### Image Processing (uploader.py, image_preparer.py)
- **Size mapping logic**: Landscape vs portrait modes map original dimensions to standard widths
  - Landscape: 640×480, 400×300, 320×240, 200×150
  - Portrait: 480×640, 300×400, 240×320, 150×200
- **Image URL replacement**: MediaManager HTML file (`Blogger メディア マネージャー_ddd.html`) contains googleusercontent.com URLs; extract with BeautifulSoup's `find_all('a', href=re.compile(...))`
- **Rename convention**: `{folder_name}{original_filename}` (e.g., `0205tai` folder + `photo01.jpg` = `0205taiphoto01.jpg`)

### Google Blogger API Integration (uploader.py)
- **OAuth flow**: Requires `credentials.json` (Desktop App type from Google Cloud Console)
- **Auth tokens**: Auto-saves as `token.pickle`, refreshes expired tokens
- **Rate limiting**: 15-second delay between posts (set `DELAY_SECONDS = 15`)
- **BLOG_ID required**: Must be configured in script before running

## Key Configuration Files
- **`keywords.xml`**: XML with `<Mastkeywords>` and `<Hitkeywords>` nodes, each with `<word>` children
- **`credentials.json`**: OAuth credentials from Google Cloud (place in project root)
- **`token.pickle`**: Auto-generated after first auth, persists session

## Common Workflows

### Full Pipeline Execution
```bash
# Run from GUI (main entry point)
python html_tobrogger.py
# Buttons launch scripts sequentially; monitor output in text widget

# Or run individually (for debugging)
python add_keywords.py      # Inject keywords
python cleaner.py           # HTML cleanup & metadata extraction
python image_preparer.py    # Image rename/consolidate
python uploader.py          # Upload to Blogger API
```

### Testing Single Stage
- Use intermediate folders: `addKeyword_upload/` (after add_keywords), `ready_to_upload/` (after cleaner)
- Check output before running subsequent stage to isolate issues

## Development Notes

### Unicode/Encoding
- All files use UTF-8 encoding (`# -*- coding: utf8 -*-`)
- Folder names are Japanese location codes (not romanized); filenames use ASCII
- Date parsing uses `unicodedata.normalize('NFKC', html)` for consistent Japanese numeral handling

### Error Handling Patterns
- **XML parsing failures** (add_keywords.py): Return empty lists, skip keyword injection
- **Missing files**: Check with `os.path.exists()` before operations; warn but continue
- **BeautifulSoup HTML parsing**: Use `'html.parser'` engine (not `'lxml'`); handles malformed HTML gracefully

### GUI Architecture
- Single-threaded Tkinter with `subprocess.Popen()` to launch child processes
- Output captured via `process.stdout.read()` in non-blocking loop (10ms polling)
- No inter-process communication; relies on folder state (input/output folders)

## Common Pitfalls
1. **Keywords not injecting**: XML malformed or keyword nodes named differently than expected
2. **HTML cleaning removes content**: Overly aggressive regex replacement; test on sample HTML first
3. **Image URLs not mapping**: MediaManager HTML format changed; inspect with BeautifulSoup's `prettify()`
4. **Upload fails silently**: BLOG_ID not set, credentials invalid, or rate limit hit
5. **Date extraction fails**: Unicode normalization needed before regex; test with specific Japanese date patterns
