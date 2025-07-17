# ethspecify

A tool for referencing the Ethereum specifications in clients.

The idea is that ethspecify will help developers keep track of when the specification changes. It
will also help auditors verify that the client implementations match the specifications. Ideally,
this is configured as a CI check which notifies client developers when the specification changes.
When that happens, they can update the implementations appropriately.

## Getting Started

### Installation

```
python3 -mpip install ethspecify
```

### Adding Spec Tags

In your client, add HTML tags like this:

```
/*
 * <spec fn="is_fully_withdrawable_validator" fork="deneb" />
 */
```

```
/*
 * <spec ssz_object="BeaconState" fork="electra" style="diff" />
 */
```

### Populating Spec Tags

Then, navigate to your codebase and run `ethspecify`:

```
ethspecify
```

## Specification Options

### Version

This attribute specifies which version of the consensus specifications to use. Default is `nightly`.

- `nightly` (default) - Uses the latest nightly build from the master branch
- `v1.6.0-alpha.2`, `v1.6.0-alpha.3`, etc. - Uses a specific tagged release version

Example:
```
/*
 * <spec fn="apply_deposit" fork="electra" version="v1.6.0-alpha.3" />
 */
```

### Fork

This attribute can be any of the [executable
specifications](https://github.com/ethereum/consensus-specs/blob/e6bddd966214a19d2b97199bbe3c02577a22a8b4/Makefile#L3-L15)
in the consensus-specs. At the time of writing, these are: phase0, altair, bellatrix, capella,
deneb, electra, fulu, whisk, eip6800, and eip7732.

### Style

This attribute can be used to change how the specification content is shown.

#### `hash` (default)

This style adds a hash of the specification content to the spec tag, without showing the content.

```
/*
 * <spec fn="apply_deposit" fork="electra" hash="c723ce7b" />
 */
```

> [!NOTE]
> The hash is the first 8 characters of the specification content's SHA256 digest.

#### `full`

This style displays the whole content of this specification item, including comments.

```
/*
 * <spec fn="is_fully_withdrawable_validator" fork="deneb" style="full">
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

#### `link`

This style displays a GitHub link to the specification item.

```
/*
 * <spec fn="apply_pending_deposit" fork="electra" style="link" hash="83ee9126">
 * https://github.com/ethereum/consensus-specs/blob/dev/specs/electra/beacon-chain.md#new-apply_pending_deposit
 * </spec>
 */
```

#### `diff`

This style displays a diff with the previous fork's version of the specification.

```
/*
 * <spec ssz_object="BeaconState" fork="electra" style="diff">
 * --- deneb
 * +++ electra
 * @@ -27,3 +27,12 @@
 *      next_withdrawal_index: WithdrawalIndex
 *      next_withdrawal_validator_index: ValidatorIndex
 *      historical_summaries: List[HistoricalSummary, HISTORICAL_ROOTS_LIMIT]
 * +    deposit_requests_start_index: uint64
 * +    deposit_balance_to_consume: Gwei
 * +    exit_balance_to_consume: Gwei
 * +    earliest_exit_epoch: Epoch
 * +    consolidation_balance_to_consume: Gwei
 * +    earliest_consolidation_epoch: Epoch
 * +    pending_deposits: List[PendingDeposit, PENDING_DEPOSITS_LIMIT]
 * +    pending_partial_withdrawals: List[PendingPartialWithdrawal, PENDING_PARTIAL_WITHDRAWALS_LIMIT]
 * +    pending_consolidations: List[PendingConsolidation, PENDING_CONSOLIDATIONS_LIMIT]
 * </spec>
 */
```

> [!NOTE]
> Comments are stripped from the specifications when the `diff` style is used. We do this because
> these complicate the diff; the "[Modified in Fork]" comments aren't valuable here.

This can be used with any specification item, like functions too:

```
/*
 * <spec fn="is_eligible_for_activation_queue" fork="electra" style="diff">
 * --- phase0
 * +++ electra
 * @@ -4,5 +4,5 @@
 *      """
 *      return (
 *          validator.activation_eligibility_epoch == FAR_FUTURE_EPOCH
 * -        and validator.effective_balance == MAX_EFFECTIVE_BALANCE
 * +        and validator.effective_balance >= MIN_ACTIVATION_BALANCE
 *      )
 * </spec>
 */
```

## Supported Specification Items

### Constants

These are items found in the `Constants` section of the specifications.

```
/*
 * <spec constant_var="COMPOUNDING_WITHDRAWAL_PREFIX" fork="electra" style="full">
 * COMPOUNDING_WITHDRAWAL_PREFIX: Bytes1 = '0x02'
 * </spec>
 */
```

### Custom Types

These are items found in the `Custom types` section of the specifications.

```
/*
 * <spec custom_type="Blob" fork="electra" style="full">
 * Blob = ByteVector[BYTES_PER_FIELD_ELEMENT * FIELD_ELEMENTS_PER_BLOB]
 * </spec>
 */
```

### Preset Variables

These are items found in the
[`presets`](https://github.com/ethereum/consensus-specs/tree/dev/presets) directory.

For preset variables, in addition to the `preset_var` attribute, you can specify a `preset`
attribute: minimal or mainnet.

```
/*
 * <spec preset="minimal" preset_var="PENDING_CONSOLIDATIONS_LIMIT" fork="electra" style="full">
 * PENDING_CONSOLIDATIONS_LIMIT: uint64 = 64
 * </spec>
 *
 * <spec preset="mainnet" preset_var="PENDING_CONSOLIDATIONS_LIMIT" fork="electra" style="full">
 * PENDING_CONSOLIDATIONS_LIMIT: uint64 = 262144
 * </spec>
 */
```

It's not strictly necessary to specify the preset attribute. The default preset is mainnet.

```
/*
 * <spec preset_var="FIELD_ELEMENTS_PER_BLOB" fork="electra" style="full">
 * FIELD_ELEMENTS_PER_BLOB: uint64 = 4096
 * </spec>
 */
```

### Config Variables

These are items found in the
[`configs`](https://github.com/ethereum/consensus-specs/tree/dev/presets) directory.

```
/*
 * <spec config_var="MAX_REQUEST_BLOB_SIDECARS" fork="electra" style="full">
 * MAX_REQUEST_BLOB_SIDECARS = 768
 * </spec>
 */
```

### SSZ Objects

These are items found in the `Containers` section of the specifications.

```
/*
 * <spec ssz_object="ConsolidationRequest" fork="electra" style="full">
 * class ConsolidationRequest(Container):
 *     source_address: ExecutionAddress
 *     source_pubkey: BLSPubkey
 *     target_pubkey: BLSPubkey
 * </spec>
 */
```

### Dataclasses

These are classes with the `@dataclass` decorator.

```
/*
 * <spec dataclass="PayloadAttributes" fork="electra" style="full">
 * class PayloadAttributes(object):
 *     timestamp: uint64
 *     prev_randao: Bytes32
 *     suggested_fee_recipient: ExecutionAddress
 *     withdrawals: Sequence[Withdrawal]
 *     parent_beacon_block_root: Root  # [New in Deneb:EIP4788]
 * </spec>
 */
```

### Functions

These are all the functions found in the specifications.

For example, two versions of the same function:

```
/*
 * <spec fn="is_fully_withdrawable_validator" fork="deneb" style="full">
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

```
/*
 * <spec fn="is_fully_withdrawable_validator" fork="electra" style="full">
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

With functions, it's possible to specify which line/lines should be displayed. For example:

```
/*
 * <spec fn="is_fully_withdrawable_validator" fork="electra" style="full" lines="5-9">
 * return (
 *     has_execution_withdrawal_credential(validator)  # [Modified in Electra:EIP7251]
 *     and validator.withdrawable_epoch <= epoch
 *     and balance > 0
 * )
 * </spec>
 */
```

Note that the content is automatically dedented.

Or, to display just a single line, only specify a single number. For example:

```
/*
 * <spec fn="is_fully_withdrawable_validator" fork="electra" style="full" lines="6">
 * has_execution_withdrawal_credential(validator)  # [Modified in Electra:EIP7251]
 * </spec>
 */
 ```