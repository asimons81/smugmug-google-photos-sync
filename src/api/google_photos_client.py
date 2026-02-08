"""Google Photos API client with OAuth 2.0 authentication."""

import os
import hashlib
import io
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

GOOGLE_PHOTOS_API_BASE = "https://photoslibrary.googleapis.com/v1"
SCOPES = [
    "https://www.googleapis.com/auth/photoslibrary.appendonly",
    "https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata",
]
SCOPES_CACHE_VERSION = 2


class GooglePhotosApiError(RuntimeError):
    """Base error for Google Photos API failures."""

    def __init__(self, message: str, status_code: int | None = None,
                 response_text: str = "", endpoint: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
        self.endpoint = endpoint


class GooglePhotosPermissionError(GooglePhotosApiError):
    """Permission-related Google Photos API error."""


@dataclass
class GooglePhotosAlbum:
    """Represents a Google Photos album."""

    id: str
    title: str
    product_url: str
    media_items_count: int
    cover_photo_url: str = ""


@dataclass
class GooglePhotosMediaItem:
    """Represents a media item in Google Photos."""

    id: str
    filename: str
    mime_type: str
    creation_time: str
    width: int
    height: int
    base_url: str
    product_url: str
    description: str = ""


class GooglePhotosClient:
    """Client for interacting with the Google Photos Library API."""

    def __init__(self, client_id: str = "", client_secret: str = "",
                 credentials_path: Path | None = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self._credentials: Credentials | None = None
        self._credentials_path = credentials_path
        self._session: requests.Session | None = None
        self._force_consent = False

        if credentials_path and credentials_path.exists():
            self._load_credentials()

    @property
    def is_authenticated(self) -> bool:
        return self._credentials is not None and self._credentials.valid

    def _load_credentials(self):
        """Load saved credentials from disk."""
        try:
            if self._credentials_path and self._credentials_path.exists():
                if not self._is_scope_cache_valid():
                    self._invalidate_cached_credentials("OAuth scopes changed")
                    return
                self._credentials = Credentials.from_authorized_user_file(
                    str(self._credentials_path), SCOPES
                )
                if self._credentials and self._credentials.expired and self._credentials.refresh_token:
                    self._credentials.refresh(GoogleRequest())
                    self._save_credentials()
                logger.info("Google Photos credentials loaded")
        except Exception as e:
            logger.warning("Failed to load Google Photos credentials: %s", e)
            self._credentials = None

    def _save_credentials(self):
        """Save credentials to disk for reuse."""
        if self._credentials and self._credentials_path:
            self._credentials_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._credentials_path, "w") as f:
                f.write(self._credentials.to_json())
            self._save_scope_cache()

    def _scope_cache_path(self) -> Path | None:
        if not self._credentials_path:
            return None
        return self._credentials_path.with_suffix(".scopes.json")

    def _load_scope_cache(self) -> dict[str, Any]:
        cache_path = self._scope_cache_path()
        if not cache_path or not cache_path.exists():
            return {}
        try:
            return json.loads(cache_path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_scope_cache(self):
        cache_path = self._scope_cache_path()
        if not cache_path:
            return
        payload = {
            "version": SCOPES_CACHE_VERSION,
            "scopes": SCOPES,
        }
        cache_path.write_text(json.dumps(payload, indent=2))

    def _is_scope_cache_valid(self) -> bool:
        cache = self._load_scope_cache()
        cached_scopes = cache.get("scopes")
        cached_version = cache.get("version")
        if cached_scopes is None or cached_version is None:
            self._force_consent = True
            return False
        if cached_version != SCOPES_CACHE_VERSION or cached_scopes != SCOPES:
            self._force_consent = True
            return False
        return True

    def _invalidate_cached_credentials(self, reason: str):
        logger.info("Invalidating cached Google Photos credentials: %s", reason)
        if self._credentials_path and self._credentials_path.exists():
            try:
                self._credentials_path.unlink()
            except OSError as exc:
                logger.warning("Failed to remove credentials file: %s", exc)
        cache_path = self._scope_cache_path()
        if cache_path and cache_path.exists():
            try:
                cache_path.unlink()
            except OSError as exc:
                logger.warning("Failed to remove scope cache file: %s", exc)
        self._credentials = None
        self._session = None

    def _get_session(self) -> requests.Session:
        """Get an authenticated requests session."""
        if self._session is None:
            self._session = requests.Session()
        if self._credentials:
            if self._credentials.expired and self._credentials.refresh_token:
                self._credentials.refresh(GoogleRequest())
                self._save_credentials()
            self._session.headers.update({
                "Authorization": f"Bearer {self._credentials.token}",
                "Content-Type": "application/json",
            })
        return self._session

    # --- OAuth Flow ---

    def get_auth_flow(self, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> InstalledAppFlow:
        """Create an OAuth flow for user authorization."""
        client_config = {
            "installed": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        return flow

    def authenticate_with_code(self, auth_code: str) -> bool:
        """Complete authentication with an authorization code."""
        try:
            flow = self.get_auth_flow()
            flow.fetch_token(code=auth_code)
            self._credentials = flow.credentials
            self._save_credentials()
            self._session = None
            logger.info("Google Photos authentication completed")
            return True
        except Exception as e:
            logger.error("Google Photos auth failed: %s", e)
            return False

    def authenticate_local_server(self, port: int = 8090) -> bool:
        """Authenticate using a local server redirect (opens browser)."""
        try:
            host = os.environ.get("OAUTH_CALLBACK_HOST")
            if not host and self._is_chromeos():
                host = "penguin.linux.test"
            if not host:
                host = "localhost"

            redirect_uri = f"http://{host}:{port}/"
            fallback_url = f"http://penguin.linux.test:{port}/"
            if host != "penguin.linux.test":
                logger.info(
                    "If the callback fails on ChromeOS, try this URL: %s",
                    fallback_url,
                )

            flow = self.get_auth_flow(redirect_uri=redirect_uri)
            self._credentials = flow.run_local_server(
                port=port,
                prompt="consent" if self._force_consent else None,
                open_browser=True,
                host=host,
                bind_addr="0.0.0.0",
            )
            self._force_consent = False
            self._save_credentials()
            self._session = None
            logger.info("Google Photos authentication completed via local server")
            return True
        except Exception as e:
            logger.error("Google Photos local server auth failed: %s", e)
        return False

    def _is_chromeos(self) -> bool:
        try:
            with open("/etc/os-release", "r") as handle:
                content = handle.read().lower()
            return "cros" in content or "chromeos" in content
        except Exception:
            return False

    # --- API Methods ---

    def _api_request(self, method: str, endpoint: str,
                     json_data: dict | None = None,
                     params: dict | None = None) -> dict[str, Any]:
        """Make an authenticated API request."""
        url = f"{GOOGLE_PHOTOS_API_BASE}/{endpoint}"
        session = self._get_session()

        def _normalize_payload(payload: Any) -> dict[str, Any]:
            if payload is None:
                return {}
            if isinstance(payload, dict):
                return payload
            if isinstance(payload, str):
                preview = payload[:200]
                logger.debug("Google Photos response payload type=str preview=%r", preview)
                try:
                    parsed = json.loads(payload)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        "Google Photos API response was not a JSON object "
                        f"(type=str preview={preview!r})"
                    ) from exc
                if isinstance(parsed, dict):
                    return parsed
                raise ValueError(
                    "Google Photos API response JSON was not an object "
                    f"(type={type(parsed).__name__} preview={preview!r})"
                )
            preview = str(payload)[:200]
            logger.debug(
                "Google Photos response payload type=%s preview=%r",
                type(payload).__name__,
                preview,
            )
            raise ValueError(
                "Google Photos API response was not a JSON object "
                f"(type={type(payload).__name__} preview={preview!r})"
            )

        for attempt in range(3):
            try:
                resp = session.request(method, url, json=json_data, params=params, timeout=30)
                if resp.status_code == 429:
                    wait = min(2 ** attempt * 2, 30)
                    logger.warning("Google Photos rate limited, waiting %ds", wait)
                    time.sleep(wait)
                    continue
                if resp.status_code >= 400:
                    response_text = resp.text.strip()
                    logger.error(
                        "Google Photos API request failed (%s %s): status=%s body=%s",
                        method,
                        endpoint,
                        resp.status_code,
                        response_text,
                    )
                    if resp.status_code == 403:
                        raise GooglePhotosPermissionError(
                            "Google Photos API permission error",
                            status_code=resp.status_code,
                            response_text=response_text,
                            endpoint=endpoint,
                        )
                    raise GooglePhotosApiError(
                        "Google Photos API request failed",
                        status_code=resp.status_code,
                        response_text=response_text,
                        endpoint=endpoint,
                    )
                payload = resp.json() if resp.content else {}
                return _normalize_payload(payload)
            except requests.exceptions.RequestException as e:
                if e.response is not None:
                    logger.error(
                        "Google Photos API request failed (%s %s): status=%s body=%s",
                        method,
                        endpoint,
                        e.response.status_code,
                        e.response.text.strip(),
                    )
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                logger.error("Google Photos API request failed: %s", e)
                raise

        return {}

    def get_albums(self, page_token: str = "") -> tuple[list[GooglePhotosAlbum], str]:
        """List user's albums. Returns (albums, next_page_token)."""
        params = {"pageSize": 50}
        if page_token:
            params["pageToken"] = page_token

        data = self._api_request("GET", "albums", params=params)

        albums = []
        for item in data.get("albums", []):
            albums.append(GooglePhotosAlbum(
                id=item.get("id", ""),
                title=item.get("title", ""),
                product_url=item.get("productUrl", ""),
                media_items_count=int(item.get("mediaItemsCount", 0)),
                cover_photo_url=item.get("coverPhotoBaseUrl", ""),
            ))

        return albums, data.get("nextPageToken", "")

    def create_album(self, title: str) -> GooglePhotosAlbum:
        """Create a new album in Google Photos."""
        data = self._api_request("POST", "albums", json_data={
            "album": {"title": title}
        })
        album_data = data.get("album", data)
        return GooglePhotosAlbum(
            id=album_data.get("id", ""),
            title=album_data.get("title", title),
            product_url=album_data.get("productUrl", ""),
            media_items_count=0,
        )

    def search_media_items(self, album_id: str = "",
                           page_token: str = "",
                           page_size: int = 100) -> tuple[list[GooglePhotosMediaItem], str]:
        """Search media items, optionally filtered by album."""
        body: dict[str, Any] = {"pageSize": page_size}
        if album_id:
            body["albumId"] = album_id
        if page_token:
            body["pageToken"] = page_token

        data = self._api_request("POST", "mediaItems:search", json_data=body)

        items = []
        for item in data.get("mediaItems", []):
            metadata = item.get("mediaMetadata", {})
            items.append(GooglePhotosMediaItem(
                id=item.get("id", ""),
                filename=item.get("filename", ""),
                mime_type=item.get("mimeType", ""),
                creation_time=metadata.get("creationTime", ""),
                width=int(metadata.get("width", 0)),
                height=int(metadata.get("height", 0)),
                base_url=item.get("baseUrl", ""),
                product_url=item.get("productUrl", ""),
                description=item.get("description", ""),
            ))

        return items, data.get("nextPageToken", "")

    def upload_photo(self, photo_bytes: bytes, filename: str,
                     description: str = "", album_id: str = "",
                     callback=None) -> str | None:
        """Upload a photo to Google Photos.

        Returns the media item ID on success, None on failure.
        """
        session = self._get_session()

        # Step 1: Upload bytes to get an upload token
        upload_headers = {
            "Authorization": session.headers.get("Authorization", ""),
            "Content-Type": "application/octet-stream",
            "X-Goog-Upload-File-Name": filename,
            "X-Goog-Upload-Protocol": "raw",
        }

        try:
            resp = requests.post(
                f"{GOOGLE_PHOTOS_API_BASE}/uploads",
                headers=upload_headers,
                data=photo_bytes,
                timeout=300,
            )
            resp.raise_for_status()
            upload_token = resp.text
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                logger.error(
                    "Failed to upload bytes for %s: status=%s body=%s",
                    filename,
                    e.response.status_code,
                    e.response.text.strip(),
                )
            else:
                logger.error("Failed to upload bytes for %s: %s", filename, e)
            return None

        # Step 2: Create media item from the upload token
        new_item: dict[str, Any] = {
            "simpleMediaItem": {
                "uploadToken": upload_token,
                "fileName": filename,
            }
        }
        if description:
            new_item["description"] = description

        body: dict[str, Any] = {"newMediaItems": [new_item]}
        if album_id:
            body["albumId"] = album_id

        try:
            data = self._api_request("POST", "mediaItems:batchCreate", json_data=body)
            results = data.get("newMediaItemResults", [])
            if results:
                status = results[0].get("status", {})
                if status.get("message", "").upper() in ("SUCCESS", "OK") or "mediaItem" in results[0]:
                    media_item = results[0].get("mediaItem", {})
                    logger.info("Uploaded %s to Google Photos (id=%s)", filename, media_item.get("id"))
                    return media_item.get("id")
                else:
                    logger.error("Upload failed for %s: %s", filename, status)
                    return None
        except Exception as e:
            logger.error("Failed to create media item for %s: %s", filename, e)
            return None

        return None

    def add_to_album(self, album_id: str, media_item_ids: list[str]) -> bool:
        """Add media items to an album."""
        try:
            self._api_request(
                "POST",
                f"albums/{album_id}:batchAddMediaItems",
                json_data={"mediaItemIds": media_item_ids},
            )
            return True
        except Exception as e:
            logger.error("Failed to add items to album: %s", e)
            return False

    def get_all_media_filenames(self) -> set[str]:
        """Fetch all media item filenames for duplicate detection."""
        filenames = set()
        page_token = ""
        while True:
            items, page_token = self.search_media_items(page_token=page_token)
            for item in items:
                filenames.add(item.filename)
            if not page_token:
                break
        return filenames

    def test_connection(self) -> bool:
        """Test if the current credentials are valid."""
        try:
            albums, _ = self.get_albums()
            return True
        except GooglePhotosPermissionError as e:
            message = (
                "Google Photos album listing is restricted. "
                "Reconnect Google Photos or create an app-created album."
            )
            logger.error("Google Photos connection test failed: %s", message)
            raise GooglePhotosPermissionError(
                message,
                status_code=e.status_code,
                response_text=e.response_text,
                endpoint=e.endpoint,
            ) from e
        except Exception as e:
            logger.error("Google Photos connection test failed: %s", e)
            raise
