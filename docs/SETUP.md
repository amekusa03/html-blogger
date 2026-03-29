# Google Cloud & Blogger API Setup Guide

⚠️ **This setup is optional** — It is recommended to first complete the operation check in [QUICKSTART.md](QUICKSTART.md) before proceeding with Google Cloud configuration.

## Overview

This document explains the steps to set up the Google Cloud project and Blogger API v3 required to use HTMLtoBlogger.

## Prerequisites

- Google account (@gmail.com)
- A Blogger blog to post to (you must have posting permissions)
- Internet connection

## Step 1: Create a Google Cloud Project

### 1.1 Access Google Cloud Console

```
https://console.cloud.google.com
```

Open the above URL in your browser and log in with your Google account.

### 1.2 Create a New Project

1. Click “Select a project” at the top of the page  
2. Click the “New Project” button  
3. Enter the following:  
   - **Project name**: `HTMLtoBlogger` (any name is fine)  
   - **Organization**: Leave as default  
4. Click “Create”

### 1.3 Select the Project

Once creation is complete, it will automatically switch to the new project.

## Step 2: Enable Blogger API v3

### 2.1 Open API Library

From the left navigation menu:
```
APIs & Services → Library
```

### 2.2 Search and Enable Blogger API

1. Enter “Blogger API” in the search box  
2. Select “Blogger API v3” from the results  
3. Click the “Enable” button  
4. Wait for activation to complete (a few seconds)

## Step 3: Configure OAuth 2.0 Credentials

### 3.1 Set Up OAuth Consent Screen

1. From the left menu:
   ```
   APIs & Services → OAuth consent screen
   ```

2. Select “External” as **User Type**  
3. Click “Create”

### 3.2 Enter OAuth Consent Screen Details

**Required fields:**

| Field | Input | Example |
|------|------|--------|
| **App name** | Application name | `HTMLtoBlogger` |
| **User support email** | Support email address | `your-email@gmail.com` |
| **Developer contact information** | Your email address | `your-email@gmail.com` |

4. Click “Save and Continue”

### 3.3 Set Scopes (Optional)

- Click “Save and Continue” with default settings  
- Click “Save and Continue” again on the next page  

### 3.4 Add Test Users

1. In the “Test users” section, click “+ Add Users”  
2. Enter your Google email address  
3. Click “Add”  
4. Click “Save and Continue”

## Step 4: Create Desktop App Credentials

### 4.1 Go to Credentials Page

```
APIs & Services → Credentials
```

### 4.2 Create OAuth Client ID

1. Click “+ Create Credentials”  
2. Select “OAuth client ID” from the dropdown  
3. Configure as follows:  
   - **Application type**: Select “Desktop app”  
   - **Name**: `HTMLtoBlogger Desktop` (any name is fine)  
4. Click “Create”

### 4.3 Download Credentials

1. After creation, click the download button (↓ icon)  
2. A JSON file will be downloaded automatically  
3. Rename the file to `credentials.json`  
4. Place it in the `data/` folder  

```
htmltobrogger/
├─ html_tobrogger.py
├─ data/
│   ├─ credentials.json  ← place here
│   ├─ backup/
│   ├─ history/
│   ├─ log/
│   ├─ logs/
│   ├─ media_man/
│   ├─ report/
│   ├─ serialization/
│   ├─ upload/
│   └─ work/
```

## Step 5: Get Blogger Blog Information

### 5.1 Check Blog ID

1. Access the Blogger dashboard: https://www.blogger.com  
2. Select your target blog  
3. Check the browser URL:
   ```
   https://www.blogger.com/blog/posts/{BLOG_ID}
   ```
   Note down the number in `{BLOG_ID}`

### 5.2 Set Blog ID

A setup wizard will appear on first launch, so manual configuration is not required.  
To configure manually, edit the `upload_art` section in `data/config.json5`:

```json5
upload_art: {
  blog_id: 1234567890123456789,
}
```

## Step 6: Initial Authentication Flow

### 6.1 Launch the Application

```bash
python html_tobrogger.py
```

### 6.2 First-Time Authentication

1. When attempting upload, a browser will open automatically  
2. A Google account selection screen will appear  
3. You will be asked to grant access to the “HTMLtoBlogger” app  
4. Click “Allow”

### 6.3 Automatic Token Storage

1. After authentication, `data/token.pickle` will be generated automatically  
2. This file stores the authentication token  
3. It will be used automatically in subsequent runs  

