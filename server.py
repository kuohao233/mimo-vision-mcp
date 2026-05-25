#!/usr/bin/env python3
"""MiMo Vision Bridge - 让纯文本模型借用 MiMo-V2.5 的多模态能力。"""
import os
import json
import base64
from pathlib import Path
from urllib import request, error

from mcp.server.fastmcp import FastMCP

BASE_URL = os.environ.get(
    "MIMO_BASE_URL",
    "https://token-plan-cn.xiaomimimo.com/anthropic",
).rstrip("/")
API_KEY = os.environ.get("MIMO_API_KEY", "")
if not API_KEY:
    raise RuntimeError("MIMO_API_KEY environment variable is required")
VISION_MODEL = os.environ.get("MIMO_VISION_MODEL", "mimo-v2.5")
MAX_TOKENS = int(os.environ.get("MIMO_MAX_TOKENS", "4096"))
MAX_IMG_BYTES = 5 * 1024 * 1024  # Anthropic 协议单图上限

MIME_BY_EXT = {
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif":  "image/gif",
}

mcp = FastMCP("mimo-vision")


def _load_image(path: str) -> dict:
    """读图并组装成 Anthropic image content block。"""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"图片不存在: {p}")

    mime = MIME_BY_EXT.get(p.suffix.lower())
    if not mime:
        raise ValueError(
            f"不支持的格式 {p.suffix}; 仅支持 png/jpg/webp/gif"
        )

    raw = p.read_bytes()
    if len(raw) > MAX_IMG_BYTES:
        raise ValueError(
            f"图片过大 ({len(raw) // 1024} KB); 上限 5MB，请先缩放"
        )

    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": mime,
            "data": base64.b64encode(raw).decode(),
        },
    }


def _call_mimo(content_blocks: list, max_tokens: int = MAX_TOKENS) -> str:
    """调用 MiMo 的 Anthropic 兼容端点。"""
    payload = {
        "model": VISION_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": content_blocks}],
    }
    req = request.Request(
        f"{BASE_URL}/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read())
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"MiMo API {e.code}: {body}") from e
    except error.URLError as e:
        raise RuntimeError(f"网络错误: {e.reason}") from e

    # Anthropic 返回格式: {"content": [{"type": "text", "text": "..."}, ...]}
    chunks = [
        b.get("text", "")
        for b in data.get("content", [])
        if b.get("type") == "text"
    ]
    if not chunks:
        raise RuntimeError(f"MiMo 返回空文本: {data}")
    return "".join(chunks)


@mcp.tool()
def describe_image(image_path: str, prompt: str = "") -> str:
    """
    Analyze an image using MiMo-V2.5 multimodal model and return a text description.
    Use this tool whenever you need to understand image content (screenshots,
    UI mocks, diagrams, error captures, photos, etc.). Do NOT attempt to read
    image files with the Read tool — the active model is text-only.

    Args:
        image_path: Absolute or relative path to a png/jpg/webp/gif file.
        prompt: Specific instruction for what to extract. Be concrete, e.g.
            "extract all error messages and stack traces",
            "list every button, label, and input field with their positions",
            "describe nodes and edges of this flowchart",
            "transcribe all visible text verbatim".
            If empty, returns a general description.

    Returns:
        Text description / extraction from the image.
    """
    instruction = prompt.strip() or "请详细描述这张图片的内容，包括所有可见的文字、UI 元素、结构关系。"
    return _call_mimo([_load_image(image_path), {"type": "text", "text": instruction}])


@mcp.tool()
def analyze_images(image_paths: list[str], prompt: str) -> str:
    """
    Analyze multiple images together — useful for before/after diffs,
    A/B comparison, or multi-frame sequences.

    Args:
        image_paths: List of image file paths (2-5 recommended).
        prompt: Comparative or aggregate instruction,
            e.g. "what visual changes occurred between these screenshots?"
                 "do these UI mocks follow a consistent design system?"

    Returns:
        Aggregated analysis text.
    """
    if not image_paths:
        raise ValueError("至少需要一张图片")
    blocks = []
    for i, p in enumerate(image_paths, 1):
        blocks.append({"type": "text", "text": f"=== 图片 {i} ({Path(p).name}) ==="})
        blocks.append(_load_image(p))
    blocks.append({"type": "text", "text": prompt})
    return _call_mimo(blocks, max_tokens=max(MAX_TOKENS, 4096))


@mcp.tool()
def extract_text_from_image(image_path: str) -> str:
    """
    Pure OCR — extract all visible text from an image verbatim, no interpretation.
    Best for screenshots of logs, terminals, code, error dialogs, documents.

    Args:
        image_path: Path to image file.

    Returns:
        Raw transcribed text, preserving line breaks and structure as much as possible.
    """
    return _call_mimo([
        _load_image(image_path),
        {"type": "text", "text":
            "请逐字转录图中所有可见文本，保留换行和缩进结构。"
            "只输出文字内容，不要解释，不要添加任何评注。"
            "无法识别的字符用 [?] 代替。"},
    ])


if __name__ == "__main__":
    mcp.run()