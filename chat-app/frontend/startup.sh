#!/bin/sh

if [ -z "$VITE_API_BASE_URL" ]; then
  host="${WEBSITE_HOSTNAME:-}"
  case "$host" in
    app-chat-*.*)
      suf="${host#app-chat-}"
      VITE_API_BASE_URL="https://api-chat-${suf}"
      ;;
  esac
fi

cat > /usr/share/nginx/html/runtime-config.js << EOF
window.__RUNTIME_CONFIG__ = {
  VITE_API_BASE_URL: '${VITE_API_BASE_URL}'
};
EOF

nginx -g "daemon off;"
