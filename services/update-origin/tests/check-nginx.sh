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
import sys

source, destination, certificate, certificate_key = sys.argv[1:]
text = pathlib.Path(source).read_text(encoding="utf-8")
text = text.replace("__HOSTNAME__", "updates.homecloud.test")
text = text.replace("__CERTIFICATE__", certificate)
text = text.replace("__CERTIFICATE_KEY__", certificate_key)
pathlib.Path(destination).write_text(text, encoding="utf-8")
PY

{
    echo "pid $temporary/nginx.pid;"
    echo "error_log stderr notice;"
    echo "events {}"
    echo "http {"
    cat "$rendered"
    echo "}"
} > "$configuration"

nginx -t -p "$temporary/" -c "$configuration"
