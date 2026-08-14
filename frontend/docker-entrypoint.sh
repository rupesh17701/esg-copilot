#!/bin/sh
# Renders the nginx config from a template (backend host/port are only known
# at runtime — e.g. Railway assigns internal service hostnames dynamically),
# and turns on HTTP Basic Auth only when BASIC_AUTH_USER/PASSWORD are set.
# Local docker-compose leaves these unset, so local dev stays auth-free.
set -e

export BACKEND_HOST="${BACKEND_HOST:-backend}"
export BACKEND_PORT="${BACKEND_PORT:-8000}"

# nginx needs an explicit resolver IP to re-resolve BACKEND_HOST per request
# (see the comment in the template for why that matters). "resolver
# local=on" isn't supported by every nginx build, so read the container's
# actual DNS server straight out of /etc/resolv.conf instead — this works
# the same whether that's Docker's embedded DNS (127.0.0.11) or Railway's
# internal resolver, with nothing platform-specific hardcoded.
export RESOLVER_IP="$(awk '/^nameserver/{print $2; exit}' /etc/resolv.conf)"
if [ -z "$RESOLVER_IP" ]; then
  echo "WARNING: no nameserver found in /etc/resolv.conf; falling back to 127.0.0.11"
  export RESOLVER_IP="127.0.0.11"
fi
# nginx's resolver directive requires IPv6 addresses in brackets (it uses a
# bare trailing ":port" to mean a port override, which is ambiguous with the
# colons inside an unbracketed IPv6 address). Railway's internal resolver is
# IPv6 (e.g. fd12::10), so without this nginx fails to even start.
case "$RESOLVER_IP" in
  *:*) RESOLVER_IP="[$RESOLVER_IP]" ;;
esac
export RESOLVER_IP
echo "Using DNS resolver: $RESOLVER_IP"

envsubst '${BACKEND_HOST} ${BACKEND_PORT} ${RESOLVER_IP}' \
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
