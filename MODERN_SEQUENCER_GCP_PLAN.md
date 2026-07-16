# Modern Sequencer GCP Migration Plan

## Objective

Provide remote administration and automatic Google Cloud Storage delivery for
new NextSeq 1000/2000 and MiSeq i100 instruments without changing the legacy
infrastructure serving existing sequencers.

The new design will:

- Run its relay in the `sabeti-h3africa` GCP project in `us-central1`.
- Keep the existing AWS relay and legacy sequencer configuration unchanged.
- Upload completed runs directly from each instrument to its assigned GCS
  bucket and prefix.
- Store runs as native directory trees rather than composed tar archives.
- Support remote SSH and Illumina web/IRM access through private tunnels.
- Treat direct MiSeq i100 deployment as conditional on a read-only access
  preflight.

## Agreed Decisions

| Topic | Decision |
| --- | --- |
| Relay project | `sabeti-h3africa` |
| Relay region | `us-central1` |
| Legacy sequencers | Continue using the existing AWS infrastructure |
| New sequencers | Use the new GCP relay and direct GCS upload |
| Site addresses | Dynamic; no fixed public CIDR allowlist is available |
| Remote interfaces | SSH and Illumina web/IRM |
| Upload start | After the authoritative completion marker |
| Completion marker | Prefer `CopyComplete.txt`; confirm per model and output path |
| GCS representation | Native run directory tree |
| GCS destination | Machine-specific bucket and prefix mapping |
| Source retention | Never delete or move source data as part of upload |
| MiSeq i100 | Attempt direct deployment only after shell-access discovery |

## Current Project Findings

Read-only inspection of `sabeti-h3africa` found:

- The project is active and Compute Engine, OS Login, Cloud Logging, and Cloud
  Monitoring are enabled.
- `iap.googleapis.com` is not currently enabled.
- The project has an auto-mode `default` VPC.
- The default VPC permits SSH and RDP from `0.0.0.0/0`.

The relay must not use the default VPC. A dedicated VPC avoids inheriting those
permissive rules without risking existing project resources by changing the
legacy firewall configuration.

## Target Architecture

```text
Legacy sequencers
    |
    +-- existing reverse tunnels --> existing AWS relay
    +-- existing legacy delivery path

New sequencer
    |
    +-- HTTPS ---------------------> machine-specific GCS bucket/prefix
    |                                 native run directory tree
    |
    +-- IAP over outbound HTTPS ---> GCE relay in sabeti-h3africa
                                      reverse SSH and IRM forwards
                                              |
Operator -- IAP + OS Login -------------------+
```

The relay is a control-plane service only. Sequencing data must not pass
through the relay or IAP. Direct GCS upload avoids a relay bottleneck, avoids
double transfer, and respects IAP's documented limitation against bulk data
transfer.

## GCP Relay Infrastructure

### Network

Create an isolated custom-mode VPC and a small subnet in `us-central1`.

- Permit relay SSH ingress only from the IAP TCP forwarding range
  `35.235.240.0/20`.
- Target the firewall rule specifically to the relay service account or network
  tag.
- Do not create public SSH, HTTPS, or reverse-forward firewall rules.
- Prefer a VM without an external IP and provide controlled egress through
  Cloud NAT.
- Enable Private Google Access on the subnet.
- Leave the existing default VPC and its firewall rules unchanged.

### VM

Initial sizing and configuration:

- Ubuntu 24.04 LTS.
- Non-preemptible `e2-small` instance.
- Small balanced persistent boot disk with log rotation enabled.
- Shielded VM features enabled.
- Automatic restart and deletion protection enabled.
- OS Login enabled and project SSH keys blocked.
- Ops Agent installed for system and SSH logs.
- Dedicated VM service account with only logging and monitoring permissions.
- No permission to read or write sequencing buckets.

The VM zone should be parameterized within `us-central1`; `us-central1-a` is a
reasonable initial default subject to quota and availability checks.

### IAP and IAM

Enable `iap.googleapis.com` and use IAP TCP forwarding for both operators and
instrument-originated tunnel connections.

- Human administrators receive OS Login and IAP access through a managed Google
  group, not individual IAM grants.
- Each instrument receives a unique GCP service account.
- Grant each instrument identity IAP tunnel access only to the relay VM and
  only to the tunnel SSH port.
- Grant only the minimal Compute read permissions required by
  `gcloud compute start-iap-tunnel`.
