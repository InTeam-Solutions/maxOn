# syntax=docker/dockerfile:1.6

FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install --silent

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG VITE_MAX_WEB_APP_SRC=https://static.maxhub.com/sdk/max-web-app.js
ENV VITE_MAX_WEB_APP_SRC=${VITE_MAX_WEB_APP_SRC}
RUN npm run build

FROM nginx:1.27-alpine AS runner
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 4173
CMD ["nginx", "-g", "daemon off;"]
