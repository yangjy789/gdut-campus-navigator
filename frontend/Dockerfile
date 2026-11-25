# 前端镜像：Node 构建静态产物，nginx 托管并反代 /api 到后端。
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
# 使用国内 npm 镜像，便于在国内网络环境构建（可通过 NPM_REGISTRY 构建参数覆盖）。
ARG NPM_REGISTRY=https://registry.npmmirror.com
RUN npm ci --registry "$NPM_REGISTRY"
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
