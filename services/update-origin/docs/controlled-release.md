# Pubblicazione controllata di una release v1

Usare questa procedura prima su un origin isolato e due appliance di prova.
CI usa soltanto chiavi effimere e artifact sintetici: una CI verde non
autorizza una pubblicazione. L'origin pubblico resta statico e riceve
esclusivamente artifact già firmati e chiavi pubbliche di firma release/trust.

## 1. Qualificare la destinazione e costruire offline

Per ogni canale e piattaforma, registrare fuori dall'origin l'ultima coppia
approvata: `sequence` del piano, `release_sequence` del runtime, commit, digest
del piano e del bundle, firma e stato trust. Verificare spazio per staging e
copia pubblica, orario UTC, scadenza del piano e della trust policy, DNS, TLS
e disponibilità dei backup.

| Destinazione | Cosa verifica v1 | Condizione operativa |
| --- | --- | --- |
| Pi4 con Debian 12/13 ARM64 | OS, versione e architettura esatti | Bundle con lock e firma interna accettati da Setup; prova di installazione e aggiornamento Pi4. |
| Pi5 con Debian 12/13 ARM64 | La stessa terna; nessun campo board | `homecloud-lock.json`/bundle validator di Setup main accettano l'origine del repository HomeCloud, non il repository separato HomeCloud-pi5. Non distribuire un payload specifico Pi5 con un piano generico. |
| Raspberry Pi OS identificato come `raspbian-12` | Identità distinta da `debian-12` | Nessun endpoint origin v1 corrispondente. Non rinominare la piattaforma per far passare il controllo. |

Il confronto in sola lettura ha trovato la stessa policy
`homecloud/update_compatibility.json` (schema 1, release_sequence 1) nei riferimenti
`HomeCloud/42339dc` e `HomeCloud-pi5/ad9e355`. Questo prova l'allineamento
della policy, non l'intercambiabilità dei payload. Per distribuire un bundle
comune occorre la prova dello **stesso** bundle firmato su entrambi i target,
con agente Setup supportato e compatibilità di pacchetti, kernel e runtime.
Per bundle distinti serve prima un contratto di destinazione coordinato tra
Setup e origin; v1 non firma il canale e una URL separata non vincola
crittograficamente il piano a una scheda.

