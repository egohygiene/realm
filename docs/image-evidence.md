# Installed-image evidence

Realm #7 adds explicit local evidence for an actual native Linux AMD64 base
image. The closed receipt is limited evidence, never a release or security
certification. Profile SPDX files under `dist/profiles` remain declared intent;
they cannot substitute for a scanner inventory of an installed image.

## Identity and source

The producer accepts only a full local Docker image configuration digest such
as `sha256:<64 lowercase hexadecimal characters>`. It refuses mutable tags,
including version-shaped tags. A full Git revision must match the image source
label and the nine actual canonical build-input files in the selected checkout.
The installed lock, package inventory and build metadata must agree.

Three digests have different meanings:

| Field | Meaning | Establishes publication? |
| --- | --- | --- |
| `local_config_digest` | Exact local Docker configuration identity | No |
| `scanner_manifest_digest` | Manifest synthesized/read by the local scanner | No |
| Registry manifest/index digest | Registry-observed immutable distribution object | Separate #17 proof |

The receipt requires registry reference, registry manifest digest and index
digest to remain `null`. Its `state` is `limited` and `release_ready` is `false`.
Image signing, provenance authentication and registry publication remain
`not-performed`; neither a well-typed receipt nor a passing command promotes them.

## Tools and capture

`config/image-evidence-tools.v1.json` pins official Syft 1.55.0 and Grype 0.121.0
Linux AMD64 archives, source revisions and executable hashes. Both use Apache-2.0.
Archives were checked against the official release checksum files and GitHub
asset digests. Those checks prove selected bytes. Sigstore signatures and
producer provenance were not verified and are not claimed. Install reviewed
executables outside the source tree and verify those pins before use. The
collector checks exact executable bytes and runtime version/source/platform.

Provide an existing Grype database explicitly. An intentional database refresh
is a separate online operation, for example using the pinned Grype executable:

```bash
GRYPE_DB_CACHE_DIR="$DATABASE_DIRECTORY" "$GRYPE" db update
```

The collector disables automatic database/app updates, clears inherited scanner
configuration variables and supplies an empty explicit YAML configuration.
It requires a valid schema-v6 database with an immutable archive-checksum URL,
records the database file checksum and build time, and checks its age at capture
against Grype's 120-hour baseline. It hashes the database before and after the
scan. A stale, future, invalid or changing database fails. Historical evidence
records freshness at capture; it is not a current vulnerability assessment.

Plan without Docker/scanner execution or file writes:

```bash
python3 tools/realm_image_evidence.py plan \
  --image "$LOCAL_CONFIG_DIGEST" --source-revision "$SOURCE_REVISION"
```

Run the explicit producer after building the exact selected source:

```bash
python3 tools/realm_image_evidence.py collect \
  --image "$LOCAL_CONFIG_DIGEST" \
  --source-revision "$SOURCE_REVISION" --source-root "$SOURCE_CHECKOUT" \
  --output "$NEW_EVIDENCE_DIRECTORY" \
  --syft "$SYFT" --grype "$GRYPE" --database-directory "$DATABASE_DIRECTORY"
```

The equivalent Tasks are `image:evidence:plan`, `image:evidence` and
`image:evidence:verify`; `task --summary <name>` lists their required inputs.
Task arguments enter shell commands through dedicated quoted environment
variables. `task check` calls only the offline pin/contract check and unit tests;
it does not contact a registry, update a database or run image tools.

The producer selects the explicit local Docker socket, inspects the exact image
and native platform, then runs installed-lock verification and non-root smoke
with network disabled. Smoke retains the image's documented development-user
sudo boundary. Syft scans that image once into native JSON and SPDX 2.3; Grype
scans the resulting same-image SBOM. The producer binds both scanner image
identities, all installed package name/version records, SPDX container identity,
Grype matched package identities, tool versions and observed source/platform.

