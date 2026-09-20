# HomeCloud Update Origin

Servizio di distribuzione degli aggiornamenti HomeCloud per Debian. La prima
versione è volutamente un'origine HTTPS statica: Nginx serve esclusivamente
piani già firmati e bundle content-addressed, mentre il comando di pubblicazione
verifica tutto prima di rendere una release visibile.

Non esiste una API amministrativa esposta a Internet e la chiave privata di
release non deve mai essere presente sul server.

## Confine di fiducia

```text
macchina di release offline
  crea bundle HomeCloud firmato
  crea release.json
  firma release.json
             |
             | trasferimento operatore
             v
server Debian
  verifica firma con chiave pubblica
  verifica schema, origine, hash e dimensione bundle
  impone sequence monotona per canale/piattaforma
  pubblica atomicamente file statici root-owned
             |
             v
Nginx HTTPS read-only
  /v1/stable/debian-13-arm64.json
  /v1/stable/debian-13-arm64.json.sig
  /releases/<sha256>.tar.gz
```

Una compromissione del server può causare indisponibilità o servire file
alterati, ma non può produrre un piano accettato dalle appliance senza la chiave
privata offline. Il client verifica inoltre scadenza, sequenza, piattaforma,
firma interna del bundle e policy di compatibilità inclusa in HomeCloud.

## Requisiti server

- Debian 12 o Debian 13;
- Python 3.11 o successivo;
- OpenSSL;
- Nginx;
- hostname DNS dedicato, per esempio `updates.example.com`;
- certificato TLS pubblico valido per tale hostname;
- copia della stessa chiave **pubblica** installata sulle appliance.

Il server può essere x86-64: gli artifact distribuiti rimangono destinati alle
appliance Debian ARM64.

## Installazione su Debian

Installare prima le dipendenze e predisporre DNS e certificato TLS:

```bash
sudo apt-get update
sudo apt-get install --yes nginx openssl python3
```

Poi, dalla directory `services/update-origin`:

```bash
sudo ./deploy/install-debian.sh \
  updates.example.com \
  /percorso/update-signing-public.pem \
  /etc/letsencrypt/live/updates.example.com/fullchain.pem \
  /etc/letsencrypt/live/updates.example.com/privkey.pem
```

L'installer:

- verifica Debian e le dipendenze;
- installa il publisher in `/usr/local/sbin/homecloud-update-origin`;
- copia la chiave pubblica in `/etc/homecloud-update-origin/`;
- crea `/srv/homecloud-updates` root-owned;
- installa un virtual host Nginx HTTPS che accetta soltanto GET/HEAD;
- convalida la configurazione prima del reload.

Non richiede né installa la chiave privata di release.

## Preparazione di una release

Costruire prima il bundle pubblicabile dal checkout HomeCloudSetup approvato,
dopo aver aggiornato lock, artifact e firma interna:

```bash
tools/sign-homecloud-update \
  --private-key /supporto-offline/update-signing-private.pem \
  /percorso/HomeCloudSetup
tools/build-homecloud-update-archive \
  --output /percorso/homecloud-release.tar.gz \
  /percorso/HomeCloudSetup
```

Creare quindi il piano. L'esempio non aggiorna pacchetti Linux:

```bash
PYTHONPATH=services/update-origin/src \
python3 -m homecloud_update_origin.cli prepare \
  --origin https://updates.example.com \
  --sequence 1 \
  --os-version 13 \
  --architecture arm64 \
  --commit 0123456789abcdef0123456789abcdef01234567 \
  --release-sequence 2 \
  --bundle /percorso/homecloud-release.tar.gz \
  --output /percorso/release.json
```

Per autorizzare un pacchetto necessario al runtime o alla sicurezza, aggiungere
una opzione per ogni versione esatta:

```bash
--package 'openssl=3.5.1-1=security'
```

Il publisher ordina i pacchetti e il client rifiuta nomi non presenti nella
policy della release HomeCloud. Non usare questo meccanismo per aggiornamenti
generali della distribuzione.

Firmare `release.json` sulla macchina offline:

```bash
openssl dgst -sha256 \
  -sign /supporto-offline/update-signing-private.pem \
  -out /percorso/release.json.sig \
  /percorso/release.json
```

Trasferire sul server soltanto bundle, piano e firma detached.

## Pubblicazione

Sul server Debian:

```bash
sudo homecloud-update-origin publish \
  --origin https://updates.example.com \
  --channel stable \
  --plan /staging/release.json \
  --signature /staging/release.json.sig \
  --bundle /staging/homecloud-release.tar.gz
```

La pubblicazione viene serializzata con un lock locale. Prima dello switch
vengono verificati:

- file regolari senza symlink;
- firma RSA-SHA256;
- schema esatto del piano;
- HTTPS e origine del bundle;
- hash e dimensione del bundle;
- piattaforma Debian supportata;
- pacchetti univoci, ordinati e classificati `runtime` o `security`;
- crescita strettamente monotona di `sequence`.

Bundle e piani storici sono conservati con nomi content-addressed. Il puntatore
del canale viene aggiornato con replace atomici; durante il brevissimo switch un
client concorrente può al massimo osservare una firma non corrispondente e
riprovare, mai accettare contenuto non firmato.

## Configurazione appliance

Per Debian 13 ARM64, il file root-owned
`/etc/homecloud/update-source.json` diventerà:

```json
{
  "schema": 1,
  "enabled": true,
  "metadata_url": "https://updates.example.com/v1/stable/debian-13-arm64.json",
  "allowed_hosts": ["updates.example.com"]
}
```

Per Debian 12 usare `debian-12-arm64.json`. Questa configurazione deve essere
applicata in fabbrica o tramite un aggiornamento già autenticato; non è
modificabile dalla Web UI.

## Stato del primo traguardo

Implementato:

- generazione deterministica del piano da firmare;
- validazione compatibile con il client HomeCloudSetup;
- verifica firma e pubblicazione atomica;
- protezione da downgrade/replay del canale;
- origine statica Nginx installabile su Debian;
- test senza dipendenze Python esterne.

Non ancora implementato:

- mirror/repository APT HomeCloud;
- pipeline CI di promozione staging → stable;
- rotazione coordinata della chiave di release;
- telemetria aggregata e anonima sugli esiti;
- replica geografica e disaster recovery.

Fino alla realizzazione del mirror APT, il piano HomeCloud autorizza versioni
esatte ma i `.deb` continuano a provenire dai repository APT firmati già
configurati sulle appliance.

## Test

```bash
PYTHONPATH=services/update-origin/src \
python3 -m unittest discover -s services/update-origin/tests -v
```
