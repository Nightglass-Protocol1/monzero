#include "asset_confidential.h"

#include <cstring>

#include "ringct/bulletproofs_plus.h"
#include "ringct/rctOps.h"

namespace cryptonote
{
namespace assets
{
namespace
{
  bool fail(std::string* error, const std::string& message)
  {
    if (error)
      *error = message;
    return false;
  }

  bool valid_points(const rct::keyV& points)
  {
    for (const rct::key& point : points)
      if (!rct::isInMainSubgroup(point))
        return false;
    return true;
  }
}

bool verify_confidential_asset_balance(const confidential_asset_balance& balance, std::string* error)
{
  if (balance.asset_id == crypto::null_hash)
    return fail(error, "confidential balance has a zero asset id");
  if (balance.pseudo_inputs.empty())
    return fail(error, "confidential balance has no pseudo inputs");
  if (balance.outputs.empty() && balance.burns.empty())
    return fail(error, "confidential balance has no outputs or burns");
  if (balance.pseudo_inputs.size() > MAX_CONFIDENTIAL_ASSET_INPUTS
      || balance.outputs.size() + balance.burns.size() > MAX_CONFIDENTIAL_ASSET_OUTPUTS)
    return fail(error, "confidential balance exceeds input or output limits");
  rct::keyV input_commitments;
  input_commitments.reserve(balance.pseudo_inputs.size());
  for (const confidential_pseudo_input& input : balance.pseudo_inputs)
  {
    if (input.source_asset_id != balance.asset_id)
      return fail(error, "pseudo input crosses asset balance domains");
    input_commitments.push_back(input.commitment);
  }
  if (!valid_points(input_commitments) || !valid_points(balance.outputs) || !valid_points(balance.burns))
    return fail(error, "confidential balance contains an invalid curve point");

  const size_t commitment_count = balance.outputs.size() + balance.burns.size();
  size_t proof_commitments = 0;
  rct::keyV proven_commitments;
  proven_commitments.reserve(commitment_count);
  for (const rct::BulletproofPlus& proof : balance.range_proofs)
  {
    if (proof.V.empty() || proof_commitments > commitment_count - proof.V.size())
      return fail(error, "range proofs do not cover the declared commitments exactly");
    try
    {
      if (!rct::bulletproof_plus_VERIFY(proof))
        return fail(error, "invalid asset Bulletproof+");
    }
    catch (const std::exception&)
    {
      return fail(error, "malformed asset Bulletproof+");
    }
    for (const rct::key& scaled : proof.V)
    {
      proven_commitments.push_back(rct::scalarmult8(scaled));
    }
    proof_commitments += proof.V.size();
  }
  if (proof_commitments != commitment_count)
    return fail(error, "range proofs do not cover every output and burn");
  for (size_t index = 0; index < balance.outputs.size(); ++index)
    if (!rct::equalKeys(proven_commitments[index], balance.outputs[index]))
      return fail(error, "range proof output commitment mismatch");
  for (size_t index = 0; index < balance.burns.size(); ++index)
    if (!rct::equalKeys(proven_commitments[balance.outputs.size() + index], balance.burns[index]))
      return fail(error, "range proof burn commitment mismatch");

  const rct::key input_sum = rct::addKeys(input_commitments);
  rct::keyV destinations = balance.outputs;
  destinations.insert(destinations.end(), balance.burns.begin(), balance.burns.end());
  const rct::key output_sum = rct::addKeys(destinations);
  if (!rct::equalKeys(input_sum, output_sum))
    return fail(error, "asset commitments do not conserve value");
  return true;
}

bool verify_confidential_asset_transaction(
  const std::vector<confidential_asset_balance>& balances,
  const std::set<crypto::hash>& known_assets,
  const boost::optional<issuance_descriptor>& issuance,
  std::string* error)
{
  if (balances.empty())
    return fail(error, "confidential asset transaction is empty");
  std::set<crypto::hash> seen;
  crypto::hash issued_id{};
  if (issuance && !derive_asset_id(*issuance, issued_id, error))
    return false;
  bool found_issuance = false;
  for (const confidential_asset_balance& balance : balances)
  {
    if (!seen.insert(balance.asset_id).second)
      return fail(error, "asset appears in more than one balance group");
    const bool is_issuance = issuance && balance.asset_id == issued_id;
    if (!is_issuance && known_assets.count(balance.asset_id) == 0)
      return fail(error, "confidential balance references an unknown asset");
    if (is_issuance)
    {
      if (known_assets.count(balance.asset_id) != 0)
        return fail(error, "confidential issuance duplicates an existing asset");
      if (balance.pseudo_inputs.size() != 1
          || !rct::equalKeys(balance.pseudo_inputs.front().commitment, rct::commit(issuance->atomic_supply, rct::zero()))
          || balance.pseudo_inputs.front().source_asset_id != balance.asset_id)
        return fail(error, "issuance pseudo input does not commit to the fixed supply");
      found_issuance = true;
    }
    if (!verify_confidential_asset_balance(balance, error))
      return false;
  }
  if (issuance && !found_issuance)
    return fail(error, "issuance has no matching confidential balance group");
  return true;
}
}
}
