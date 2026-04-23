"""Figma Fetcher — extracts design data from Figma files via REST API.

Pulls frame metadata, component names, and optionally renders frame images.
Requires a Figma personal access token (FIGMA_TOKEN env var).
"""

import logging
import os
import re
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

FIGMA_API_BASE = "https://api.figma.com/v1"


def _parse_figma_url(url: str) -> tuple[str, Optional[str]]:
    """Extract file key and optional node ID from a Figma URL.
    
    Supports:
      - https://www.figma.com/file/FILEKEY/Name
      - https://www.figma.com/design/FILEKEY/Name?node-id=287-147428
      - https://www.figma.com/file/FILEKEY/Name?node-id=287:147428
    """
    # Extract file key
    match = re.search(r'figma\.com/(?:file|design)/([a-zA-Z0-9]+)', url)
    if not match:
        raise ValueError(f"Cannot extract Figma file key from URL: {url}")
    file_key = match.group(1)
    
    # Extract node ID if present
    node_id = None
    node_match = re.search(r'node-id=([0-9:%-]+)', url)
    if node_match:
        node_id = node_match.group(1).replace('%3A', ':').replace('-', ':')
    
    return file_key, node_id


class FigmaFetcher:
    """Fetches design data from Figma files."""

    def __init__(self, figma_token: Optional[str] = None):
        self._token = figma_token or os.environ.get("FIGMA_TOKEN", "")
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            if not self._token:
                raise ValueError("No Figma token. Set FIGMA_TOKEN env var.")
            self._client = httpx.Client(
                base_url=FIGMA_API_BASE,
                headers={"X-Figma-Token": self._token},
                timeout=30.0,
            )
        return self._client

    async def fetch(self, figma_url: str) -> dict:
        """Fetch design data from a Figma file URL.
        
        Returns dict with:
          - file_name: name of the Figma file
          - frames: list of top-level frames with their children
          - components: list of component names used
          - styles: color/text styles used
        """
        try:
            file_key, node_id = _parse_figma_url(figma_url)
        except ValueError as e:
            print(f"   ❌ Invalid Figma URL: {e}")
            return {"error": str(e), "frames": [], "components": [], "styles": {}}

        print(f"   📐 Fetching Figma file {file_key}...")
        
        try:
            client = self._get_client()
        except ValueError as e:
            print(f"   ❌ {e}")
            return {"error": str(e), "frames": [], "components": [], "styles": {}}

        try:
            # Get file metadata
            if node_id:
                resp = client.get(f"/files/{file_key}/nodes", params={"ids": node_id, "depth": 5})
            else:
                resp = client.get(f"/files/{file_key}", params={"depth": 4})
            resp.raise_for_status()
            data = resp.json()

            file_name = data.get("name", file_key)
            print(f"   📐 File: {file_name}")

            # Extract frames and components
            frames = []
            components = []
            
            if node_id and "nodes" in data:
                # Specific node requested
                for nid, node_data in data["nodes"].items():
                    doc = node_data.get("document", {})
                    frames.append(self._extract_frame(doc))
            else:
                # Full file — get top-level frames from pages
                document = data.get("document", {})
                for page in document.get("children", []):
                    for child in page.get("children", []):
                        if child.get("type") == "FRAME":
                            frames.append(self._extract_frame(child))

            # Extract component names
            comp_map = data.get("components", {})
            for comp_id, comp_data in comp_map.items():
                components.append({
                    "id": comp_id,
                    "name": comp_data.get("name", ""),
                    "description": comp_data.get("description", ""),
                })

            # Extract styles
            styles = {}
            style_map = data.get("styles", {})
            for style_id, style_data in style_map.items():
                styles[style_data.get("name", style_id)] = {
                    "type": style_data.get("styleType", ""),
                    "description": style_data.get("description", ""),
                }

            print(f"   📐 Found {len(frames)} frames, {len(components)} components, {len(styles)} styles")

            # Render frame images
            frame_images = {}
            if frames:
                frame_ids = [f["id"] for f in frames if f.get("id")]
                # Also get child frame IDs (the actual screens)
                for frame in frames:
                    for child in frame.get("children", []):
                        if child.get("id") and child.get("type") == "FRAME":
                            frame_ids.append(child["id"])
                
                if frame_ids:
                    print(f"   📸 Rendering {len(frame_ids)} frames as images...")
                    try:
                        img_resp = client.get(
                            f"/images/{file_key}",
                            params={"ids": ",".join(frame_ids[:20]), "format": "png", "scale": 2},
                        )
                        img_resp.raise_for_status()
                        img_data = img_resp.json()
                        frame_images = img_data.get("images", {})
                        rendered = sum(1 for v in frame_images.values() if v)
                        print(f"   📸 Got {rendered} rendered images")
                    except Exception as img_exc:
                        print(f"   ⚠️ Image rendering failed: {img_exc}")

            return {
                "file_name": file_name,
                "file_key": file_key,
                "frames": frames,
                "components": components,
                "styles": styles,
                "images": frame_images,
            }

        except httpx.HTTPStatusError as e:
            print(f"   ❌ Figma API error: {e.response.status_code} — {e.response.text[:200]}")
            return {"error": str(e), "frames": [], "components": [], "styles": {}}
        except Exception as e:
            print(f"   ❌ Figma fetch failed: {e}")
            return {"error": str(e), "frames": [], "components": [], "styles": {}}

    def _extract_frame(self, node: dict, depth: int = 0) -> dict:
        """Extract frame data recursively."""
        frame = {
            "id": node.get("id", ""),
            "name": node.get("name", ""),
            "type": node.get("type", ""),
        }
        
        # Get bounding box if available
        bbox = node.get("absoluteBoundingBox", {})
        if bbox:
            frame["width"] = bbox.get("width", 0)
            frame["height"] = bbox.get("height", 0)

        # Get children (limit depth to avoid huge payloads)
        if depth < 5 and "children" in node:
            frame["children"] = [
                self._extract_frame(child, depth + 1)
                for child in node["children"]
            ]
        
        return frame

    def close(self):
        if self._client and not self._client.is_closed:
            self._client.close()