- Grant the same instrument identity object access only to that instrument's
  assigned GCS bucket prefix, even when the bucket is in another project.
- Do not grant project-wide Storage roles in `sabeti-h3africa`.

Using one tightly scoped identity per instrument keeps provisioning manageable
while preserving independent revocation and audit history. If cross-project
policy prevents this, split relay and uploader identities for that instrument.

## Relay SSH Design

Use separate administrative and instrument tunnel entry points:

- Administrative SSH uses OS Login through IAP.
- Instrument SSH uses a dedicated `sshd` configuration and local tunnel-only
  accounts.
- Password, keyboard-interactive, agent forwarding, X11 forwarding, and PTY
  allocation are disabled for tunnel accounts.
- `GatewayPorts` remains disabled.
- Reverse forwards bind only to `127.0.0.1` on the relay.
- Each instrument has a unique SSH key and a fixed pair of reverse ports.
- Authorized-key restrictions allow only the assigned reverse listen ports.
- Tunnel accounts cannot execute a shell or commands.

Maintain a version-controlled, non-secret port registry. For example:

| Instrument | Relay SSH port | Relay web port |
| --- | ---: | ---: |
| `nextseq-a` | 6101 | 7101 |
| `nextseq-b` | 6102 | 7102 |
| `miseq-i100-a` | 6103 | 7103 |

Actual names and ports will be assigned from the confirmed instrument
inventory.

## Instrument Tunnel Client

Each supported instrument will run a systemd-managed OpenSSH client. The SSH
connection will use `gcloud compute start-iap-tunnel` as its transport, so only
outbound HTTPS access to Google is required.

The connection will request two reverse forwards when supported:

- Relay loopback port to the instrument's local SSH service.
- Relay loopback port to the instrument's local HTTPS/IRM service.

Client settings will include:

- `ExitOnForwardFailure=yes`.
- Server keepalives to prevent idle disconnection.
- Strict relay host-key verification using a pinned host key.
- No interactive authentication.
- Automatic restart with bounded backoff.
- A dedicated service account configuration and SSH key readable only by the
  tunnel service.

Google documents that IAP may disconnect an idle session after one hour and
that `gcloud` attempts reconnection. The proof of concept must demonstrate that
SSH keepalives and systemd recovery sustain the nested reverse tunnel for at
least 72 hours before instrument rollout.

If direct IAP transport proves unreliable on the instrument OS, the fallback is
a hardened public reverse-SSH listener with a reserved GCP address, key-only
authentication, a dedicated port, and aggressive connection monitoring. This
fallback is not the default because source addresses cannot be allowlisted.

## Operator Access

Add a new connection helper rather than changing the legacy `connect.sh` flow.
The helper will:

- Connect to the GCE relay through IAP and OS Login.
- Resolve the selected instrument from the modern inventory.
- Keep relay and instrument usernames separate.
- Open a local connection to the instrument's relay-loopback SSH port.
- Optionally expose the instrument's relay-loopback HTTPS port on a local port
  for browser access.

Example operator flows, hidden behind the helper, are:

```bash
# Forward the instrument SSH endpoint through the relay.
gcloud compute ssh RELAY \
  --project=sabeti-h3africa \
  --zone=us-central1-a \
  --tunnel-through-iap \
  -- -L 6101:127.0.0.1:6101

# In another terminal, connect using the instrument's actual account.
ssh -p 6101 ilmnadmin@127.0.0.1
```

```bash
# Expose the instrument web interface locally.
gcloud compute ssh RELAY \
  --project=sabeti-h3africa \
  --zone=us-central1-a \
  --tunnel-through-iap \
  -- -L 8443:127.0.0.1:7101
```

The web interface would then be accessed locally over HTTPS. Certificate-name
handling will be documented once the actual IRM hostname and certificate are
known.

## Native GCS Uploader

### Why a New Uploader Is Needed

The existing Broad `sequence-upload-to-gs` script incrementally creates and
composes tar archives. Its modernization PR remains open and explicitly
requires full-run validation. It does not satisfy the selected native-directory
layout.

The legacy uploader in this repository is also unsuitable because it depends
on DNAnexus, Python 2, legacy run markers and directory conventions, and
destructive post-upload movers.

The new uploader should therefore be a small completion-triggered wrapper
around the supported `gcloud storage` CLI, not a port of either legacy upload
system.

