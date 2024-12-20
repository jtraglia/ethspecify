# eth-spec-tags

A tool for referencing the Ethereum specifications in clients.

## Getting Started

### Add Spec Tags

In your client, add an HTML tag (don't forget the closing tag) like this:

```c
/**
 * <spec function="is_fully_withdrawable_validator" fork="deneb"></spec>
 */
```

This supports all languages and comment styles. It preserves indentation, so something like this
would also work:

```csharp
/// <spec function="is_compounding_withdrawal_credential" fork="electra"></spec>
```

After the script is finished executing, the spec tag will be updated to be:

```csharp
/// <spec function="is_compounding_withdrawal_credential" fork="electra">
/// def is_compounding_withdrawal_credential(withdrawal_credentials: Bytes32) -> bool:
///     return withdrawal_credentials[:1] == COMPOUNDING_WITHDRAWAL_PREFIX
/// </spec>
```

### Running the Script

First, clone the repository. You only need the latest commit.

```bash
git clone https://github.com/jtraglia/eth-spec-tags.git --depth=1
cd eth-spec-tags
```

Then, run the `update_spec_tags.py` script and provide the path to your client.

```bash
./update_spec_tags.py --project-path=~/Projects/client
Processing file: /Users/user/Projects/client/src/file.ext
spec tag: {'custom_type': 'Blob', 'fork': 'electra'}
spec tag: {'dataclass': 'PayloadAttributes', 'fork': 'electra'}
spec tag: {'ssz_object': 'ConsolidationRequest', 'fork': 'electra'}
```

### Specification Options

#### Version

This attribute can be a release version (_e.g._, `version="v1.5.0-alpha.10"`) or "nightly" to get
the latest & greatest. The nightly specifications are updated everyday at UTC midnight.

#### Fork

This attribute can be any of the [executable
specifications](https://github.com/ethereum/consensus-specs/blob/e6bddd966214a19d2b97199bbe3c02577a22a8b4/Makefile#L3-L15)
in the consensus-specs. At the time of writing, these are: phase0, altair, bellatrix, capella,
deneb, electra, fulu, whisk, eip6800, and eip7732.

### Supported Specification Items

#### Constants

These are items found in the `Constants` section of the specifications.

```c
/**
 * <spec constant_var="COMPOUNDING_WITHDRAWAL_PREFIX" fork="electra">
 * COMPOUNDING_WITHDRAWAL_PREFIX: Bytes1 = '0x02'
 * </spec>
 */
```

#### Custom Types

These are items found in the `Custom types` section of the specifications.

```c
/**
 * <spec custom_type="Blob" fork="electra">
 * Blob = ByteVector[BYTES_PER_FIELD_ELEMENT * FIELD_ELEMENTS_PER_BLOB]
 * </spec>
 */
```

#### Preset Variables

These are items found in the
[`presets`](https://github.com/ethereum/consensus-specs/tree/dev/presets) directory.

For preset variables, in addition to the `preset_var` attribute, you can specify a `preset`
attribute: minimal or mainnet.

```c
/**
 * <spec preset="minimal" preset_var="PENDING_CONSOLIDATIONS_LIMIT" fork="electra">
 * PENDING_CONSOLIDATIONS_LIMIT: uint64 = 64
 * </spec>
 *
 * <spec preset="mainnet" preset_var="PENDING_CONSOLIDATIONS_LIMIT" fork="electra">
 * PENDING_CONSOLIDATIONS_LIMIT: uint64 = 262144
 * </spec>
 */
```

It's not strictly necessary to specify the preset attribute. The default preset is mainnet.

```c
/**
 * <spec preset_var="FIELD_ELEMENTS_PER_BLOB" fork="electra">
 * FIELD_ELEMENTS_PER_BLOB: uint64 = 4096
 * </spec>
 */
```

#### Config Variables

These are items found in the
[`configs`](https://github.com/ethereum/consensus-specs/tree/dev/presets) directory.

```c
/**
 * <spec config_var="MAX_REQUEST_BLOB_SIDECARS" fork="electra">
 * MAX_REQUEST_BLOB_SIDECARS = 768
 * </spec>
 */
```

#### SSZ Objects

These are items found in the `Containers` section of the specifications.

```c
/**
 * <spec ssz_object="ConsolidationRequest" fork="electra">
 * class ConsolidationRequest(Container):
 *     source_address: ExecutionAddress
 *     source_pubkey: BLSPubkey
 *     target_pubkey: BLSPubkey
 * </spec>
 */
```

#### Dataclasses

These are classes with the `@dataclass` decorator.

```c
/**
 * <spec dataclass="PayloadAttributes" fork="electra">
 * class PayloadAttributes(object):
 *     timestamp: uint64
 *     prev_randao: Bytes32
 *     suggested_fee_recipient: ExecutionAddress
 *     withdrawals: Sequence[Withdrawal]
 *     parent_beacon_block_root: Root  # [New in Deneb:EIP4788]
 * </spec>
 */
```

#### Functions

These are all the functions found in the specifications.

```c
/**
 * <spec function="is_fully_withdrawable_validator" fork="deneb">
 * def is_fully_withdrawable_validator(validator: Validator, balance: Gwei, epoch: Epoch) -> bool:
 *     """
 *     Check if ``validator`` is fully withdrawable.
 *     """
 *     return (
 *         has_eth1_withdrawal_credential(validator)
 *         and validator.withdrawable_epoch <= epoch
 *         and balance > 0
 *     )
 * </spec>
 */
```

```c
/**
 * <spec function="is_fully_withdrawable_validator" fork="electra">
 * def is_fully_withdrawable_validator(validator: Validator, balance: Gwei, epoch: Epoch) -> bool:
 *     """
 *     Check if ``validator`` is fully withdrawable.
 *     """
 *     return (
 *         has_execution_withdrawal_credential(validator)  # [Modified in Electra:EIP7251]
 *         and validator.withdrawable_epoch <= epoch
 *         and balance > 0
 *     )
 * </spec>
 */
```