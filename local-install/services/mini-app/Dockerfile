# syntax=docker/dockerfile:1.6

FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --silent

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG VITE_MAX_WEB_APP_SRC=https://static.maxhub.com/sdk/max-web-app.js
ARG VITE_CORE_API_URL=http://localhost:8104
ARG VITE_ORCHESTRATOR_API_URL=http://localhost:8101
ARG VITE_USE_REAL_API=false
ENV VITE_MAX_WEB_APP_SRC=${VITE_MAX_WEB_APP_SRC}
ENV VITE_CORE_API_URL=${VITE_CORE_API_URL}
ENV VITE_ORCHESTRATOR_API_URL=${VITE_ORCHESTRATOR_API_URL}
ENV VITE_USE_REAL_API=${VITE_USE_REAL_API}
RUN npm run build

FROM nginx:1.27-alpine AS runner
# Copy custom nginx config
RUN echo 'server { \n\
    listen 80; \n\
    location / { \n\
        root /usr/share/nginx/html; \n\
        index index.html index.htm; \n\
        try_files $uri $uri/ /index.html; \n\
    } \n\
}' > /etc/nginx/conf.d/default.conf

COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
