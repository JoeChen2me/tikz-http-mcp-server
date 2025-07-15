# 使用Ubuntu作为基础镜像，包含完整的LaTeX环境
FROM ubuntu:22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    # Python环境
    python3 \
    python3-pip \
    python3-venv \
    # LaTeX环境
    texlive-full \
    # ImageMagick用于图像转换
    imagemagick \
    # 字体支持
    fonts-noto-cjk \
    fonts-lmodern \
    # 其他工具
    curl \
    wget \
    git \
    dumb-init \
    && rm -rf /var/lib/apt/lists/*

# 修复ImageMagick策略以允许PDF转换
RUN sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml || \
    sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick/policy.xml || true

# 创建应用目录
WORKDIR /app

# 复制应用文件
COPY tikz_http_server.py ./
COPY clean_images.py ./
COPY run.sh ./
RUN chmod +x run.sh

# 安装Python依赖
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir mcp starlette uvicorn click anyio

# 创建非root用户以提升安全性
RUN useradd -m -u 1000 tikz && \
    chown -R tikz:tikz /app
USER tikz

# 暴露端口
EXPOSE 3000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import requests; requests.post('http://localhost:3000/mcp/', json={'method':'tools/list', 'params':{}})" || exit 1

# 启动命令
CMD ["dumb-init", "./run.sh"]