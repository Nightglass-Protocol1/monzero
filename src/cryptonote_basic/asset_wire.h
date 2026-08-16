#pragma once

#include <string>
#include <vector>

#include <boost/optional.hpp>

#include "asset_confidential.h"
#include "asset_recipient.h"
#include "cryptonote_basic.h"

namespace cryptonote
{
namespace assets
{
  constexpr uint8_t ASSET_TRANSACTION_WIRE_VERSION = 1;
  constexpr size_t MAX_ASSET_BALANCE_GROUPS = 8;
  constexpr size_t MAX_ASSET_TOTAL_INPUTS = 64;
  constexpr size_t MAX_ASSET_TOTAL_DESTINATIONS = 64;
  constexpr size_t MAX_ASSET_OWNERSHIP_PROOFS = 64;
  constexpr size_t MAX_ASSET_RANGE_PROOFS = 16;
  constexpr size_t MAX_ASSET_WIRE_BYTES = 256 * 1024;

  struct confidential_asset_output
  {
    rct::key destination{};
    rct::key commitment{};
  };

  // Inactive canonical payload prototype. The carrier hash is computed from
  // the native transaction prefix with this envelope omitted; activation code
  // must enforce that procedure to avoid a self-referential hash.
  struct asset_transaction_payload
  {
    uint8_t version = ASSET_TRANSACTION_WIRE_VERSION;
    network_type network = UNDEFINED;
    crypto::hash carrier_prefix_hash{};
    boost::optional<issuance_payload> issuance;
    std::vector<confidential_asset_balance> balances;
    std::vector<std::vector<asset_recipient_data>> output_recipients;
    std::vector<asset_ownership_proof> ownership_proofs;
  };

  bool validate_asset_transaction_payload_shape(
    const asset_transaction_payload& payload,
    std::string* error = nullptr);
  bool encode_asset_transaction_payload(
    const asset_transaction_payload& payload,
    std::vector<uint8_t>& encoded,
    std::string* error = nullptr);
  bool decode_asset_transaction_payload(
    const std::vector<uint8_t>& encoded,
    asset_transaction_payload& payload,
    std::string* error = nullptr);
  bool verify_asset_transaction_payload(
    const asset_transaction_payload& payload,
    const std::set<crypto::hash>& known_assets,
    network_type expected_network,
    const crypto::hash& expected_carrier_prefix_hash,
    std::string* error = nullptr);
  bool derive_asset_output_id(
    network_type network,
    const crypto::hash& carrier_prefix_hash,
    const crypto::hash& asset_id,
    uint32_t output_index,
    const confidential_asset_output& output,
    crypto::hash& output_id,
    std::string* error = nullptr);
  bool parse_native_asset_transaction(
    const transaction_prefix& tx,
    uint8_t hard_fork_version,
    network_type expected_network,
    boost::optional<asset_transaction_payload>& payload,
    std::string* error = nullptr);
}
}
