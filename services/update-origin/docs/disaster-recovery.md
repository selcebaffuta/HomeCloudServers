# Disaster recovery dell'update origin

Queste procedure assumono che il DNS pubblico e il formato v1 restino
invariati. Conservare offline copie versionate di `/srv/homecloud-updates`,
delle sole chiavi pubbliche, della configurazione Nginx e dell'audit locale.
Le chiavi private release e trust root devono avere backup offline separati,
cifrati e con accesso a due persone; non fanno parte del backup del server.

Prima di ogni recupero fermare le pubblicazioni, identificare l'ultima
`sequence` attendibile per ogni canale/piattaforma e lavorare su una copia. Non
azzerare mai lo stato anti-replay dei client per far accettare un recupero.

## 1. Perdita completa del server update

- **Client:** i controlli falliscono per indisponibilità; la release installata
  continua a funzionare.
- **Garanzie:** nessun contenuto viene accettato senza firma, anche se DNS o TLS
  vengono temporaneamente compromessi.
- **Non fare:** cambiare hostname, distribuire una chiave privata al server o
  ripartire da `sequence=1`.
- **Recupero:** reinstallare Debian supportato, ripristinare chiavi pubbliche e
  albero pubblicato con ownership/mode originali, installare Nginx, eseguire
  `nginx -t`, verificare firme/hash e solo dopo spostare DNS. Se il backup non è
  completo, pubblicare una nuova release con sequence superiore al massimo
  noto.
- **Limite:** il server non conosce il massimo registrato su ogni appliance;
  serve un registro operativo offline delle sequence pubblicate.

## 2. Perdita dei file pubblicati

- **Client:** 404 o errore di download; nessun aggiornamento parziale viene
  applicato.
- **Garanzie:** manifest e bundle mancanti non vengono sostituiti implicitamente.
- **Non fare:** ricreare un bundle con lo stesso nome/hash o riutilizzare una
  sequence con JSON diverso.
- **Recupero:** ripristinare esattamente bundle content-addressed, piano e firma;
  verificarli con `homecloud-update-origin promote` su staging oppure pubblicare
  una sequence nuova. Ripulire file orfani solo dopo aver enumerato tutti i
  riferimenti firmati.
- **Limite:** senza backup dell'artefatto originale occorre una nuova release.

## 3. Manifest stable corrotto

- **Client:** la firma o il parsing falliscono; l'aggiornamento si arresta.
- **Garanzie:** la corruzione non può trasformarsi in una release accettata.
- **Non fare:** modificare a mano JSON o firma in stable.
- **Recupero:** ripristinare la coppia esatta dall'archivio immutabile oppure
  ripetere la promozione dello stesso staging verificato, vincolata al digest
  approvato. Se staging non è più valido, ripristinare prima la coppia
  attendibile e poi firmare una nuova sequence. Se mancano entrambi i file,
  verificare il floor nel registro offline: l'origin non può riconoscere da
  solo la perdita di un canale.
- **Limite:** piano e firma sono due file; un'interruzione può produrre
  temporaneamente una coppia incoerente, sempre fail-closed.

## 4. Chiave privata release persa

- **Client:** le release già firmate restano verificabili; non se ne possono
  creare di nuove con quella chiave.
- **Garanzie:** la perdita non riduce l'autenticità delle release esistenti.
- **Non fare:** generare una chiave con lo stesso nome/id o copiare la trust root
  privata sul server.
- **Recupero:** se la trust root è già installata sui device, pubblicare metadata
  trust con una nuova release key attiva e procedere all'overlap. Altrimenti è
  necessario un aggiornamento assistito/factory dell'agente e della trust root.
- **Limite:** i client legacy con la sola chiave persa non hanno una catena verso
  una nuova chiave.

## 5. Chiave privata release compromessa

- **Client:** un attaccante può firmare piani per i client che si fidano ancora
  della chiave, ma non superare una revoca root-signed già applicata.
- **Garanzie:** sequence trust monotona e revoca irreversibile proteggono i client
  migrati.
- **Non fare:** revocare cancellando semplicemente il file pubblico o abbassando
  sequence; non firmare la revoca con la chiave compromessa.