Tool exits and findings have separate meanings. A successful Grype invocation
still records every match, ignored match and severity count. There is no
clean-image verdict or automatic finding suppression. Native ARM64 scanner pins
and actual ARM64 capture are not qualified by this checkpoint. Existing native
AMD64/ARM64 build Tasks remain; no emulated run becomes native proof.

## Portable bundle and verification

`schemas/image-evidence.v1.schema.json` defines the closed receipt. Each new
bundle contains `image-evidence.json` plus eight checksummed artifacts: portable
image identity, Syft native JSON, installed-image SPDX, Grype report, exact apt
lock, installed-package TSV, build metadata and runtime verification results.

Runtime configuration, private database/cache paths and embedded image config
are removed from portable scanner reports. The raw and portable report hashes
are recorded separately; all package/finding data and applied ignore records
remain. The exported format names identify this redaction. Raw tool output and
local execution logs stay outside public evidence.

```bash
python3 tools/realm_image_evidence.py verify --directory "$EVIDENCE_DIRECTORY"
```

`verify_evidence(directory)` exposes the same dependency-free read-only API for
#17. It validates the bounded closed receipt and exact artifact inventory,
rejects unsafe members/duplicate keys/nonfinite numbers/excessive nesting,
checks file sizes/hashes, and re-derives all available subject, inventory,
package, database-age and finding facts from the checked bytes. It verifies the
included lock against its source-input hash. Other source hashes and runtime
observations are recorded claims; this portable verifier does not independently
rebuild the image, retrieve Git history or authenticate a producer. The checker
implements its own contract vocabulary, not a general external JSON Schema engine.

Capture builds a temporary sibling directory and publishes it with Linux
`renameat2(RENAME_NOREPLACE)`. An existing or racing destination is preserved;
unsupported atomic publication fails. Tool failures/deadlines leave no partial
final directory. Each Docker invocation gets a fresh name and label. Deadline cleanup verifies
that name, label and exact container ID before removing an owned disposable
container; already-removed containers require a successful absence check. Only
owned process groups, containers and temporary files are cleaned; no broad
image/container/cache pruning or registry deletion occurs. Producer bytes are
frozen at capture start and must remain unchanged before publication, preventing
a normal source edit from relabelling old running code with a new file hash.

## Optional build transport trust

The base Dockerfile accepts an optional BuildKit secret `realm_build_ca` containing
a caller-reviewed CA bundle. It configures apt HTTPS trust for that installation
RUN only. An empty supplied bundle fails, absence uses ordinary system trust,
and temporary apt configuration is removed before the layer completes. TLS
verification remains enabled; the bundle is never copied into an image layer.
For a build that requires explicit proxy trust:

```bash
docker build --secret "id=realm_build_ca,src=$BUILD_CA_BUNDLE" \
  --file images/base/Dockerfile --build-arg "IMAGE_REVISION=$SOURCE_REVISION" \
  --tag realm-base:local .
```

This changes transport trust, not package roots, immutable source pins, locks or
base policy. The first unmodified local build failed TLS verification; that
failure remains distinct from the later exact-source successful build.

## Distribution and recovery policy boundary

#17 owns the reviewed manual publication adapter and release declaration.
The source convention uses immutable `vMAJOR.MINOR.PATCH` release identity and
registry-observed digest references. Discovery aliases such as `stable` or
`latest` are mutable hints; consumers and rollback records use verified digests.
Do not overwrite a prior immutable release binding after partial publication.

Retain referenced immutable release/evidence records without automatic deletion.
Rollback selects a previously reviewed non-revoked digest and records the alias
change separately. Revocation retains an append-only reason/tombstone and
verification evidence; it does not rewrite history or silently reuse a tag.
Registry-specific credentials, signing, provenance attestations, channel moves
and retention/deletion operations require their actual reviewed adapter and
publication authority. This local collector performs none of them.

Full #7 acceptance remains open for supported native architecture evidence,
cryptographic/signature/provenance verification, accepted producer/release
compatibility and actual approved distribution. Hosted Actions remain deferred.
