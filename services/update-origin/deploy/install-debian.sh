#!/bin/sh
set -eu

usage() {
    echo "Uso: sudo ./deploy/install-debian.sh HOSTNAME CHIAVE_PUBBLICA CERTIFICATO_TLS CHIAVE_TLS" >&2
    exit 2
}

[ "$#" -eq 4 ] || usage
[ "$(id -u)" -eq 0 ] || { echo "Esegui l'installer come root." >&2; exit 1; }

hostname=$1
public_key=$2
certificate=$3
certificate_key=$4

case "$hostname" in
    ''|.*|*..*|*.|*'-.'*|*'.-'*) echo "Hostname aggiornamenti non valido." >&2; exit 2 ;;
    *[!a-z0-9.-]*) echo "Hostname aggiornamenti non valido." >&2; exit 2 ;;
    *.*) ;;
    *) echo "L'hostname aggiornamenti deve essere un nome DNS completo." >&2; exit 2 ;;
esac
[ "${#hostname}" -le 253 ] || { echo "Hostname aggiornamenti troppo lungo." >&2; exit 2; }
old_ifs=$IFS
IFS=.
set -- $hostname
IFS=$old_ifs
for label in "$@"; do
    [ "${#label}" -le 63 ] || { echo "Etichetta DNS troppo lunga." >&2; exit 2; }
    case "$label" in
        -*|*-) echo "Etichetta DNS non valida." >&2; exit 2 ;;
    esac
done

for path in "$public_key" "$certificate" "$certificate_key"; do
    case "$path" in
        /*) ;;
        *) echo "I percorsi di chiavi e certificati devono essere assoluti." >&2; exit 2 ;;
    esac
    case "$path" in
        *[!A-Za-z0-9_./-]*) echo "Percorso non valido: $path" >&2; exit 2 ;;
    esac
    [ -f "$path" ] || {
        echo "File mancante o non regolare: $path" >&2
        exit 1
    }
done
[ ! -L "$public_key" ] || {
    echo "La chiave pubblica di release non può essere un link simbolico." >&2
    exit 1
}

. /etc/os-release
[ "${ID:-}" = debian ] && { [ "${VERSION_ID:-}" = 12 ] || [ "${VERSION_ID:-}" = 13 ]; } || {
    echo "Sono supportati soltanto Debian 12 e Debian 13." >&2
    exit 1
}
for command in nginx openssl python3 systemctl; do
    command -v "$command" >/dev/null 2>&1 || {
        echo "Dipendenza mancante: $command" >&2
        exit 1
    }
done

repository=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
install -d -o root -g root -m 0755 /usr/lib/homecloud-update-origin/homecloud_update_origin
for source in "$repository"/src/homecloud_update_origin/*.py; do
    install --remove-destination -o root -g root -m 0644 "$source" \
        "/usr/lib/homecloud-update-origin/homecloud_update_origin/$(basename -- "$source")"
done
install --remove-destination -D -o root -g root -m 0755 \
    "$repository/deploy/homecloud-update-origin" \
    /usr/local/sbin/homecloud-update-origin
install --remove-destination -D -o root -g root -m 0644 "$public_key" \
    /etc/homecloud-update-origin/release-signing-public.pem
[ ! -L /srv/homecloud-updates ] || {
    echo "La directory di pubblicazione non può essere un link simbolico." >&2
    exit 1
}
install -d -o root -g root -m 0755 /srv/homecloud-updates
health_stage=$(mktemp /srv/homecloud-updates/.healthz.XXXXXX)
trap 'rm -f "$health_stage"' EXIT HUP INT TERM
printf 'ok\n' > "$health_stage"
chown root:root "$health_stage"
chmod 0644 "$health_stage"
mv -T "$health_stage" /srv/homecloud-updates/healthz
trap - EXIT HUP INT TERM

nginx_config=/etc/nginx/sites-available/homecloud-updates.conf
nginx_enabled=/etc/nginx/sites-enabled/homecloud-updates.conf
for target in "$nginx_config" "$nginx_enabled"; do
    if { [ -e "$target" ] || [ -L "$target" ]; } \
        && [ ! -f "$target" ] && [ ! -L "$target" ]; then
        echo "Destinazione Nginx non sicura: $target" >&2
        exit 1
    fi
done
nginx_stage=$(mktemp /etc/nginx/sites-available/.homecloud-updates.XXXXXX)
nginx_backup=$(mktemp -d /etc/nginx/.homecloud-updates-backup.XXXXXX)
config_backed_up=false
enabled_backed_up=false

rollback_nginx() {
    rm -f "$nginx_stage" "$nginx_config" "$nginx_enabled"
    if [ "$config_backed_up" = true ]; then
        mv "$nginx_backup/config" "$nginx_config"
        config_backed_up=false
    fi
    if [ "$enabled_backed_up" = true ]; then
        mv "$nginx_backup/enabled" "$nginx_enabled"
        enabled_backed_up=false
    fi
    rmdir "$nginx_backup" 2>/dev/null || true
}

trap 'rollback_nginx' EXIT
trap 'exit 1' HUP INT TERM
python3 - "$repository/deploy/nginx-site.conf.in" "$nginx_stage" \
    "$hostname" "$certificate" "$certificate_key" <<'PY'
import pathlib
import sys

source, destination, hostname, certificate, certificate_key = sys.argv[1:]
text = pathlib.Path(source).read_text(encoding="utf-8")
text = text.replace("__HOSTNAME__", hostname)
text = text.replace("__CERTIFICATE__", certificate)
text = text.replace("__CERTIFICATE_KEY__", certificate_key)
pathlib.Path(destination).write_text(text, encoding="utf-8")
PY
chmod 0644 "$nginx_stage"
chown root:root "$nginx_stage"

if [ -e "$nginx_config" ] || [ -L "$nginx_config" ]; then
    mv "$nginx_config" "$nginx_backup/config"
    config_backed_up=true
fi
if [ -e "$nginx_enabled" ] || [ -L "$nginx_enabled" ]; then
    mv "$nginx_enabled" "$nginx_backup/enabled"
    enabled_backed_up=true
fi
mv "$nginx_stage" "$nginx_config"
ln -s "$nginx_config" "$nginx_enabled"

openssl pkey -pubin -in /etc/homecloud-update-origin/release-signing-public.pem \
    -noout >/dev/null
if ! nginx -t; then
    echo "Configurazione Nginx non valida; ripristino quella precedente." >&2
    exit 1
fi
trap - EXIT HUP INT TERM
rm -f "$nginx_backup/config" "$nginx_backup/enabled"
rmdir "$nginx_backup"
systemctl enable --now nginx.service
systemctl reload nginx.service

echo "Origine aggiornamenti installata per https://$hostname"
echo "La chiave privata di release non deve essere copiata su questo server."
