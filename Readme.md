# TikZ HTTP MCP 服务器

## 声明  
项目来自于一个现有的开源项目：[tikz-mcp-server](https://github.com/ChaNg1o1/tikz-mcp-server)  
- 本项目在其基础上，增加了HTTP-Streamable接口，实现了远程部署。  
- 增加了一键部署脚本，实现自定义的一键部署。

这是一个基于 Model Context Protocol (MCP) 的 HTTP 服务器，专门用于将 TikZ/LaTeX 代码渲染成高质量的 PNG 图像。它提供了一个 `render_tikz` 工具，允许客户端通过 HTTP 请求提交 TikZ 代码并接收渲染后的图像。  

兼容 `Cherry Studio`客户端


## 功能特性

*   **TikZ 渲染**: 将 TikZ/LaTeX 代码编译为 PNG 图像，并支持直接返回 base64 编码的图像数据或可访问的图片 URL。
*   **MCP 兼容**: 作为 MCP 服务器运行，提供 `render_tikz_base64`、`render_tikz_url` 和 `install_tex_package` 三种工具。
*   **图片自动清理**: 生成的图片会定期自动清理，默认为 1 天。
*   **最小化镜像**: 提供最小化的 Docker 镜像，仅包含必要的 TeX 包，大幅减少镜像大小。
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
*   `PORT`: 服务监听的外部端口，默认为 `3000`。
*   `PUBLIC_IP`: 公网IP地址，用于生成图片URL，默认为 `localhost`。
*   `PUBLIC_PORT`: 公网端口，用于生成图片URL，默认为 `3000`。
*   `DOMAIN`: （可选）域名，如果设置将优先使用HTTPS域名生成图片URL，例如 `https://tikz.yourdomain.com`

### 部署步骤

#### 完整镜像部署（包含所有TeX包，体积较大）

1.  **克隆仓库** (如果尚未克隆):
    ```bash
    git clone git@github.com:JoeChen2me/tikz-http-mcp-server.git
    cd tikz-http-mcp-server
    ```

2.  **运行部署脚本**:
    首先，确保 `deploy.sh` 脚本具有执行权限：
    ```bash
    chmod +x deploy.sh
    ```
    然后，执行 `deploy.sh` 脚本来构建 Docker 镜像并启动服务：

    ```bash
    ./deploy.sh
    ```

#### 最小化镜像部署（仅包含必要TeX包，体积较小）

1.  **运行最小化部署脚本**:
    首先，确保 `deploy-minimal.sh` 脚本具有执行权限：
    ```bash
    chmod +x deploy-minimal.sh
    ```
    然后，执行脚本来构建最小化 Docker 镜像：

    ```bash
    ./deploy-minimal.sh
    ```

### 镜像大小对比
- **完整镜像**: ~2-3GB（包含完整TeX Live）
- **最小化镜像**: ~500-800MB（仅包含必要包）

## 本地测试运行

### 前提条件
在本地运行Python脚本需要安装以下依赖：

#### 系统依赖（macOS/Linux）
```bash
# macOS
brew install imagemagick mactex

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y texlive-xetex texlive-latex-recommended texlive-pictures imagemagick fonts-noto-cjk

# CentOS/RHEL
sudo yum install -y texlive-xetex texlive-latex-recommended texlive-pictures ImageMagick fonts-noto-cjk
```

#### Python依赖
```bash
pip install mcp starlette uvicorn click anyio
```

### 本地启动测试

1. **创建图片目录**
   ```bash
   mkdir -p images
   ```

2. **启动服务器**
   ```bash
   python3 tikz_http_server.py --port 3000 --log-level INFO
   ```

3. **测试工具列表**
   ```bash
   curl -X POST http://localhost:3000/mcp \
     -H "Content-Type: application/json" \
     -d '{"method":"tools/list","params":{}}'
   ```

4. **测试TikZ渲染**
   ```bash
   curl -X POST http://localhost:3000/mcp \
     -H "Content-Type: application/json" \
     -d '{
       "method":"tools/call",
       "params":{
         "name":"render_tikz_base64",
         "arguments":{"tikz_code":"\\begin{tikzpicture}\\draw (0,0) circle (1cm);\\end{tikzpicture}"}
       }
     }'
   ```

5. **测试安装TeX包**（仅当需要时）
   ```bash
   curl -X POST http://localhost:3000/mcp \
     -H "Content-Type: application/json" \
     -d '{
       "method":"tools/call",
       "params":{
         "name":"install_tex_package",
         "arguments":{"package_name":"pgfplots"}
       }
     }'
   ```

### 环境变量
本地运行时可以使用以下环境变量：
- `PUBLIC_IP`: 公网IP地址（默认：localhost）
- `PUBLIC_PORT`: 公网端口（默认：3000）
- `LOG_LEVEL`: 日志级别（默认：INFO）

示例：
```bash
PUBLIC_IP=localhost PUBLIC_PORT=3000 python3 tikz_http_server.py
```

    脚本将执行以下操作：
    *   检查 Docker 和 Docker Compose 是否安装。
    *   如果 Docker Compose 未安装，将尝试自动安装。
    *   从 `.env` 文件加载环境变量（如果存在）。
    *   **检查容器是否已在运行，如果存在则停止并删除。**
    *   构建名为 `tikz-mcp-server:latest` 的 Docker 镜像（`docker-compose.simple.yml` 已明确指定使用项目根目录下的 `Dockerfile` 进行构建）。镜像名称基于 `SERVICE_NAME`。
    *   启动名为 `tikz-mcp-server-container` 的 Docker 容器（容器名称基于 `CONTAINER_NAME`），并将容器内部的 `3000` 端口映射到外部的 `${PORT}` 端口。
    *   等待服务启动并进行健康检查。

### 服务地址

服务成功启动后，您可以通过以下地址访问 MCP 服务器：

*   **MCP 服务端点**: `http://localhost:${PORT}/mcp/`

### MCP 工具使用说明

服务器提供了以下三个工具：

1. **render_tikz_base64**: 将TikZ代码渲染为PNG并返回base64编码
2. **render_tikz_url**: 将TikZ代码渲染为PNG并返回可访问的URL
3. **install_tex_package**: 安装额外的TeX包（最小化镜像特别有用）

#### 安装TeX包示例
当使用最小化镜像时，如果缺少特定TeX包，可以使用`install_tex_package`工具：

```json
{
  "package_name": "pgfplots"
}
```

支持的包名示例：
- `pgfplots` - 用于绘制函数图表
- `tikz-cd` - 用于交换图
- `tkz-euclide` - 用于欧式几何
- `circuitikz` - 用于电路图

### MCP 客户端配置

项目根目录下的 `mcp_server_configs.json` 文件包含了不同 MCP 客户端（如 Claude Desktop, VSCode, Windsurf, Cline, Cursor）的服务器配置示例。您可以参考该文件，根据您使用的客户端类型进行相应的配置。

例如，以下是通用的 MCP 客户端配置示例：

```json
{
  "type": "http",
  "url": "http://localhost:${PORT}/mcp/",
  "transport": "streamable-http"
}
```

### 常用 Docker 命令

#### 完整镜像命令
在服务部署后，您可以使用以下 `docker-compose` 命令来管理服务：

*   **查看日志**:
    ```bash
    docker-compose -f docker-compose.simple.yml logs -f
    ```
*   **重启服务**:
    ```bash
    docker-compose -f docker-compose.simple.yml restart
    ```
*   **停止服务**:
    ```bash
    docker-compose -f docker-compose.simple.yml stop
    ```
*   **删除服务容器**:
    ```bash
    docker-compose -f docker-compose.simple.yml down
    ```

#### 最小化镜像命令
*   **查看日志**:
    ```bash
    docker-compose -f docker-compose.minimal.yml logs -f
    ```
*   **重启服务**:
    ```bash
    docker-compose -f docker-compose.minimal.yml restart
    ```
*   **停止服务**:
    ```bash
    docker-compose -f docker-compose.minimal.yml stop
    ```
*   **删除服务容器**:
    ```bash
    docker-compose -f docker-compose.minimal.yml down
    ```

### 域名配置与开发说明

#### 域名配置
当使用反向代理（如nginx）时，可以通过设置域名来生成HTTPS格式的图片URL：

1. **配置域名**：在`.env`文件中设置域名
   ```bash
   DOMAIN=https://tikz.yourdomain.com
   ```

2. **重启服务**：
   ```bash
   docker-compose -f docker-compose.minimal.yml restart
   ```

#### 开发热更新
为了便于开发，所有脚本文件已通过volume映射到容器内：

- **映射文件**：
  - `tikz_http_server.py` → `/app/tikz_http_server.py`
  - `clean_images.py` → `/app/clean_images.py`
  - `run.sh` → `/app/run.sh`

- **热更新流程**：
  1. 直接修改本地文件
  2. 运行 `docker-compose -f docker-compose.minimal.yml restart`
  3. 无需重新构建镜像即可生效

#### CORS支持
已添加全面的CORS头支持，允许所有来源访问图片资源，解决了跨域加载问题。