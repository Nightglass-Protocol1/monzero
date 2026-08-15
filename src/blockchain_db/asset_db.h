#pragma once

#include <string>
#include <vector>

#include "blockchain_db.h"
#include "cryptonote_basic/asset_confidential.h"
#include "cryptonote_basic/asset_types.h"

namespace cryptonote
{
namespace assets
{
  bool load_registry_from_db(
    const BlockchainDB& db,
    network_type expected_network,
    asset_registry& registry,
    std::string* error = nullptr);

  // The caller must hold the blockchain write transaction. Semantic
  // validation finishes before the first database write, and any exception
  // raised by storage must cause that outer transaction to be aborted.
  bool apply_block_extensions_to_db(
    BlockchainDB& db,
    const std::vector<transaction_extension>& extensions,
    const std::vector<crypto::hash>& carrier_prefix_hashes,
    network_type expected_network,
    uint64_t height,
    std::vector<crypto::hash>& asset_ids,
    std::string* error = nullptr);

  // Resolve every claimed ring member against consensus storage and reject
  // key images already spent by an earlier accepted asset transaction before
  // performing the cryptographic ownership check.
  bool verify_asset_ownership_against_db(
    const BlockchainDB& db,
    const asset_ownership_proof& proof,
    network_type expected_network,
    const crypto::hash& carrier_prefix_hash,
    std::string* error = nullptr);
}
}
