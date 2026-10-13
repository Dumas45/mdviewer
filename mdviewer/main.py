import os
import logging
import mimetypes
from pathlib import Path
from typing import Optional
from xml.etree.ElementTree import Element

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

from urllib.parse import urlparse

log = logging.getLogger(__name__)


app = FastAPI(title="Markdown Viewer")

# Store the base folder path on the server
base_folder_path: Optional[Path] = None

# Configure Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


class SetBaseFolderRequest(BaseModel):
    folder_path: str


@app.post("/api/set-base-folder")
def set_base_folder(request: SetBaseFolderRequest):
    """Set the base folder path on the server"""
    global base_folder_path
    try:
        target_dir = Path(request.folder_path).resolve()

        if not target_dir.exists():
            raise HTTPException(status_code=404, detail="Directory not found")

        if not target_dir.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")

        base_folder_path = target_dir
        return JSONResponse(content={"status": "success", "base_folder": str(base_folder_path)})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting base folder: {str(e)}")


@app.get("/api/get-base-folder")
def get_base_folder():
    """Get the current base folder path from the server"""
    if base_folder_path is None:
        return JSONResponse(content={"base_folder": None})
    return JSONResponse(content={"base_folder": str(base_folder_path)})


def is_relative_path(path: str) -> bool:
    return not os.path.isabs(path) and not urlparse(path).scheme


def _tweak_urls(element: Element, path_prefix: Path) -> None:
    """Update urls in `img[src]` and `a[href]` by adding a prefix to them."""
    cwd = Path.cwd()
    assets_path = Path('/assets')
    if element.tag == 'img' and 'src' in element.attrib:
        src = element.attrib['src']
        if src and is_relative_path(src):
            new_src = (path_prefix / src).resolve().absolute().relative_to(cwd)
            new_src = assets_path / new_src
            element.set('src', str(new_src))
            log.info("Image file link changed from %s to %s", src, new_src)
    elif element.tag == 'a' and 'href' in element.attrib:
        href = element.attrib['href']
        if href and is_relative_path(href):
            new_href = (path_prefix / href).resolve().absolute().relative_to(cwd)
            element.set('href', str(new_href))
            log.info("URL changed from %s to %s", href, new_href)


class HtmlTweakProcessor(Treeprocessor):
    def __init__(self, md: markdown.Markdown, path_prefix: Path):
        super().__init__(md)
        self.path_prefix = path_prefix

    def run(self, root: Element) -> Element:
        for element in root.iter():
            _tweak_urls(element, self.path_prefix)

        return root


class HtmlTweakExtension(Extension):
    def __init__(self, path_prefix: Path, **kwargs):
        self.config = {
            'path_prefix': [path_prefix, 'Prefix to add to URLs'],
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md: markdown.Markdown):
        path_prefix = self.getConfig('path_prefix')
        md.treeprocessors.register(
            HtmlTweakProcessor(md, path_prefix),
            name='html_tweak_processor',
            priority=15
        )


def _render_markdown_to_html(markdown_content: str, path_prefix: Path) -> str:
    """Convert markdown content to HTML with optional emoji and LaTeX math support"""
    extensions = [
        'extra',
        'codehilite',
        HtmlTweakExtension(path_prefix=path_prefix)
    ]
    extension_configs = {}

    try:
        import pymdownx.emoji

        def to_alt_with_span(*args, **kwargs):
            alt = args[4] if len(args) > 4 else kwargs.get('alt', '')
            span = Element('span')
            span.set('class', 'emoji')
            span.text = alt
            return span

        extensions.extend(['pymdownx.emoji', 'pymdownx.superfences', 'pymdownx.arithmatex'])
        extension_configs['pymdownx.emoji'] = {
            'emoji_index': pymdownx.emoji.gemoji,
            'emoji_generator': to_alt_with_span
        }
        # Generic mode emits \(...\) / \[...\] which KaTeX auto-render picks up in the browser
        extension_configs['pymdownx.arithmatex'] = {'generic': True}
    except ImportError:
        pass

    md = markdown.Markdown(
        extensions=extensions,
        extension_configs=extension_configs
    )
    return md.convert(markdown_content)


