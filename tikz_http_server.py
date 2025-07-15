#!/usr/bin/env python3

import subprocess
import tempfile
import base64
import logging
import sys
import os
import uuid
from pathlib import Path
import contextlib
from collections.abc import AsyncIterator
from datetime import datetime

import click
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse
from starlette.types import Receive, Scope, Send

# Configure logging
logger = logging.getLogger(__name__)


class TikZHTTPServer:
    def __init__(self):
        self.server = Server("tikz-renderer-http")
        self.server_name = "tikz-renderer-http"
        self.server_version = "0.1.0"
        
        # 获取公网IP地址
        self.public_ip = os.getenv('PUBLIC_IP', 'localhost')
        self.public_port = os.getenv('PUBLIC_PORT', '3000')
        
        # 确保图片存储目录存在
        self.images_dir = Path('./images').expanduser()
        self.images_dir.mkdir(exist_ok=True)
        
        # 确保有权限写入
        try:
            test_file = self.images_dir / '.test'
            test_file.touch()
            test_file.unlink()
        except PermissionError:
            logger.error(f"无法写入图片目录: {self.images_dir}")
            raise

    def compile_tikz_to_image(self, tikz_code: str) -> tuple[str, str]:
        return self._compile_tikz(tikz_code, return_base64=True)

    def compile_tikz_to_url(self, tikz_code: str) -> str:
        base64_data, file_url = self._compile_tikz(tikz_code, return_base64=False)
        return file_url

    def install_tex_package(self, package_name: str) -> str:
        """Install a TeX package using tlmgr or apt-get."""
        try:
            # 首先尝试使用 tlmgr
            result = subprocess.run([
                "tlmgr", "install", package_name
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return f"Successfully installed TeX package: {package_name}"
            else:
                # 如果tlmgr不可用，尝试使用apt-get
                result = subprocess.run([
                    "apt-get", "update"
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    result = subprocess.run([
                        "apt-get", "install", "-y", f"texlive-{package_name}"
                    ], capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0:
                        return f"Successfully installed TeX package: texlive-{package_name}"
                    else:
                        return f"Failed to install package {package_name} via apt-get: {result.stderr}"
                else:
                    return f"Failed to install package {package_name}: {result.stderr}"
                    
        except subprocess.TimeoutExpired:
            return f"Installation timeout for package: {package_name}"
        except Exception as e:
            return f"Error installing package {package_name}: {str(e)}"

    def _compile_tikz(self, tikz_code: str, return_base64: bool) -> tuple[str, str]:
        """Compile TikZ code to PNG image and return (base64_data, file_url)."""
        try:
            subprocess.run(["xelatex", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("xelatex not found. Please install TeX Live or MiKTeX.")

        try:
            subprocess.run(["convert", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("ImageMagick convert not found. Please install ImageMagick.")

        with tempfile.TemporaryDirectory() as temp_dir:
            tex_file = Path(temp_dir) / "diagram.tex"

            if '\\documentclass' in tikz_code:
                latex_content = tikz_code
            else:
                latex_content = f"""\\documentclass[border=2pt]{{standalone}}
\\usepackage{{xeCJK}}
\\usepackage{{fontspec}}
\\usepackage{{tikz}}
\\usepackage{{pgfplots}}
\\usepackage{{amsmath}}
\\usepackage{{amssymb}}
\\usepackage{{xcolor}}
\\usetikzlibrary{{shapes,arrows,positioning,calc,decorations.pathreplacing,patterns,fit,backgrounds,mindmap,trees,arrows.meta,angles,quotes}}
\\pgfplotsset{{compat=1.18}}

\\begin{{document}}
{tikz_code}
\\end{{document}}
"""

            tex_file.write_text(latex_content, encoding='utf-8')

            try:
                subprocess.run([
                    "xelatex",
                    "-interaction=nonstopmode",
                    "-output-directory", temp_dir,
                    str(tex_file)
                ], check=True, capture_output=True, text=True, cwd=temp_dir)
            except subprocess.CalledProcessError as e:
                log_file = Path(temp_dir) / "diagram.log"
                error_details = ""
                if log_file.exists():
                    log_content = log_file.read_text(encoding='utf-8', errors='ignore')
                    lines = log_content.split('\n')

                    error_section = False
                    error_lines = []
                    context_lines = []

                    for i, line in enumerate(lines):
                        line_clean = line.strip()

                        if any(keyword in line.lower() for keyword in ['! ', 'error:', 'undefined', 'missing']):
                            error_section = True
                            error_lines.append(line_clean)
                            for j in range(max(0, i-2), i):
                                if lines[j].strip() and lines[j].strip() not in context_lines:
                                    context_lines.append(lines[j].strip())
                            continue

                        if error_section:
                            if line_clean:
                                if line.startswith('l.') or 'line' in line.lower():
                                    error_lines.append(line_clean)
                                elif any(char in line for char in ['^', '?']):
                                    error_lines.append(line_clean)
                                elif line_clean.startswith('\\') or '\\' in line_clean:
                                    error_lines.append(line_clean)
                                elif len(error_lines) < 10:
                                    error_lines.append(line_clean)
                            else:
                                if len(error_lines) > 0:
                                    break

                    if context_lines or error_lines:
                        all_lines = context_lines + ['--- Error Details ---'] + error_lines
                        error_details = '\n'.join(all_lines[:20])
                    else:
                        last_lines = [line for line in lines[-50:] if line.strip()]
                        error_details = '\n'.join(last_lines[-15:])

                    if not error_details:
                        error_details = e.stderr or "LaTeX compilation failed with unknown error"
                else:
                    error_details = e.stderr or "LaTeX compilation failed - no log file generated"

                raise RuntimeError(f"LaTeX compilation failed:\n\n{error_details}")

            pdf_file = Path(temp_dir) / "diagram.pdf"
            if not pdf_file.exists():
                raise RuntimeError("PDF file was not generated")

            # 生成唯一的文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"tikz_{timestamp}_{unique_id}.png"
            saved_png_path = self.images_dir / filename
            
            try:
                subprocess.run([
                    "convert",
                    "-density", "300",
                    "-quality", "90",
                    str(pdf_file),
                    str(saved_png_path)
                ], check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Image conversion failed: {e}")

            if not saved_png_path.exists():
                raise RuntimeError("PNG file was not generated")

            # 生成文件URL
            file_url = f"http://{self.public_ip}:{self.public_port}/images/{filename}"
            
            # 生成base64数据
            image_base64 = ""
            if return_base64:
                with open(saved_png_path, "rb") as f:
                    image_base64 = base64.b64encode(f.read()).decode('utf-8')
                
            return image_base64, file_url

    def setup_handlers(self):
        """Setup MCP tool handlers."""

        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            tools = [
                types.Tool(
                    name="render_tikz_base64",
                    description="Render TikZ code to high-quality PNG image and return as base64. Supports TikZ diagrams, mathematical plots, flowcharts, and technical illustrations.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tikz_code": {
                                "type": "string",
                                "description": "TikZ/LaTeX code to render. Can include \\begin{tikzpicture}...\\end{tikzpicture} or full LaTeX document with \\documentclass."
                            }
                        },
                        "required": ["tikz_code"]
                    }
                ),
                types.Tool(
                    name="render_tikz_url",
                    description="Render TikZ code to high-quality PNG image and return as a URL. Supports TikZ diagrams, mathematical plots, flowcharts, and technical illustrations.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tikz_code": {
                                "type": "string",
                                "description": "TikZ/LaTeX code to render. Can include \\begin{tikzpicture}...\\end{tikzpicture} or full LaTeX document with \\documentclass."
                            }
                        },
                        "required": ["tikz_code"]
                    }
                ),
                types.Tool(
                    name="install_tex_package",
                    description="Install additional TeX packages using tlmgr or apt-get. Useful for adding missing packages needed for TikZ rendering.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "package_name": {
                                "type": "string",
                                "description": "Name of the TeX package to install (e.g., 'pgfplots', 'tikz-cd', 'tkz-euclide')."
                            }
                        },
                        "required": ["package_name"]
                    }
                )
            ]
            logger.info(f"Listing tools: {[tool.name for tool in tools]}")
            return tools

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict
        ) -> list[types.ContentBlock]:
            logger.info(f"Call tool received: {name}")
            if name == "render_tikz_base64":
                tikz_code = arguments.get("tikz_code")

                if not tikz_code or not isinstance(tikz_code, str):
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Valid TikZ code is required"
                        )
                    ]

                try:
                    logger.info("Starting TikZ compilation for base64...")
                    image_base64, file_url = self.compile_tikz_to_image(tikz_code)
                    logger.info("TikZ compilation completed successfully for base64")

                    return [
                        types.TextContent(
                            type="text",
                            text="TikZ diagram rendered successfully"
                        ),
                        types.ImageContent(
                            type="image",
                            data=image_base64,
                            mimeType="image/png"
                        )
                    ]

                except Exception as e:
                    error_msg = str(e)
                    logger.exception("TikZ compilation failed for base64")
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Compilation Error: {error_msg}"
                        )
                    ]

            elif name == "render_tikz_url":
                tikz_code = arguments.get("tikz_code")

                if not tikz_code or not isinstance(tikz_code, str):
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Valid TikZ code is required"
                        )
                    ]

                try:
                    logger.info("Starting TikZ compilation for URL...")
                    image_base64, file_url = self.compile_tikz_to_image(tikz_code)
                    logger.info("TikZ compilation completed successfully for URL")

                    return [
                        types.TextContent(
                            type="text",
                            text=f"TikZ diagram rendered successfully. URL: {file_url}"
                        ),
                        types.ImageContent(
                            type="image",
                            data=image_base64,
                            mimeType="image/png"
                        )
                    ] if image_base64 else [
                        types.TextContent(
                            type="text",
                            text=f"TikZ diagram rendered successfully. URL: {file_url}"
                        )
                    ]

                except Exception as e:
                    error_msg = str(e)
                    logger.exception("TikZ compilation failed for URL")
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Compilation Error: {error_msg}"
                        )
                    ]

            elif name == "install_tex_package":
                package_name = arguments.get("package_name")

                if not package_name or not isinstance(package_name, str):
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Valid package name is required"
                        )
                    ]

                try:
                    logger.info(f"Starting installation of TeX package: {package_name}")
                    result = self.install_tex_package(package_name)
                    logger.info(f"TeX package installation completed: {package_name}")

                    return [
                        types.TextContent(
                            type="text",
                            text=result
                        )
                    ]

                except Exception as e:
                    error_msg = str(e)
                    logger.exception("TeX package installation failed")
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Installation Error: {error_msg}"
                        )
                    ]

            else:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Unknown tool: {name}. Available tools: render_tikz_base64, render_tikz_url, install_tex_package"
                    )
                ]


