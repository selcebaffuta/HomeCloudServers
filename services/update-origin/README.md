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

Le chiavi pubbliche release vengono conservate per digest in
`/etc/homecloud-update-origin/release-keys.d/`. Rieseguire l'installer con una
nuova chiave durante l'overlap la aggiunge senza sostituire quella legacy. Le
vecchie chiavi pubbliche non sono segrete e servono a verificare la storia.

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

## Promozione staging → stable

Pubblicare e collaudare prima la release su `staging`, quindi promuoverla senza
ricostruire o riscaricare nulla:

```bash
sudo homecloud-update-origin publish \
  --origin https://updates.example.com \
  --channel staging \
  --plan /staging/release.json \
  --signature /staging/release.json.sig \
  --bundle /staging/homecloud-release.tar.gz

sudo homecloud-update-origin promote \
  --origin https://updates.example.com \
  --platform debian-13-arm64
```

La promozione riusa byte per byte piano e firma staging. Il canale non è parte
del documento firmato: generare un nuovo JSON stable richiederebbe una seconda
firma e creerebbe due dichiarazioni per lo stesso artefatto. Prima dello switch
il comando riverifica firma, scadenza, piattaforma, hash e dimensione del bundle,
nonché la monotonia di stable. Il lock è lo stesso del publisher.

L'audit append-only locale è in
`/srv/homecloud-updates/.audit/promotion.jsonl`, mode `0600`, e viene sincronizzato
prima dello switch. Non è un log anti-manomissione contro root: deve essere
esportato nei backup operativi.

Il protocollo v1 usa JSON e firma detached, quindi non può sostituire la coppia
con un singolo rename. Ogni file usa temp+`fsync`+rename; durante lo switch una
coppia incoerente fallisce sempre la verifica. Il piano viene scritto prima
della firma, così un retry idempotente ripara in sicurezza un'interruzione tra i
due rename. Una futura v2 potrà usare un envelope firmato singolo.

## Rotazione coordinata delle chiavi

La release key e la **trust root** sono ruoli differenti. La trust root privata
rimane offline e firma soltanto `trust.json`; il server pubblico riceve la sua
chiave pubblica. Una nuova release key viene accettata dai client solo se inclusa
in metadata trust root-signed con sequence monotona.

Preparare offline i metadata di overlap:

```bash
homecloud-update-origin prepare-trust \
  --sequence 1 \
  --root-public-key /supporto-offline/trust-root-public.pem \
  --active-key /supporto-offline/release-old-public.pem \
  --active-key /supporto-offline/release-new-public.pem \
  --output /staging/trust.json

openssl dgst -sha256 \
  -sign /supporto-offline/trust-root-private.pem \
  -out /staging/trust.json.sig \
  /staging/trust.json
```

Sul server si pubblicano soltanto metadata, firma e chiave root **pubblica**:

```bash
sudo homecloud-update-origin publish-trust \
  --origin https://updates.example.com \
  --channel stable \
  --root-public-key /staging/trust-root-public.pem \
  --metadata /staging/trust.json \
  --signature /staging/trust.json.sig
```

Il client aggiornato deriva `/v1/stable/trust.json` dall'URL del piano, verifica
la firma con `/etc/homecloud/update-trust-root.pem` e conserva in un singolo file
atomico payload e firma. Impone:

- sequence trust monotona e scadenza;
- stesso contenuto per una sequence già vista;
- chiavi RSA valide e identificate dall'hash del PEM;
- almeno una release key attiva;
- revoca esplicita e irreversibile;
- firma del piano e del bundle con una chiave ancora attiva.

La trust root viene installata in fabbrica con:

```bash
sudo ./install-appliance.sh \
  --update-trust-root /supporto-offline/trust-root-public.pem
```

L'installer HomeCloudSetup rifiuta di sostituire automaticamente una root già
presente. Durante l'overlap conservare old e new come `active`, distribuire e
verificare il client, iniziare a firmare con new, quindi pubblicare una sequence
successiva con old `revoked`. Non cancellare old dai metadata: la revoca deve
restare esplicita.

Limite importante: gli agenti già distribuiti che conoscono soltanto la vecchia
release key non sanno interpretare la trust root. Il normale tarball HomeCloud
non aggiorna il codice privilegiato `homecloud_setup`; questi device richiedono
una reinstallazione/aggiornamento autenticato dell'agente prima della revoca.
Se la vecchia private key viene compromessa prima della migrazione, tali device
richiedono recupero factory o fisico: il server non può risolvere in sicurezza
questa assenza di trust anchor.

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
- promozione staging → stable verificata, idempotente e auditata;
- keyring release con overlap e metadata trust root-signed;
- revoca irreversibile e protezione rollback del trust store client;
- test senza dipendenze Python esterne.

Non ancora implementato:

- mirror/repository APT HomeCloud;
- telemetria aggregata e anonima sugli esiti;
- replica geografica automatizzata e restore drill automatizzati.

Fino alla realizzazione del mirror APT, il piano HomeCloud autorizza versioni
esatte ma i `.deb` continuano a provenire dai repository APT firmati già
configurati sulle appliance.

## Test

```bash
PYTHONPATH=services/update-origin/src \
python3 -m unittest discover -s services/update-origin/tests -v
```

La CI installa inoltre Nginx e valida la configurazione renderizzata con un
certificato effimero tramite `tests/check-nginx.sh`, senza privilegi e con
log/directory temporanee isolate. Prove HTTPS reali opt-in verificano endpoint,
byte firmati, artifact/hash/size, errori, cache, metodi e verifica TLS; gli stessi
controlli Nginx girano anche in container Debian12/13 disposable.

Gli artifact riusciti (200/206/304) sono immutable; gli errori sono `no-store`,
come health e metadata. Non si conserva una risposta404 come artifact immutabile.
Nessuna chiave privata reale, release installabile o servizio production è usato
nei test. [Diagnosi CI, copertura e compatibilità client](docs/ci-and-client-compatibility.md)
distinguono verifiche automatiche, revisione del contratto e gate appliance aperti.

## Operazioni e sviluppi futuri

- [Disaster recovery](docs/disaster-recovery.md)
- [Design del futuro repository APT](docs/apt-repository-design.md)