- **Recupero:** con la trust root offline creare una sequence trust superiore,
  marcare la chiave `revoked`, attivare una nuova chiave, pubblicare e poi firmare
  le release solo con la nuova. Conservare la vecchia chiave **pubblica** sul
  publisher per verificare la storia.
- **Limite:** un device legacy/offline che non possiede la trust root non può
  distinguere una migrazione autentica da una firmata dalla chiave compromessa;
  richiede recupero fisico o canale factory autenticato.

## 6. Chiave pubblica errata su alcuni device

- **Client:** firme valide per gli altri device vengono rifiutate.
- **Garanzie:** non esiste fallback a TLS o a chiavi scaricate non autenticate.
- **Non fare:** disabilitare la verifica o pubblicare chiavi private.
- **Recupero:** correggere il file root-owned tramite reinstallazione factory,
  pacchetto agente autenticato o intervento locale verificato. Se la trust root è
  corretta, ripubblicare metadata trust correnti non richiede rollback.
- **Limite:** il server non può correggere remotamente una trust anchor errata.

## 7. Sequence stable avanzata erroneamente

- **Client:** chi ha osservato la sequence alta rifiuterà qualunque valore più
  basso anche se firmato.
- **Garanzie:** rollback e replay restano bloccati.
- **Non fare:** cancellare `update-status.json`, riusare la sequence o abbassare
  stable.
- **Recupero:** emettere un piano correttivo valido con sequence strettamente
  superiore. Può referenziare la release applicativa corrente e nessun pacchetto
  se non serve cambiare software.
- **Limite:** le sequence consumate non sono recuperabili.

## 8. Release pubblicata ma difettosa

- **Client:** un fallimento del health check applicativo attiva il rollback
  locale; difetti non rilevati dal health check possono restare attivi.
- **Garanzie:** non è possibile sostituire silenziosamente l'artefatto
  content-addressed.
- **Non fare:** sovrascrivere il bundle, ripromuovere una sequence con contenuto
  diverso o tentare un downgrade.
- **Recupero:** fermare nuove promozioni, produrre e testare una release corretta,
  assegnare sequence e release_sequence superiori e promuoverla normalmente.
- **Limite:** il protocollo non è un sistema di rollout percentuale; staging e
  collaudo hardware devono precedere stable.

## 9. Storage pieno durante publish/promotion

- **Client:** stable precedente resta leggibile se l'errore avviene in staging;
  durante lo switch a due file può comparire una firma non corrispondente e il
  client ritenta senza applicare.
- **Garanzie:** snapshot, `fsync`, file temporanei e rename evitano file accettati
  parzialmente.
- **Non fare:** cancellare bundle referenziati o file `.publish.lock` durante un
  processo attivo.
- **Recupero:** liberare soltanto temporanei/orfani verificati, controllare la
  coppia stable con OpenSSL e ripetere la stessa operazione idempotente.
- **Limite:** non è ancora presente garbage collection automatica.

## 10. Interruzione di corrente durante publish/promotion

- **Client:** può vedere il vecchio piano oppure una coppia piano/firma
  temporaneamente incoerente; non può accettare dati senza firma corrispondente.
- **Garanzie:** ogni singolo file è sostituito atomicamente e le directory sono
  sincronizzate; l'audit della promozione viene sincronizzato prima dello switch.
- **Non fare:** correggere manualmente uno solo dei due file.
- **Recupero:** controllare audit, staging e record immutabili, quindi ripetere
  publish/promotion con gli stessi input. Il piano già corrispondente permette al
  retry di completare la firma mancante.
- **Limite:** il formato v1 con firma detached non consente un rename atomico
  dell'intera coppia. Una futura v2 potrebbe usare un envelope firmato singolo.

## Verifica periodica

Eseguire almeno trimestralmente un restore su host isolato: `nginx -t`, verifica
di tutte le firme correnti, ricalcolo dei bundle SHA-256, promotion idempotente e
simulazione di perdita di alimentazione. Registrare fuori dal server le sequence
massime release e trust, gli hash delle chiavi pubbliche e l'esito del drill.
