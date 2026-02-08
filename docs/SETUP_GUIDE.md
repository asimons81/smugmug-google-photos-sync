# Setup Guide

## Step 1: SmugMug API Credentials

1. Go to [SmugMug API Developer Portal](https://api.smugmug.com/api/developer/apply)
2. Sign in with your SmugMug account
3. Apply for an API key:
   - **Application Name**: SmugMug Google Photos Sync
   - **Type**: Application
   - **Platform**: Desktop
   - **Use**: Personal / Migration
4. Once approved, you'll receive:
   - **API Key** (Consumer Key)
   - **API Secret** (Consumer Secret)
5. Enter these in the app's Settings tab

## Step 2: Google Photos API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the **Photos Library API**:
   - Navigate to APIs & Services > Library
   - Search for "Photos Library API"
   - Click Enable
4. Create OAuth 2.0 credentials:
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: **Desktop app**
   - Name: SmugMug Google Photos Sync
5. Configure the OAuth consent screen:
   - User type: External (or Internal for Workspace)
   - Add scopes:
     - `https://www.googleapis.com/auth/photoslibrary.appendonly`
     - `https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata`
     - (Only if needed) `https://www.googleapis.com/auth/photoslibrary.edit.appcreateddata`
   - Add your Google account as a test user
6. Download or copy:
   - **Client ID**
   - **Client Secret**
7. Enter these in the app's Settings tab

## Step 3: Authentication

### SmugMug
1. Enter API Key and Secret in Settings
2. Click "Authenticate with SmugMug"
3. A browser window opens — authorize the app
4. Copy the verification code
5. Paste it into the dialog box in the app

### Google Photos
1. Enter Client ID and Secret in Settings
2. Click "Authenticate with Google"
3. A browser window opens — sign in and authorize
4. The app automatically receives the token

## Step 4: Start Syncing

1. Go to the **Photo Browser** tab
2. Click the refresh button to load your SmugMug albums
3. Browse albums and select photos with checkboxes
4. Click **Sync Selected** to begin

Or use the **Dashboard** tab:
- **Start Sync** — syncs all photos based on your filter settings
- **Preview (Dry Run)** — shows what would be synced without transferring

## Troubleshooting

### "Connection test failed"
- Verify your API keys are correct
- Check your internet connection
- For Google: ensure Photos Library API is enabled in your project

### "Rate limited"
- The app handles this automatically with exponential backoff
- If persistent, try reducing concurrent uploads in Settings

### "Authentication expired"
- Google tokens refresh automatically
- SmugMug tokens don't expire but may be revoked
- Re-authenticate through Settings if needed

### Photos not appearing
- Click the refresh button in Photo Browser
- Check that your SmugMug account has the correct permissions
- Ensure the API key has "Read" access

## Bandwidth Considerations
- Default: unlimited bandwidth
- Set a limit in Settings > Sync Preferences to avoid saturating your connection
- Recommended: 5-10 MB/s for background syncing
