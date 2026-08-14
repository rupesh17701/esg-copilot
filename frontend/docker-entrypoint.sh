#!/bin/sh
# Renders the nginx config from a template (backend host/port are only known
# at runtime — e.g. Railway assigns internal service hostnames dynamically),
# and turns on HTTP Basic Auth only when BASIC_AUTH_USER/PASSWORD are set.
# Local docker-compose leaves these unset, so local dev stays auth-free.
set -e

export BACKEND_HOST="${BACKEND_HOST:-backend}"
export BACKEND_PORT="${BACKEND_PORT:-8000}"

envsubst '${BACKEND_HOST} ${BACKEND_PORT}' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf

if [ -n "$BASIC_AUTH_USER" ] && [ -n "$BASIC_AUTH_PASSWORD" ]; then
  htpasswd -bc /etc/nginx/.htpasswd "$BASIC_AUTH_USER" "$BASIC_AUTH_PASSWORD" >/dev/null
  printf 'auth_basic "ESG Copilot";\nauth_basic_user_file /etc/nginx/.htpasswd;\n' > /etc/nginx/auth.conf
  echo "Basic auth enabled for user '$BASIC_AUTH_USER'."
else
  : > /etc/nginx/auth.conf
  echo "BASIC_AUTH_USER/PASSWORD not set — running without auth."
fi

exec nginx -g 'daemon off;'
