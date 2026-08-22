# Offline asset issuance workflow

Status: experimental and inactive

Monzero assets are not active at consensus on the currently configured
networks. `asset_create` and `asset_inspect` therefore provide a safe offline
workflow today. The activation-gated `asset_issue` path is also implemented,
but refuses to construct a transaction until the connected daemon reports the
asset hard fork active. Do not represent an exported artifact as an issued
token or NFT.

## Create an artifact

Open a full software wallet on the intended network, then run:

```text
asset_create <class> <atomic_supply> <decimals> <metadata_hash|none> <metadata_reference|none> <collection_id|none> <filename>
```

Classes are `fungible`, `nft`, `collection`, and `edition`.

Examples:

```text
asset_create fungible 100000000 2 none ipfs://example none token.mzi
asset_create nft 1 0 <64-character-metadata-hash> ipfs://example none artwork.mzi
asset_create collection 1 0 none ipfs://example none collection.mzi
asset_create edition 100 0 <64-character-metadata-hash> ipfs://example <collection-id> edition.mzi
```

NFTs and collections require a supply of one and zero decimals. Editions are
indivisible. NFTs and editions require a non-zero metadata content hash. A
collection member is authorized with the current wallet's primary spend key;
future registry validation will only accept it if that wallet controls the
referenced collection.

Creation is rejected for watch-only, background, multisig, and hardware
wallets. Those signing modes need separate reviewed protocols before support.

## Inspect an artifact

```text
asset_inspect <filename>
```

Inspection validates the bounded canonical payload, issuer signature, declared
asset ID, network, class invariants, and inactive marker. A collection signature
can be identified in isolation, but its authority cannot be established until
the referenced collection is available in an authenticated asset registry.

Metadata references and their content are public and untrusted. Applications
must verify downloaded metadata against the signed metadata hash and must not
execute active content.

## Issue after activation

Once the connected daemon reports the asset hard fork active, a full software
wallet can construct and submit an issuance directly:

```text
asset_issue <address> <fungible|nft|collection|edition> <atomic_supply> <decimals> <metadata_hash|none> <metadata_reference|none> <collection_id|none>
```

The command constructs exactly one native fee-paying transaction, attaches the
signed asset envelope before the native prefix is signed, verifies the finished
envelope, displays the permanent asset ID and fee, and asks for confirmation
before relay. It refuses inactive daemons, light wallets, watch-only wallets,
multisig wallets, and hardware wallets. With `--do-not-relay`, it uses the
wallet's existing raw-transaction save path instead of submission.
