"""SmugMug API client with OAuth 1.0a authentication."""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

import requests
from requests_oauthlib import OAuth1, OAuth1Session

logger = logging.getLogger(__name__)

SMUGMUG_API_BASE = "https://api.smugmug.com"
SMUGMUG_API_VERSION = "/api/v2"
SMUGMUG_REQUEST_TOKEN_URL = "https://api.smugmug.com/services/oauth/1.0a/getRequestToken"
SMUGMUG_AUTHORIZE_URL = "https://api.smugmug.com/services/oauth/1.0a/authorize"
SMUGMUG_ACCESS_TOKEN_URL = "https://api.smugmug.com/services/oauth/1.0a/getAccessToken"
SMUGMUG_UPLOAD_URL = "https://upload.smugmug.com/"


@dataclass
class SmugMugPhoto:
    """Represents a photo from SmugMug."""

    key: str
    uri: str
    title: str
    filename: str
    caption: str
    date_taken: str
    date_uploaded: str
    thumbnail_url: str
    web_url: str
    original_url: str
    size_bytes: int
    width: int
    height: int
    album_name: str = ""
    album_key: str = ""
    keywords: list[str] = field(default_factory=list)
    md5_hash: str = ""

    @property
    def unique_id(self) -> str:
        """Generate a unique identifier for duplicate detection."""
        if self.md5_hash:
            return self.md5_hash
        return hashlib.md5(f"{self.filename}:{self.size_bytes}:{self.date_taken}".encode()).hexdigest()


@dataclass
class SmugMugAlbum:
    """Represents a SmugMug album."""

    key: str
    uri: str
    name: str
    description: str
    image_count: int
    url: str
    date_modified: str