def get_file_tree(directory: Path, relative_to: Optional[Path] = None) -> list:
    """Recursively build a tree structure of markdown files"""
    if relative_to is None:
        relative_to = directory

    items = []
    try:
        for item in sorted(directory.iterdir()):
            if item.is_file() and item.suffix.lower() == '.md':
                relative_path = item.relative_to(relative_to)
                items.append({
                    "name": item.name,
                    "path": str(relative_path),
                    "type": "file"
                })
            elif item.is_dir() and not item.name.startswith('.'):
                subdirectory_items = get_file_tree(item, relative_to)
                if subdirectory_items:  # Only include directories with markdown files
                    items.append({
                        "name": item.name,
                        "path": str(item.relative_to(relative_to)),
                        "type": "directory",
                        "children": subdirectory_items
                    })
    except PermissionError:
        pass

    return items


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    """Serve the main HTML page using Jinja2 template"""
    return templates.TemplateResponse(request=request, name="index.html", context={
        "request": request,
        "title": "Markdown Viewer",
        "sidebar_title": "Markdown Files",
        "default_message": "Select a markdown file from the tree to view its content."
    })


@app.get("/api/files")
def get_files(folder_path: Optional[str] = None):
    """API endpoint to get the file tree structure"""
    try:
        if folder_path is None:
            return JSONResponse(content=[])

        target_dir = Path(folder_path).resolve()

        # Security check: ensure the path exists and is a directory
        if not target_dir.exists():
            raise HTTPException(status_code=404, detail="Directory not found")

        if not target_dir.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")

        file_tree = get_file_tree(target_dir)
        return JSONResponse(content=file_tree)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading directory: {str(e)}")


@app.get("/assets/{file_path:path}")
def serve_asset(file_path: str):
    """Serve static assets (images, etc.) from the selected markdown folder"""
    try:
        if base_folder_path is None:
            raise HTTPException(status_code=400, detail="Base folder not set. Please select a folder first.")

        base_dir = base_folder_path.resolve().absolute()
        full_path = base_dir / file_path

        # Security check: ensure the file is within the base directory
        if not str(full_path.resolve()).startswith(str(base_dir.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")

        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(full_path))
        if mime_type is None:
            mime_type = "application/octet-stream"

        return FileResponse(full_path, media_type=mime_type)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving asset: {str(e)}")


def _get_markdown_html(file_path: str) -> str:
    """Read and render a markdown file to HTML. Performs security checks."""
    # Only handle .md files
    if not file_path.endswith('.md'):
        raise HTTPException(status_code=404, detail="Not found")

    if base_folder_path is None:
        raise HTTPException(status_code=400, detail="Base folder not set. Please select a folder first.")

    full_path = base_folder_path / file_path

    # Security check: ensure the file is within the base directory
    if not str(full_path.resolve()).startswith(str(base_folder_path.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    if full_path.suffix.lower() != '.md':
        raise HTTPException(status_code=400, detail="Not a markdown file")

    # Read and render markdown
    with open(full_path, 'r', encoding='utf-8') as f:
        markdown_content = f.read()

    return _render_markdown_to_html(markdown_content, path_prefix=Path(file_path).parent)


@app.get("/raw/{file_path:path}")
def get_file_raw_html_content(file_path: str):
    """Serve markdown file using relative paths from the base folder"""
    try:
        html_content = _get_markdown_html(file_path)
        return HTMLResponse(content=f'<div class="markdown-content">{html_content}</div>')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@app.get("/{file_path:path}", response_class=HTMLResponse)
def get_file_rendered_markdown(request: Request, file_path: str):
    """Serve markdown file with Jinja2 template using relative paths from the base folder"""
    try:
        html_content = _get_markdown_html(file_path)

        return templates.TemplateResponse(request=request, name="markdown.html", context={
            "request": request,
            "filename": Path(file_path).name,
            "html_content": html_content,
            "base_folder": str(base_folder_path),
            "sidebar_title": "Markdown Files"
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8700)
