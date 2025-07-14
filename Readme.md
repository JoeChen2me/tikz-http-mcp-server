# TikZ HTTP MCP 服务器

这是一个基于 Model Context Protocol (MCP) 的 HTTP 服务器，专门用于将 TikZ/LaTeX 代码渲染成高质量的 PNG 图像。它提供了一个 `render_tikz` 工具，允许客户端通过 HTTP 请求提交 TikZ 代码并接收渲染后的图像。

## 功能特性

*   **TikZ 渲染**: 将 TikZ/LaTeX 代码编译为 PNG 图像。
*   **MCP 兼容**: 作为 MCP 服务器运行，提供 `render_tikz` 工具。
*   **Docker 部署**: 提供 `deploy.sh` 脚本，简化 Docker 环境下的部署。
*   **错误处理**: 捕获 LaTeX 编译和图像转换过程中的错误，并提供详细的错误信息。

## 启动方法

### 前提条件

在启动服务器之前，请确保您的系统已安装以下软件：

*   **Docker**: 用于容器化部署。
*   **Docker Compose**: 用于管理多容器 Docker 应用程序。

### 环境变量配置

项目使用 `.env` 文件来配置环境变量。您可以复制 `.env.example` 文件并将其重命名为 `.env`，然后根据需要修改其中的值。

```bash
cp .env.example .env
```

`.env` 文件中包含以下示例变量：

*   `SERVICE_NAME`: Docker Compose 服务的名称，默认为 `tikz-mcp-server`。
*   `CONTAINER_NAME`: Docker 容器的显式名称，默认为 `tikz-mcp-server-container`。

### 部署步骤

1.  **克隆仓库** (如果尚未克隆):
    ```bash
    git clone git@github.com:JoeChen2me/tikz-http-mcp-server.git
    cd tikz-http-mcp-server
    ```
    (请将 `git@github.com:JoeChen2me/tikz-http-mcp-server.git` 替换为实际的项目仓库地址)

2.  **运行部署脚本**:
    执行 `deploy.sh` 脚本来构建 Docker 镜像并启动服务。

    ```bash
    ./deploy.sh
    ```

    脚本将执行以下操作：
    *   检查 Docker 和 Docker Compose 是否安装。
    *   如果 Docker Compose 未安装，将尝试自动安装。
    *   从 `.env` 文件加载环境变量（如果存在）。
    *   构建名为 `tikz-mcp-server:latest` 的 Docker 镜像（镜像名称基于 `SERVICE_NAME`）。
    *   启动名为 `tikz-mcp-server-container` 的 Docker 容器（容器名称基于 `CONTAINER_NAME`）。
    *   等待服务启动并进行健康检查。

### 服务地址

服务成功启动后，您可以通过以下地址访问 MCP 服务器：

*   **MCP 服务端点**: `http://localhost:3000/mcp`

### MCP 客户端配置

项目根目录下的 `mcp_server_configs.json` 文件包含了不同 MCP 客户端（如 Claude Desktop, VSCode, Windsurf, Cline, Cursor）的服务器配置示例。您可以参考该文件，根据您使用的客户端类型进行相应的配置。

例如，以下是通用的 MCP 客户端配置示例：

```json
{
  "type": "http",
  "url": "http://localhost:3000/mcp",
  "transport": "streamable-http"
}
```

### 常用 Docker 命令

在服务部署后，您可以使用以下 Docker 命令来管理容器：

*   **查看日志**:
    ```bash
    docker logs tikz-mcp-server-container -f
    ```
*   **重启服务**:
    ```bash
    docker restart tikz-mcp-server-container
    ```
*   **停止服务**:
    ```bash
    docker stop tikz-mcp-server-container
    ```
*   **删除容器**:
    ```bash
    docker rm tikz-mcp-server-container