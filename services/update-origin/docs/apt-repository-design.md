# Design futuro del repository APT HomeCloud

Questo documento è deliberatamente un design: il repository APT non è ancora
implementato. L'obiettivo è evitare che l'introduzione di pacchetti Debian
indebolisca il protocollo release già firmato.

## Tre domini separati

1. **Pacchetti OS Debian:** kernel, OpenSSL, systemd e dipendenze provenienti dai
   repository Debian firmati. Il piano HomeCloud autorizza nome e versione
   esatti; non rende attendibile un repository.
2. **Release applicativa HomeCloud:** bundle tar content-addressed con sorgente,
   wheel e catalogo verificati, installato atomicamente dall'updater esistente.
3. **Metadata di sicurezza HomeCloud:** piani release e metadata trust firmati
   offline. Non devono essere impacchettati come normali `.deb` mutabili.

## Cosa potrebbe passare da APT

Soltanto componenti appliance che devono essere aggiornabili indipendentemente
e con ownership Debian chiara: agente privilegiato, unit systemd, wrapper kiosk,
configurazioni con conffile espliciti e driver hardware scelti. L'app Web e il
catalogo continuano nel bundle finché il loro switch/rollback atomico è più
forte di quello ottenibile con più pacchetti `.deb`.

Ogni path deve appartenere a un solo pacchetto o al bundle, mai a entrambi. Dati,
database, pairing, factory profile e trust state non sono payload di pacchetto.

## Firma e pubblicazione repository

- chiave APT offline distinta da release key e trust root;
- `Release` e `InRelease` generati deterministicamente; `InRelease` firmato e
  `Release.gpg` mantenuto solo se serve compatibilità;
- hash SHA-256/SHA-512 di `Packages`, indici compressi e `.deb`;
- `Valid-Until` breve e monotonia operativa della suite;
- nessuna private key sul mirror/origin pubblico;
- promozione staging → stable per snapshot immutabile, non rigenerazione;
- chiave pubblica distribuita tramite factory o trust chain già autenticata,
  mai perché scaricata dallo stesso mirror.

## Layout, pinning e versioni

Usare suite snapshot immutabili per Debian 12/13 ARM64, per esempio una suite
interna identificata da sequence, e un puntatore stable promosso atomicamente.
Le appliance configurano `Signed-By` su un keyring dedicato e pinning per
origine, label, suite e architettura. Il repository HomeCloud non deve avere
priorità sufficiente a sostituire pacchetti Debian non allowlisted.

Il piano release continua a indicare versioni esatte e la release HomeCloud
richiesta. L'agente simula APT, rifiuta installazioni nuove non previste,
rimozioni, downgrade e dipendenze aggiuntive. Una versione presente nel repo ma
assente dal piano non è autorizzata.

## Downgrade e rollback

APT non fornisce da solo rollback transazionale. Conservare `.deb` e snapshot
precedenti per recupero offline, ma non autorizzare downgrade remoto. Per
componenti privilegiati servono preinst/postinst minimi, backup dello stato e
health check; un rollback richiede un nuovo piano firmato con sequence superiore
e una versione Debian formalmente superiore (eventualmente con epoch/revision),
non la riduzione della versione.

## Recovery e mirroring

Backup offline: pool `.deb`, indici, `InRelease`, chiavi pubbliche, mapping
sequence→snapshot. Un mirror replica byte per byte snapshot già firmati; non
rigenera metadata. In assenza del repository, HomeCloud continua a funzionare e
rimanda i soli aggiornamenti Linux. La cache locale può consentire il retry, ma
non sostituisce `Valid-Until` né le firme.

## Compatibilità e rischio di mutabilità

Pubblicare indici distinti per Debian 12/13 e solo `arm64` inizialmente. Testare
ogni piano contro immagini pulite e aggiornate di entrambe le versioni. Non usare
suite APT mutable come unica fonte di verità: una nuova build sotto la stessa
versione o la sostituzione di un `.deb` romperebbe riproducibilità, audit e
rollback. Filename, versione e hash devono essere immutabili; una correzione
produce una nuova versione e una nuova sequence.

## Prerequisiti prima dell'implementazione

- definire i pacchetti e la ownership completa dei path;
- rendere aggiornabile l'agente senza affidargli shell o maintainer script
  arbitrari;
- scegliere HSM/supporto offline e procedura a due persone per la chiave APT;
- costruire test su installazione, upgrade interrotto, spazio esaurito e restore;
- integrare snapshot/promotion nel disaster recovery;
- decidere come distribuire la trust root ai dispositivi legacy.
