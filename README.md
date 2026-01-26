# ethspecify

A tool for referencing the Ethereum specifications in clients.

The idea is that ethspecify will help developers keep track of when the specification changes. It
will also help auditors verify that the client implementations match the specifications. Ideally,
this is configured as a CI check which notifies client developers when the specification changes.
When that happens, they can update the implementations appropriately.

## Getting started

### Installation

```
pipx install ethspecify
```

### Initialize specrefs

From the root of the client source directory, initialize a directory for specrefs:

```
$ ethspecify init v1.6.0-beta.0
Initializing specrefs directory: v1.6.0-beta.0
Successfully created specrefs directory at: specrefs
```

This creates a `specrefs` directory with `.ethspecify.yml` and YAML files for each spec category
(constants, configs, presets, functions, containers, dataclasses, types).

### Map sources

Edit the YAML files to add sources for where each spec item is implemented.

If it's the entire file:

```yaml
- name: BlobParameters
  sources:
    - file: ethereum/spec/src/main/java/tech/pegasys/teku/spec/logic/versions/fulu/helpers/BlobParameters.java
  spec: |
    <spec dataclass="BlobParameters" fork="fulu" hash="a4575aa8">
    class BlobParameters:
        epoch: Epoch
        max_blobs_per_block: uint64
    </spec>
```

If it's multiple entire files:

```yaml
- name: BlobsBundleDeneb
  sources:
    - file: ethereum/spec/src/main/java/tech/pegasys/teku/spec/datastructures/execution/BlobsBundle.java
    - file: ethereum/spec/src/main/java/tech/pegasys/teku/spec/datastructures/builder/BlobsBundleSchema.java
    - file: ethereum/spec/src/main/java/tech/pegasys/teku/spec/datastructures/builder/versions/deneb/BlobsBundleDeneb.java
    - file: ethereum/spec/src/main/java/tech/pegasys/teku/spec/datastructures/builder/versions/deneb/BlobsBundleSchemaDeneb.java
  spec: |
    <spec dataclass="BlobsBundle" fork="deneb" hash="8d6e7be6">
    class BlobsBundle(object):
        commitments: List[KZGCommitment, MAX_BLOB_COMMITMENTS_PER_BLOCK]
        proofs: List[KZGProof, MAX_BLOB_COMMITMENTS_PER_BLOCK]
        blobs: List[Blob, MAX_BLOB_COMMITMENTS_PER_BLOCK]
    </spec>
```

If it's a specific part of a file:

```yaml
- name: EFFECTIVE_BALANCE_INCREMENT
  sources:
    - file: ethereum/spec/src/main/resources/tech/pegasys/teku/spec/config/presets/mainnet/phase0.yaml
      search: "EFFECTIVE_BALANCE_INCREMENT:"
  spec: |
    <spec preset_var="EFFECTIVE_BALANCE_INCREMENT" fork="phase0" hash="23dfe52c">
    EFFECTIVE_BALANCE_INCREMENT: Gwei = 1000000000
    </spec>
```

You can also use regex in the searches if that is necessary:

```yaml
- name: ATTESTATION_DUE_BPS
  sources:
    - file: ethereum/spec/src/main/resources/tech/pegasys/teku/spec/config/configs/mainnet.yaml
      search: "^ATTESTATION_DUE_BPS:"
      regex: true
  spec: |
    <spec config_var="ATTESTATION_DUE_BPS" fork="phase0" hash="929dd1c9">
    ATTESTATION_DUE_BPS: uint64 = 3333
    </spec>
```

### Check specrefs

Run the check command in CI to verify all spec items are properly mapped:

```
$ ethspecify check --path=specrefs
MISSING: constants.BLS_MODULUS#deneb
```

### Add exceptions

Some spec items may not be implemented in your client. Add them to the exceptions list in
`specrefs/.ethspecify.yml`:

```yaml
specrefs:
  files:
    - containers.yml
    - functions.yml
    # ...

exceptions:
  containers:
    # Not defined, unnecessary
    - Eth1Block

  functions:
    # No light client support
    - is_valid_light_client_header
    - process_light_client_update
```

## Style Options

This attribute can be used to change how the specification content is shown.

### `hash` (default)

This style adds a hash of the specification content to the spec tag, without showing the content.

```
<spec fn="apply_deposit" fork="electra" hash="c723ce7b" />
```

> [!NOTE]
> The hash is the first 8 characters of the specification content's SHA256 digest.

### `full`

This style displays the whole content of this specification item, including comments.

```
<spec fn="is_fully_withdrawable_validator" fork="deneb" style="full">
def is_fully_withdrawable_validator(validator: Validator, balance: Gwei, epoch: Epoch) -> bool:
    """
    Check if ``validator`` is fully withdrawable.
    """
    return (
        has_eth1_withdrawal_credential(validator)
        and validator.withdrawable_epoch <= epoch
        and balance > 0
    )
</spec>
```

### `link`

This style displays an ethspec.tools link to the specification item.

```
<spec fn="apply_pending_deposit" fork="electra" style="link" hash="83ee9126">
https://ethspec.tools/#specs/v1.7.0-alpha.1/functions-apply_pending_deposit-electra
</spec>
```

### `diff`

This style displays a diff with the previous fork's version of the specification.

```
<spec ssz_object="BeaconState" fork="electra" style="diff">
--- deneb
+++ electra
@@ -27,3 +27,12 @@
     next_withdrawal_index: WithdrawalIndex
     next_withdrawal_validator_index: ValidatorIndex
     historical_summaries: List[HistoricalSummary, HISTORICAL_ROOTS_LIMIT]
+    deposit_requests_start_index: uint64
+    deposit_balance_to_consume: Gwei
+    exit_balance_to_consume: Gwei
+    earliest_exit_epoch: Epoch
+    consolidation_balance_to_consume: Gwei
+    earliest_consolidation_epoch: Epoch
+    pending_deposits: List[PendingDeposit, PENDING_DEPOSITS_LIMIT]
+    pending_partial_withdrawals: List[PendingPartialWithdrawal, PENDING_PARTIAL_WITHDRAWALS_LIMIT]
+    pending_consolidations: List[PendingConsolidation, PENDING_CONSOLIDATIONS_LIMIT]
</spec>
```

> [!NOTE]
> Comments are stripped from the specifications when the `diff` style is used. We do this because
> these complicate the diff; the "[Modified in Fork]" comments aren't valuable here.

This can be used with any specification item, like functions too:

```
<spec fn="is_eligible_for_activation_queue" fork="electra" style="diff">
--- phase0
+++ electra
@@ -4,5 +4,5 @@
     """
     return (
         validator.activation_eligibility_epoch == FAR_FUTURE_EPOCH
-        and validator.effective_balance == MAX_EFFECTIVE_BALANCE
+        and validator.effective_balance >= MIN_ACTIVATION_BALANCE
     )
</spec>
```