⚠️ **Note**: `token.pickle` is a secret file. Do not publish it on GitHub. It is excluded via `.gitignore`.

## Step 7: Token Refresh

Authentication tokens expire after a certain period. In that case:

1. They will be refreshed automatically during the next upload  
2. You may be asked to authenticate again in the browser  
3. Repeat steps 6.2–6.3  

## Troubleshooting

### Q: “No module named google” error

A: Install dependencies:
```bash
pip install -r requirements.txt
```

### Q: “403 Permission Denied” error

A: Check the following:
1. `credentials.json` is placed in the `data/` folder  
2. Blogger API v3 is enabled in Google Cloud  
3. Your email is added as a test user  

### Q: token.pickle is not generated

A: Check:
1. `credentials.json` format is correct  
2. Internet connection is available  
3. Google Cloud quota limits are not exceeded  

### Q: Browser does not open automatically

A: Try:
1. Copy the URL from the terminal output and open it manually  
2. Check system browser settings  
3. If using Windows Subsystem for Linux (WSL), check `xdg-open` settings  

## Security Notes

⚠️ **Never do the following:**
- ❌ Commit `credentials.json` to public repositories like GitHub  
- ❌ Share `credentials.json` or `token.pickle` with others  
- ❌ Send these files via email  

✅ **Recommendations:**
- Ensure these files are included in `.gitignore`  
- Periodically delete unnecessary credentials (from Google Cloud Console)  
- If using multiple Google Cloud projects, keep them separated  

## API Quotas

Google Blogger API has **two types of request limits**:

### 📏 1. Daily Limit

- **Per user**: 1,000,000 calls per day  
- **Per project**: 2,000,000 calls per day  
- **Reset time**: Midnight Pacific Time (PT) (~16:00–17:00 JST)  
- **Recommended posts via API**: 45 per day  
  (`max_posts_per_run: 45` in config.json5)

### ⚡ 2. Rate Limit

- **QPS (Queries Per Second)**: ~1 request per second  
- **Per 100 seconds**: Up to 1,000 requests  
- **Counting method**: Sliding window  

⚠️ **Account lock causes:**
- Rate limits are stricter than daily limits  
- Sending many requests in a short time may trigger anomaly detection and temporarily suspend your account  

✅ **Tool safety design:**
- Default: **11.1-second interval** (~0.09 QPS)  
- Per run: **Max 45 posts**  
- Compliant with Blogger API rate limits (1 QPS)  

### Quota Check Steps

You can check usage in Google Cloud Console:

1. Access Google Cloud Console  
   ```
   https://console.cloud.google.com
   ```

2. Select your project  

3. Go to:
   ```
   APIs & Services → Quotas
   ```

4. Filter by Blogger API  

5. Check:
   - `Queries per day`  
   - `Queries per 100 seconds per user`  
   - `Queries per second per user`  

6. **Real-time monitoring (optional)**  
   ```
   APIs & Services → Dashboard → Blogger API
   ```
   - View request counts by time  

### 📊 Usage Estimates

Default usage:

| Runs | Posts | Time | Daily Limit Usage |
|------|------|------|------------------|
| 1 | 5 | ~6 sec | 0.0005% |
| 10 | 50 | ~1 min | 0.005% |
| 100 | 500 | ~9 min | 0.05% |
| 1,000 | 5,000 | ~1.5 hr | 0.5% |

**Note**: These are maximum values. Actual posts may be fewer due to skips or errors.

### 🛡️ Safe Upload Practices

1. **Test small**: Start with `MAX_POSTS_PER_RUN = 1`  
2. **Adjust delay**: If errors occur, set `DELAY_SECONDS = 2`  
3. **Distribute runs**: Split large uploads  
4. **Monitor usage**: Check regularly in Google Cloud Console  

## Reset Instructions

If issues occur:

### Reset Credentials

1. Delete:
   ```bash
   rm data/token.pickle
   ```

2. Optionally delete old OAuth credentials in Google Cloud Console  

3. Restart the app to rerun authentication  

### Reset Entire Project

1. Delete the project in Google Cloud Console  
2. Repeat from Step 1  

## Support

If issues occur:

1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)  
2. Refer to Google Cloud documentation: https://cloud.google.com/docs  
3. Check Blogger API reference: https://developers.google.com/blogger  

---

**Last updated**: February 23, 2026