### Discovery and Triggering

A cron entry will run the monitor at a conservative interval, initially every
15 minutes.

- Scan only the configured run-output root.
- Treat each immediate child directory as a candidate run.
- Require the configured completion marker before upload.
- Prefer `CopyComplete.txt`, but make the marker configurable per instrument.
- Require the directory to remain unchanged for a short confirmation interval
  after the marker appears.
- Use `flock` so overlapping cron executions cannot start duplicate uploads.
- Track completed and failed runs in a root-owned local state directory.
- Never reject a completed run merely because it is old.

The exact output root and authoritative marker must be confirmed from a real
completed run on every instrument model. Existing assumptions such as
`/usr/local/illumina/runs` must not be deployed without verification.

### Upload and Verification

For a completed run:

1. Validate that the source is a directory below the configured output root.
2. Validate that the completion marker exists.
3. Check whether the destination already has `_UPLOAD_COMPLETE.json`.
4. Run recursive `gcloud storage rsync` to the assigned destination without a
   delete option.
5. Use checksum comparison so existing valid objects can be skipped safely.
6. Run a second checksum-only dry run and require that no additional transfers
   are needed.
7. Record source file count and byte count in an upload manifest.
8. Write `_UPLOAD_COMPLETE.json` only after verification succeeds.
9. Preserve all source files and local instrument run directories.

Destination layout:

```text
gs://MACHINE_BUCKET/MACHINE_PREFIX/INSTRUMENT_ID/RUN_ID/
    RunInfo.xml
    SampleSheet.csv
    Data/
    ...
    _UPLOAD_COMPLETE.json
```

The completion object should include:

- Instrument ID and run ID.
- Source completion marker and marker timestamp.
- Upload start and completion timestamps.
- File count and source byte count.
- Uploader version or Git commit.
- Verification result.

Do not pass a destination-delete flag to `rsync`. Source cleanup and retention
are separate operational policies and are out of scope for the uploader.

### Authentication and Installation

- Install a pinned Google Cloud CLI in an application-owned location rather
  than modifying the instrument's system Python.
- Store credentials outside the repository with mode `0400` or equivalent.
- Use a dedicated non-interactive `gcloud` configuration for the service.
- Avoid tokens or credential paths in verbose logs.
- Grant object create, get, and list permissions only to the machine's assigned
  prefix. Add broader permissions only if a tested resume case requires them.

## Instrument Preflight

Perform this read-only preflight before any installation:

- Record instrument model, control software version, OS, architecture, and
  support status.
- Confirm shell account, remote SSH, sudo scope, cron, and systemd availability.
- Confirm the actual run-output root and permissions.
- Inspect at least one completed run for `RunInfo.xml`, `CopyComplete.txt`,
  `RTAComplete.txt`, and other completion artifacts.
- Confirm local disk capacity and the filesystem used for temporary state.
- Confirm outbound DNS and HTTPS access to Google APIs and IAP endpoints.
- Confirm local SSH and HTTPS/IRM listener addresses and ports.
- Confirm that installing user-local binaries and service units is permitted by
  Illumina support policy.

NextSeq 1000/2000 shell access is expected, but each machine still requires the
preflight. MiSeq i100 direct installation is not approved until its shell and
filesystem access are demonstrated. Similarity to the NextSeq OS is not enough
to infer access.

If MiSeq i100 direct access fails, use a small companion host that:

- Receives the vendor-supported external run output.
- Runs the same completion-triggered uploader.
- Originates the IAP reverse tunnel for IRM access.
- Does not require modification of the MiSeq appliance OS.

## Repository Organization

Keep new implementation separate from legacy roles and playbooks. A proposed
layout is:

```text
gcp-relay/
    terraform/
    ansible/
modern-sequencer/
    files/
    templates/
    tests/
inventory/
    modern-sequencers.example.yml
MODERN_SEQUENCER_GCP_PLAN.md
```

- Terraform manages GCP APIs, network, firewall, IAM, service accounts, and the
  relay VM.
- A new Ansible playbook configures only the GCE relay.
- Minimal instrument deployment templates install the tunnel and uploader
  without running `field-node/node-full.yml`.
- Secrets, private keys, service-account key material, and rendered inventories
  remain outside Git.
- The current AWS manager, Route53 discovery, Samba, DNAnexus, and field-node
  roles remain frozen for legacy sequencers.

## Implementation Phases

