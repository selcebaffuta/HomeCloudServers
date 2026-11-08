#!/bin/sh
set -eu

command -v nginx >/dev/null 2>&1 || {
    echo "nginx non installato" >&2
    exit 1
}

temporary=$(mktemp -d)
trap 'rm -rf "$temporary"' EXIT HUP INT TERM
certificate="$temporary/certificate.pem"
certificate_key="$temporary/certificate-key.pem"
rendered="$temporary/site.conf"
configuration="$temporary/nginx.conf"

openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -subj /CN=updates.homecloud.test \
    -keyout "$certificate_key" -out "$certificate" >/dev/null 2>&1

python3 - \
    "$(dirname -- "$0")/../deploy/nginx-site.conf.in" "$rendered" \
    "$certificate" "$certificate_key" <<'PY'
import pathlib
import socket
import sys

source, destination, certificate, certificate_key = sys.argv[1:]
text = pathlib.Path(source).read_text(encoding="utf-8")
text = text.replace("__HOSTNAME__", "updates.homecloud.test")
text = text.replace("__CERTIFICATE__", certificate)
text = text.replace("__CERTIFICATE_KEY__", certificate_key)
# Some packaged versions also validate socket binding during -t. Keep the
# production TLS directives, but use test-only unprivileged loopback listeners.
def port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]
http_port, https_port = port(), port()
while https_port == http_port:
    https_port = port()
text = text.replace("listen 80;", f"listen 127.0.0.1:{http_port};")
text = text.replace("    listen [::]:80;", "")
text = text.replace("listen 443 ssl http2;", f"listen 127.0.0.1:{https_port} ssl http2;")
text = text.replace("    listen [::]:443 ssl http2;", "")
pathlib.Path(destination).write_text(text, encoding="utf-8")
PY

{
    echo "pid $temporary/nginx.pid;"
    echo "error_log stderr notice;"
    echo "events {}"
    echo "http {"
    # The distro default is /var/log/nginx/access.log, which the non-root CI
    # user cannot open. Keep the test hermetic; do not elevate nginx -t.
    echo "access_log $temporary/access.log;"
    echo "client_body_temp_path $temporary/body;"
    echo "proxy_temp_path $temporary/proxy;"
    echo "fastcgi_temp_path $temporary/fastcgi;"
    echo "uwsgi_temp_path $temporary/uwsgi;"
    echo "scgi_temp_path $temporary/scgi;"
    cat "$rendered"
    echo "}"
} > "$configuration"

nginx -e stderr -t -p "$temporary/" -c "$configuration"
