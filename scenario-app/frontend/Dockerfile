FROM mcr.microsoft.com/azurelinux/base/nodejs:20 AS widget-builder
WORKDIR /src/chat-app/frontend
COPY chat-app/frontend/package*.json ./
RUN npm ci --legacy-peer-deps
COPY chat-app/frontend/ ./
RUN npm run build

FROM mcr.microsoft.com/azurelinux/base/nodejs:20 AS app-builder
WORKDIR /src/scenario-app/frontend
ARG VITE_SCENARIO=ecommerce
ENV VITE_SCENARIO=$VITE_SCENARIO
COPY scenario-app/frontend/package*.json ./
RUN npm ci --legacy-peer-deps
COPY scenario-app/frontend/ ./
RUN npm run build
COPY --from=widget-builder /src/chat-app/frontend/dist/widget.js ./dist/widget.js

FROM mcr.microsoft.com/azurelinux/base/nginx:1.25
COPY --from=app-builder /src/scenario-app/frontend/dist /usr/share/nginx/html
COPY scenario-app/frontend/nginx.conf /etc/nginx/nginx.conf
COPY scenario-app/frontend/startup.sh /docker-entrypoint.d/startup.sh
RUN chmod +x /docker-entrypoint.d/startup.sh
RUN sed -i 's/\r$//' /docker-entrypoint.d/startup.sh
EXPOSE 80
CMD ["/bin/sh", "-c", "/docker-entrypoint.d/startup.sh"]
