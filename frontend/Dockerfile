# ============================
# Stage 1: Build
# ============================
FROM node:18-alpine AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

# ============================
# Stage 2: Runtime (nginx)
# ============================
FROM nginx:stable-alpine AS production
EXPOSE 8080
COPY --from=builder /app/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
