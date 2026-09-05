# ============ 阶段 1：构建 React 前端 ============
FROM node:18-alpine AS frontend-build
WORKDIR /app/frontend

# 先复制依赖清单，利用 Docker 层缓存
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

# 复制前端源码并构建
COPY frontend/ ./
RUN npm run build

# ============ 阶段 2：后端运行镜像 ============
FROM python:3.11-slim

WORKDIR /app

# 安装 Python 依赖（3.11 下 pandas/numpy 等均有预编译 wheel，无需编译工具链）
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端源码与内置数据
COPY config/ ./config/
COPY src/ ./src/
COPY data/ ./data/

# 复制前端构建产物（由 FastAPI 统一托管）
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# 确保报告输出目录存在
RUN mkdir -p data/output

EXPOSE 8000

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