### Phase 0: Preserve the Legacy Baseline

- Inventory the old sequencers and confirm they remain attached to AWS.
- Record current AWS relay health and recovery instructions.
- Make no credential, DNS, firewall, or playbook changes to legacy nodes.
- Label the legacy path as maintenance-only in documentation.

### Phase 1: Build and Test Locally

- Implement the completion-triggered native-tree uploader.
- Implement configuration validation and per-run locking.
- Add ShellCheck and automated tests with a fake `gcloud` executable.
- Test delayed writes, missing markers, interrupted uploads, reruns, duplicate
  cron invocations, and GCS failures.
- Test against copies of real completed NextSeq and MiSeq run directories when
  available.

### Phase 2: Provision the GCP Relay

- Enable IAP.
- Create the dedicated VPC, subnet, firewall, and egress configuration.
- Create the relay VM and least-privilege VM service account.
- Configure OS Login, tunnel-only SSH, logging, monitoring, and port registry.
- Configure group-based operator access.

### Phase 3: Prove IAP Reverse Tunneling

- Create a temporary instrument identity and tunnel account.
- Simulate an instrument from an ordinary Linux test host.
- Verify reverse SSH and HTTPS forwarding through IAP.
- Test credential revocation, VM reboot, client restart, network interruption,
  and 72-hour tunnel stability.
- Confirm no relay port is reachable directly from the public internet.

### Phase 4: Pilot One NextSeq

- Run the read-only preflight.
- Install the tunnel client without altering the existing remote-access path.
- Validate SSH and web access through both old and new paths if applicable.
- Configure upload to a temporary GCS prefix.
- Upload a completed run and compare the native source and destination trees.
- Observe at least two successful production-sized runs before promotion.

### Phase 5: Expand NextSeq Deployment

- Promote the pilot destination to the production bucket prefix.
- Deploy to the remaining NextSeq instruments one at a time.
- Retain independent service accounts, keys, relay ports, and logs.
- Document recovery and credential-rotation procedures.

### Phase 6: Evaluate MiSeq i100

- Perform the MiSeq i100 access and filesystem preflight.
- Deploy directly only if shell access and support constraints are acceptable.
- Otherwise provision the companion-host fallback.
- Validate IRM web forwarding and one complete native-tree upload.

### Phase 7: Operational Handoff

- Add alerts for relay health, missing tunnels, and repeated upload failures.
- Create operator runbooks for SSH, IRM, upload status, credential rotation, and
  recovery.
- Confirm the AWS relay remains the documented owner of legacy sequencers.
- Do not retire old infrastructure merely because the new deployment succeeds.

## Testing and Acceptance Criteria

The new system is ready for production when:

- The relay is isolated from the project's permissive default VPC.
- No administrative or reverse-forward port is publicly reachable.
- Human relay access requires IAP and OS Login.
- Each instrument identity can access only the relay tunnel endpoint and its
  assigned GCS prefix.
- A tunnel survives or automatically recovers from client restart, relay
  reboot, transient network failure, and IAP reconnection.
- SSH and HTTPS/IRM access work through the new helper.
- No upload starts before the authoritative completion marker.
- A failed upload resumes without duplicating or deleting valid objects.
- A successful run is represented as a native directory tree.
- `_UPLOAD_COMPLETE.json` appears only after verification.
- Source run data remains unchanged.
- Logs contain no private keys, access tokens, or credential contents.
- Upload and tunnel services do not interfere with sequencing or instrument
  control software.

## Rollback

Rollback for a new instrument consists of stopping and disabling the new tunnel
and uploader services. Because the uploader does not delete source data and the
legacy AWS infrastructure is not modified, rollback does not require restoring
instrument data or legacy relay state.

Partially uploaded GCS prefixes should be retained for diagnosis or removed by
an authorized operator after review. The instrument uploader itself must not
perform that deletion.

## Remaining Inputs

Collect these values before implementation or during each preflight:

- Instrument names, models, serial identifiers, and responsible owners.
- Actual shell usernames and permitted sudo operations.
- Actual run-output roots and completion markers.
- Local SSH and IRM hostnames, addresses, and ports.
- Machine-to-bucket and prefix mappings.
- GCP group authorized to administer the relay.
- Real completed run fixtures for both instrument families.
- Illumina support guidance for MiSeq i100 shell access.
- Approved maintenance windows for installation and reboot testing.
