# --- Build stage -----------------------------------------------------------
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vite env vars are compile-time (baked into the static bundle), so this
# has to be a build ARG, not a runtime environment variable — a container
# started from the built image can't change it afterward.
ARG VITE_GOOGLE_CLIENT_ID=
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID
RUN npm run build

# --- Serve stage -------------------------------------------------------------
# nginx's current stable line (the stable-alpine tag pointed at 1.30 in
# 2026-10); 1.27 and 1.28 get no more fixes. nginx.conf uses only
# long-standing directives. Move to the next stable line each spring.
FROM nginx:1.30-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY security-headers.conf /etc/nginx/snippets/security-headers.conf
EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=6 \
    CMD wget -qO- http://localhost/ >/dev/null || exit 1