class SmugMugClient:
    """Client for interacting with the SmugMug API using OAuth 1.0a."""

    def __init__(self, api_key: str, api_secret: str,
                 access_token: str = "", token_secret: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.token_secret = token_secret
        self._session: requests.Session | None = None
        self._user_uri: str = ""
        self._rate_limit_remaining = 100

    @property
    def is_authenticated(self) -> bool:
        return bool(self.access_token and self.token_secret)

    def _get_session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            if self.is_authenticated:
                self._session.auth = OAuth1(
                    self.api_key,
                    client_secret=self.api_secret,
                    resource_owner_key=self.access_token,
                    resource_owner_secret=self.token_secret,
                )
            self._session.headers.update({
                "Accept": "application/json",
                "User-Agent": "SmugMugGooglePhotosSync/1.0",
            })
        return self._session

    # --- OAuth Flow ---

    def get_auth_url(self, callback_url: str = "oob") -> tuple[str, str, str]:
        """Start OAuth flow: returns (auth_url, request_token, request_token_secret)."""
        oauth = OAuth1Session(self.api_key, client_secret=self.api_secret,
                              callback_uri=callback_url)
        fetch_response = oauth.fetch_request_token(SMUGMUG_REQUEST_TOKEN_URL)
        request_token = fetch_response["oauth_token"]
        request_token_secret = fetch_response["oauth_token_secret"]

        params = {"oauth_token": request_token, "Access": "Full", "Permissions": "Read"}
        auth_url = f"{SMUGMUG_AUTHORIZE_URL}?{urlencode(params)}"

        logger.info("SmugMug authorization URL generated")
        return auth_url, request_token, request_token_secret

    def complete_auth(self, request_token: str, request_token_secret: str,
                      verifier: str) -> tuple[str, str]:
        """Complete OAuth flow with the verifier code.

        Returns (access_token, access_token_secret).
        """
        oauth = OAuth1Session(
            self.api_key,
            client_secret=self.api_secret,
            resource_owner_key=request_token,
            resource_owner_secret=request_token_secret,
            verifier=verifier,
        )
        tokens = oauth.fetch_access_token(SMUGMUG_ACCESS_TOKEN_URL)
        self.access_token = tokens["oauth_token"]
        self.token_secret = tokens["oauth_token_secret"]
        self._session = None  # Reset session with new creds
        logger.info("SmugMug authentication completed successfully")
        return self.access_token, self.token_secret

    # --- API Methods ---

    def _api_get(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        """Make an authenticated GET request to the SmugMug API."""
        url = f"{SMUGMUG_API_BASE}{endpoint}"
        if params is None:
            params = {}
        params.setdefault("_expand", "")
        params.setdefault("_verbosity", "1")

        session = self._get_session()

        for attempt in range(3):
            try:
                resp = session.get(url, params=params, timeout=30)
                if resp.status_code == 429:
                    wait = min(2 ** attempt * 2, 30)
                    logger.warning("Rate limited, waiting %ds", wait)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json().get("Response", {})
            except requests.exceptions.RequestException as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                logger.error("SmugMug API request failed: %s", e)
                raise

        return {}

    def get_authenticated_user(self) -> dict[str, Any]:
        """Get the authenticated user's information."""
        data = self._api_get(f"{SMUGMUG_API_VERSION}!authuser")
        user = data.get("User", {})
        self._user_uri = user.get("Uri", "")
        return user

    def get_albums(self, page: int = 1, count: int = 50) -> tuple[list[SmugMugAlbum], int]:
        """Fetch user's albums with pagination. Returns (albums, total_count)."""
        if not self._user_uri:
            self.get_authenticated_user()

        data = self._api_get(
            f"{self._user_uri}!albums",
            params={"start": (page - 1) * count + 1, "count": count},
        )

        albums = []
        for item in data.get("Album", []):
            albums.append(SmugMugAlbum(
                key=item.get("AlbumKey", ""),
                uri=item.get("Uri", ""),
                name=item.get("Name", ""),
                description=item.get("Description", ""),
                image_count=item.get("ImageCount", 0),
                url=item.get("WebUri", ""),
                date_modified=item.get("LastUpdated", ""),
            ))

        total = data.get("Pages", {}).get("Total", len(albums))
        return albums, total

    def get_album_photos(self, album_uri: str, album_name: str = "",
                         page: int = 1, count: int = 100) -> tuple[list[SmugMugPhoto], int]:
        """Fetch photos from a specific album. Returns (photos, total_count)."""
        data = self._api_get(
            f"{album_uri}!images",
            params={
                "start": (page - 1) * count + 1,
                "count": count,
                "_expand": "ImageSizeDetails",
            },
        )

        photos = []
        for item in data.get("AlbumImage", []):
            sizes = item.get("Uris", {}).get("ImageSizeDetails", {}).get("ImageSizeDetails", {})
            thumbnail_url = ""
            original_url = ""
            if sizes:
                thumbnail_url = sizes.get("ThumbImageUrl", sizes.get("SmallImageUrl", ""))
                original_url = sizes.get("OriginalImageUrl", sizes.get("LargestImageUrl", ""))
            else:
                thumbnail_url = item.get("ThumbnailUrl", "")
                original_url = item.get("ArchivedUri", "")

            photos.append(SmugMugPhoto(
                key=item.get("ImageKey", ""),
                uri=item.get("Uri", ""),
                title=item.get("Title", ""),
                filename=item.get("FileName", ""),
                caption=item.get("Caption", ""),
                date_taken=item.get("DateTimeOriginal", ""),
                date_uploaded=item.get("DateTimeUploaded", ""),
                thumbnail_url=thumbnail_url,
                web_url=item.get("WebUri", ""),
                original_url=original_url,
                size_bytes=item.get("OriginalSize", 0),
                width=item.get("OriginalWidth", 0),
                height=item.get("OriginalHeight", 0),
                album_name=album_name,
                keywords=item.get("Keywords", "").split(";") if item.get("Keywords") else [],
                md5_hash=item.get("ArchivedMD5", ""),
            ))

        total = data.get("Pages", {}).get("Total", len(photos))
        return photos, total

    def download_photo(self, photo: SmugMugPhoto, callback=None) -> bytes:
        """Download a photo's original file. Optional callback(bytes_downloaded, total)."""
        session = self._get_session()
        resp = session.get(photo.original_url, stream=True, timeout=120)
        resp.raise_for_status()

        total_size = int(resp.headers.get("content-length", 0))
        chunks = []
        downloaded = 0

        for chunk in resp.iter_content(chunk_size=64 * 1024):
            chunks.append(chunk)
            downloaded += len(chunk)
            if callback:
                callback(downloaded, total_size)

        return b"".join(chunks)

    def test_connection(self) -> bool:
        """Test if the current credentials are valid."""
        try:
            user = self.get_authenticated_user()
            return bool(user.get("NickName"))
        except Exception as e:
            logger.error("SmugMug connection test failed: %s", e)
            return False
