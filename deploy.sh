#!/bin/bash
echo "🚀 正在部署TikZ HTTP MCP服务器..."

# 检查Docker是否安装
if ! command -v docker > /dev/null 2>&1; then
    echo "❌ 请先安装Docker"
    exit 1
fi

# 检查Docker Compose是否安装
if ! command -v docker-compose > /dev/null 2>&1; then
    echo "📦 正在安装Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose 2>/dev/null || {
        echo "❌ Docker Compose安装失败，请手动安装"
        exit 1
    }
    chmod +x /usr/local/bin/docker-compose
fi

# 检查配置文件是否存在
if [ ! -f "docker-compose.simple.yml" ]; then
    echo "❌ 找不到docker-compose.simple.yml文件"
    exit 1
fi

# 构建并启动服务
# 设置默认值
DEFAULT_SERVICE_NAME="tikz-mcp-server"
DEFAULT_CONTAINER_NAME="tikz-mcp-server-container"

# 尝试从 .env 文件加载变量
if [ -f .env ]; then
    echo "📄 正在加载 .env 文件..."
    source .env
fi

# 使用 .env 中的值或默认值
SERVICE_NAME="${SERVICE_NAME:-${DEFAULT_SERVICE_NAME}}"
CONTAINER_NAME="${CONTAINER_NAME:-${DEFAULT_CONTAINER_NAME}}"
IMAGE_NAME="${SERVICE_NAME}:latest" # 镜像名称基于服务名称

BUILD_FLAG=""


# 检查镜像是否存在
if docker images -q "${IMAGE_NAME}" > /dev/null 2>&1; then
    echo "🔍 检测到镜像 ${IMAGE_NAME} 已存在。"
    read -p "是否重新构建镜像？(y/N，默认为否): " -n 1 -r REBUILD_CHOICE
    echo # 换行
    if [[ ${REBUILD_CHOICE} =~ ^[Yy]$ ]]; then
        BUILD_FLAG="--build"
        echo "✅ 用户选择重新构建镜像。"
    else
        echo "⏭️  跳过镜像重新构建，使用现有镜像。"
    fi
else
    echo "✨ 镜像 ${IMAGE_NAME} 不存在，将进行构建。"
    BUILD_FLAG="--build"
fi

echo "🏗️  正在构建和启动容器..."
docker-compose -f docker-compose.simple.yml up -d ${BUILD_FLAG}

# 等待服务启动
echo "⏳ 等待服务启动..."
for i in {1..30}; do
    if curl -s -X POST http://localhost:3000/mcp \
      -H "Content-Type: application/json" \
      -d '{"method":"tools/list","params":{}}' > /dev/null 2>&1; then
        echo "✅ 服务启动成功！"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ 服务启动超时，请检查日志："
        docker logs ${CONTAINER_NAME}
        exit 1
    fi
    sleep 1
done

# 显示部署结果
echo ""
echo "🎉 部署完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 服务地址: http://localhost:3000/mcp"
echo "✅ 健康检查: http://localhost:3000/mcp"
echo ""
echo "📋 MCP客户端配置："
echo "{"
echo '  "type": "http",'
echo '  "url": "http://localhost:3000/mcp",'
echo '  "transport": "streamable-http"'
echo "}"
echo ""
echo "🔧 常用命令："
echo "  查看日志: docker logs ${CONTAINER_NAME} -f"
echo "  重启服务: docker restart ${CONTAINER_NAME}"
echo "  停止服务: docker stop ${CONTAINER_NAME}"
echo "  删除容器: docker rm ${CONTAINER_NAME}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 显示容器状态
docker ps -a -f name=${CONTAINER_NAME}