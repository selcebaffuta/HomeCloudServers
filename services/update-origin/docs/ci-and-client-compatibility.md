# CI diagnosis and update-client compatibility

Reviewed baseline: HomeCloudServers `93889a424c7cfe6f0309829379e3c0fdcc792448`.
Client reviewed read-only: HomeCloudSetup/main
`7b099fa0e459a7528e8a735a32642edec37b4c95`, `homecloud_setup/update_agent.py`,
`update_trust.py`, `update_bundle.py`, `homecloud_update.py` and the runtime policy
contract. No other repository, production source configuration or release changed.

## Confirmed CI failure

[Run 37655926899](https://github.com/selcebaffuta/HomeCloudServers/actions/runs/37655926899),
step **Validate update-origin Nginx configuration**, reported:

```text
nginx: ... syntax is ok
open() "/var/log/nginx/access.log" failed (13: Permission denied)
nginx: ... test failed
```

Lint, typecheck, Node tests, production build/smoke and 17 publisher tests had
already passed. This was an unprivileged **test harness** depending on Nginx's
distribution default access-log path, not a certificate/TLS syntax failure.
The harness now gives access logs and all HTTP temporary directories paths
inside its private temporary prefix; early errors go to stderr. It still calls
`nginx -t` and remains unprivileged. No chmod of host logs, sudo workaround,
disabled logging, ignored exit codes or weaker TLS verification.
The current ubuntu-latest runner also surfaced a privileged-port bind check
during `nginx -t`. Test rendering now substitutes loopback high ports, as do the
live HTTPS fixtures; production listeners80/443 are unchanged. Debian slim jobs
install `ca-certificates` explicitly before Git checkout, retaining normal TLS
verification instead of depending on optional package recommendations.

## Additional delivery fixes

- Previously the artifact location used `add_header Cache-Control ... immutable
  always`: this also marked missing/denied/error responses immutable for a year.
  A status map now grants that policy only to 200/206/304; other responses use
  `no-store`. Unknown endpoints also explicitly use `no-store`. Metadata, trust
  signatures and health remain `no-store`.
- The Nginx channel regex now matches the publisher's existing 1–32 character
  allowlist. No new platform/channel semantics or manifest fields are introduced.
- Header inheritance remains explicit per location; security headers are kept
  on successful and error responses. No new recent-version-only inheritance
  directive is used. See [Nginx headers](https://nginx.org/en/docs/http/ngx_http_headers_module.html)
  and [status map](https://nginx.org/en/docs/http/ngx_http_map_module.html).

## Automated coverage and evidence boundaries

`tests/check-nginx.sh` is the original syntax gate with isolated paths.
`tests/test_nginx_origin.py` adds six opt-in unprivileged live-Nginx cases:

- GET/HEAD health and missing health →503, no-store/security headers;
- exact signed Debian12/13 manifests and trust JSON/signature bytes, independently
  verified by OpenSSL after actual HTTPS transfer;
- content-addressed artifact SHA-256/size/MIME, HEAD, ETag/304, single range/206;
- no immutable caching for 404, forbidden methods or unsatisfiable ranges/416;
- malformed/overlong/traversal/private/symlink paths cannot export test markers;
- HTTP upgrade destination, TLS1.2/1.3 and rejection of wrong hostname/untrusted CA.

Fixtures reuse the existing publisher signing helpers. All private keys are
fresh temporary **test keys**, outside the publication root, deleted with the
fixture. No real key is read or generated; no installable appliance release is
published. Nginx uses loopback high ports, its own PID/log/temp paths and direct
process lifecycle; it never controls the system service. TLS certificate/hostname
verification remains enabled. Tests are skipped by default and run only with
CI=true and HOMECLOUD_ORIGIN_NGINX_INTEGRATION=1 on the isolated runner.

CI retains all Node/Next checks and the syntax gate, adds the live transport step,
and runs the same syntax/HTTPS checks unprivileged in disposable Debian12/13
containers. Dependency installation is confined to CI. This tests the packaged
Nginx/OpenSSL behavior, not a production install, external DNS/ACME, firewall,
bandwidth, disaster recovery or Raspberry/appliance upgrade end to end.

## Client contract matrix (static review, not client execution)

| Contract | Origin / transport | Setup consumer and remaining boundary |
| --- | --- | --- |
| Source authority | HTTPS dedicated FQDN, port443; no admin endpoint | `load_source`, `_trusted_url`: root-owned enabled source/allowed_hosts, no credentials/query/fragment. Default source remains disabled. |
| Redirects/TLS | HTTP308 upgrades to fixed HTTPS origin; HTTPS data endpoints do not redirect | `_TrustedRedirectHandler` revalidates targets, `_download` uses verified TLS. Fixture high ports are test-only; client still requires443. |
| Plan envelope | schema1/product/sequence/time/platform/homecloud/linux, detached RSA-SHA256 | `validate_plan`, `_verify_signature_with_keys`: same fields, limits, timestamps and signature semantics. No request/response schema changed. |
| Platforms | `/v1/<channel>/debian-{12,13}-arm64.json[.sig]` | `_require_local_platform` compares actual OS/version/ARM64. It does **not** normalize raspbian12 to debian12. |
| Limits | plan≤256KiB, detached signature≤64KiB, bundle≤1GiB; packages≤64 | Client constants and stream checks agree; fixture verifies bytes/hash/size, not a genuine 1GiB transfer. |
| Authenticity/replay | Publisher verifies signature, expiry, hash/size, monotone channel/platform sequence | Client repeats signature/time/platform checks and persists highest sequence plus signed-plan digest. TLS alone is insufficient. |
| Artifacts | `/releases/<lowercase sha256>.tar.gz`; immutable only for successful content | `_download` verifies hash and exact size, then bounded safe extraction, internal signed bundle/approved runtime lock. Synthetic transport tar is not an installable bundle. |
| Linux packages | Exact name/version/reason runtime or security, bound to target commit | `_apply_plan`, `apply_linux_packages`: approved runtime policy, HomeCloud update/health first, then APT simulation and allowlisted packages. No general dist-upgrade. |
| Key rotation | `/v1/<channel>/trust.json[.sig]`, separately rooted metadata | `accept_trust_metadata`: locally installed trust root, overlap/revocation/sequence; downloaded key alone never grants trust. |
| Two-file publication | Individually atomic JSON/signature replace, serialized publisher | A racing reader can receive a mismatched pair; signature verification fails closed. Retry safely; transport cache must not preserve metadata. This increment does not claim pairwise atomicity. |

## Open integration gates

1. `raspbian-12-arm64` exists in appliance baseline/runtime policy but the origin
   supports only Debian12/13 ARM64. Do not relabel a target, serve a Debian plan
   under a Raspbian alias or loosen platform checking. A coordinated explicit
   support decision and both-side tests are required. Raspberry Pi OS Trixie
   identifying itself as Debian13 still requires actual appliance qualification.
2. The runtime tarball updater does not upgrade the installed privileged Setup
   agent. Migrate/qualify old agents and install the independent trust root through
   an authenticated factory/appliance path before revoking legacy signing keys.
3. Channel is not signed in v1. Promotion intentionally reuses exact bytes and
   signature; replay floors are not cryptographic channel isolation. A compromised
   origin can substitute another otherwise acceptable signed channel plan. Strong
   staging/stable separation requires a separately migrated protocol/key policy;
   not changed incidentally by an Nginx fix.
4. APT packages still come from configured signed Debian/vendor repositories;
   HomeCloud authorizes exact packages/versions but does not yet mirror the `.deb`
   payloads. No claim of HomeCloud-only package transport or fully frozen mirrors.
5. Actual DNS/certificate renewal, installer rollback/reload, backup/restore drill,
   concurrent remote downloads and real signed appliance upgrades remain operator
   acceptance tasks. The installer is source-reviewed and syntax-checked, not run
   here. No deploy, production publication, signing-key rotation or repo repin.