Usare i tool di [preparazione bundle e piano](../README.md#preparazione-di-una-release).
Leggere commit e `release_sequence` dalla release costruita; non inventare
valori nel piano. Assegnare una `sequence` superiore per un nuovo piano e
aumentare `release_sequence` quando cambia il commit. Un rinnovo del piano
o un aggiornamento dei soli pacchetti conserva commit e `release_sequence`.
Usare la chiave RSA autorizzata dalla flotta e mantenere la chiave privata offline.

Per ogni pacchetto, approvare **nome, versione Debian esatta e motivazione**
contro la policy firmata della release e verificare sull'immagine candidata
che la versione sia presente nei repository APT firmati configurati. Su
fixture isolate controllare con `apt-cache policy NOME` e simulare la
transazione con `apt-get --simulate install --only-upgrade --no-remove NOME=VERSIONE ...`.
Non ammettere downgrade, rimozioni o variazioni non nel piano. Il publisher
valida formato, unicità e vincolo al commit, non la disponibilità di una
versione APT né il contenuto interno del bundle. L'agente Setup verifica firma
interna/lock, controlla la release attiva, ripete i controlli APT e verifica
la versione installata; il mirror APT HomeCloud non è presente.

## 2. Pubblicare in staging e verificare i byte ricevuti

Trasferire i tre file già firmati, verificare che provengano dal job offline
approvato e pubblicare con `publish --channel staging` come descritto nel
[README](../README.md#promozione-staging--stable). Salvare la ricevuta JSON
del publisher, in particolare `plan_sha256`, prima del collaudo. Verificare
`/healthz` e scaricare piano, firma e bundle dal dominio TLS autorizzato
senza seguire redirect; verificare da un secondo host con la chiave **già**
approvata, senza acquisirla dallo stesso origin.

Esempio per il candidato Debian 13, in una directory nuova e privata:

```sh
set -eu
umask 077
origin=https://updates.example.com
channel=staging
platform=debian-13-arm64
expected_plan_sha256=SHA256_DELLA_RICEVUTA_APPROVATA
public_key=/percorso-fidato/release-signing-public.pem

endpoint="$origin/v1/$channel/$platform.json"
curl --fail --silent --show-error --proto '=https' --max-time 30 -o release.json "$endpoint"
curl --fail --silent --show-error --proto '=https' --max-time 30 -o release.json.sig "$endpoint.sig"
printf '%s  release.json\n' "$expected_plan_sha256" | sha256sum -c -
openssl dgst -sha256 -verify "$public_key" -signature release.json.sig \
  -sigopt rsa_padding_mode:pkcs1 release.json

# Leggere i dati solo dal manifest autenticato. Validare schema, origine,
# piattaforma e scadenza con il codice del checkout verificato.
PYTHONPATH=/checkout/HomeCloudServers/services/update-origin/src \
python3 - "$origin" "$platform" > bundle-fields <<'PY'
import json
import sys
from pathlib import Path
from homecloud_update_origin.model import platform_key, validate_plan

plan = validate_plan(json.loads(Path("release.json").read_bytes()), sys.argv[1])
if platform_key(plan["platform"]) != sys.argv[2]:
    raise SystemExit("Piattaforma non corrispondente")
bundle = plan["homecloud"]
print(bundle["bundle_sha256"], bundle["bundle_size"])
PY
read -r bundle_sha256 bundle_size < bundle-fields
curl --fail --silent --show-error --proto '=https' --max-time 600 \
  --max-filesize "$bundle_size" -o bundle.tar.gz "$origin/releases/$bundle_sha256.tar.gz"
test "$(wc -c < bundle.tar.gz)" -eq "$bundle_size"
printf '%s  bundle.tar.gz\n' "$bundle_sha256" | sha256sum -c -
```

Verificare anche policy trust e firma con la trust root pubblica preinstallata
se la flotta usa la rotazione, e verificare con l'agente su appliance
disposable l'aggiornamento, la salute e il rollback applicativo. Il semplice
download non verifica questi passaggi.

## 3. Promuovere esattamente il piano collaudato

```sh
sudo homecloud-update-origin promote \
  --origin https://updates.example.com --platform debian-13-arm64 \
  --source-channel staging --target-channel stable \
  --expected-plan-sha256 "$expected_plan_sha256"
```

Usare sempre il digest approvato nel flusso controllato: il comando lo
confronta sotto lo stesso lock del publisher; se staging è cambiato, stable
resta intatto. L'opzione è facoltativa solo per compatibilità con le
automazioni esistenti. Ripetere la verifica HTTPS su stable usando lo stesso
digest e conservare ricevuta e audit. Non usare `publish --channel stable`
come scorciatoia operativa.

Il publisher installa prima il bundle content-addressed e la coppia storica,
sincronizza file e directory, poi aggiorna i riferimenti del canale.
Per la promozione, l'audit locale è sincronizzato prima dello switch. Ogni
rename è atomico; con **due URL separati** non c'è atomicità della coppia
vista dal client. Un 404 o una firma incoerente non è una release valida.
Nginx rende non cacheabili metadata ed errori; solo artifact completi e loro
rivalidazioni possono essere immutabili in cache.

## 4. Interrompere e recuperare senza abbassare le sequence

Se il JSON nuovo è presente ma la firma manca o è rimasta quella vecchia,
ripetere la stessa operazione con **gli stessi byte firmati ancora validi** e
lo stesso bundle. Il publisher ricontrolla tutti gli input. Una coppia
parziale non autorizza un piano diverso; la sola firma, senza JSON, non
stabilisce una sequence. Se entrambi i file mancano, il publisher non può
distinguere un nuovo canale da uno perso: non inizializzarlo alla cieca.
Ripristinare la coppia dal backup e confrontarla con il registro offline
prima di riprendere. Vedere il [runbook di disaster recovery](disaster-recovery.md).

La protezione anti-replay lato appliance dipende dalla conservazione della
massima `sequence` e del digest osservato, dalla scadenza, dalla keyring
attiva e dal controllo indipendente di `release_sequence`. Non azzerare
mai questi dati. Correggere una release difettosa con una release firmata e
numeri superiori, preservando chiavi pubbliche storiche e audit. V1 non
impedisce a un origin compromesso di riproporre a un client privo di floor
un vecchio piano ancora valido, né firma il canale. La procedura non
pretende di risolvere questi limiti.
