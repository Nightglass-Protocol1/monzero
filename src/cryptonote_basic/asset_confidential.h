#pragma once

#include <set>
#include <string>
#include <vector>

#include "asset_types.h"
#include "ringct/rctTypes.h"

namespace cryptonote
{
namespace assets
{
  constexpr size_t MAX_CONFIDENTIAL_ASSET_INPUTS = 16;
  constexpr size_t MAX_CONFIDENTIAL_ASSET_OUTPUTS = 16;

  struct confidential_pseudo_input
  {
    crypto::hash source_asset_id{};
    rct::key commitment{};
  };

  struct confidential_asset_balance
  {
    crypto::hash asset_id{};
    std::vector<confidential_pseudo_input> pseudo_inputs;
    rct::keyV outputs;
    rct::keyV burns;
    std::vector<rct::BulletproofPlus> range_proofs;
  };

  bool verify_confidential_asset_balance(
    const confidential_asset_balance& balance,
    std::string* error = nullptr);

  bool verify_confidential_asset_transaction(
    const std::vector<confidential_asset_balance>& balances,
    const std::set<crypto::hash>& known_assets,
    const boost::optional<issuance_descriptor>& issuance,
    std::string* error = nullptr);
}
}