@click.command()
@click.option("--port", default=3000, help="Port to listen on for HTTP")
@click.option(
    "--log-level",
    default="INFO",
    help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
)
@click.option(
    "--json-response",
    is_flag=True,
    default=False,
    help="Enable JSON responses instead of SSE streams",
)
def main(
    port: int,
    log_level: str,
    json_response: bool,
) -> int:
    """Start the TikZ HTTP MCP server."""
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create server instance
    tikz_server = TikZHTTPServer()
    tikz_server.setup_handlers()

    # Create the session manager (stateless mode for simplicity)
    session_manager = StreamableHTTPSessionManager(
        app=tikz_server.server,
        event_store=None,  # Stateless mode
        json_response=json_response,
        stateless=True,
    )

    # ASGI handler for streamable HTTP connections
    async def handle_streamable_http(
        scope: Scope, receive: Receive, send: Send
    ) -> None:
        await session_manager.handle_request(scope, receive, send)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        """Context manager for managing session manager lifecycle."""
        async with session_manager.run():
            logger.info("TikZ HTTP MCP server started!")
            try:
                yield
            finally:
                logger.info("TikZ HTTP MCP server shutting down...")

    # Create an ASGI application
    starlette_app = Starlette(
        debug=True,
        routes=[
            Mount("/mcp", app=handle_streamable_http),
            Mount("/images", app=StaticFiles(directory=tikz_server.images_dir)),
        ],
        lifespan=lifespan,
    )

    import uvicorn
    uvicorn.run(starlette_app, host="0.0.0.0", port=port)

    return 0


if __name__ == "__main__":
    sys.exit(main())