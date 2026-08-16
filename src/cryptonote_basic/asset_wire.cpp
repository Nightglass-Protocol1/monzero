#include "asset_wire.h"

#include <cstring>
#include <limits>

#include "cryptonote_format_utils.h"
#include "ringct/rctOps.h"

namespace cryptonote
{
namespace assets
{
static_assert(MAX_ASSET_WIRE_BYTES == TX_EXTRA_MONZERO_ASSET_MAX_COUNT,
  "asset wire and tx-extra envelope limits must remain identical");

namespace
{
  constexpr char OUTPUT_ID_DOMAIN[] = "MonzeroAssetOutputIdV1";

  bool fail(std::string* error, const std::string& message)
  {
    if (error)
      *error = message;
    return false;
  }

  class writer
  {
  public:
    template<typename T> void pod(const T& value)
    {
      const auto* begin = reinterpret_cast<const uint8_t*>(&value);
      bytes.insert(bytes.end(), begin, begin + sizeof(value));
    }
    void count(size_t value) { pod(static_cast<uint8_t>(value)); }
    void u16(uint16_t value)
    {
      bytes.push_back(static_cast<uint8_t>(value));
      bytes.push_back(static_cast<uint8_t>(value >> 8));
    }
    void u32(uint32_t value)
    {
      for (unsigned shift = 0; shift < 32; shift += 8)
        bytes.push_back(static_cast<uint8_t>(value >> shift));
    }
    std::vector<uint8_t> bytes;
  };

  class reader
  {
  public:
    explicit reader(const std::vector<uint8_t>& source) : source_(source) {}
    template<typename T> bool pod(T& value)
    {
      if (offset_ > source_.size() || sizeof(value) > source_.size() - offset_)
        return false;
      std::memcpy(&value, source_.data() + offset_, sizeof(value));
      offset_ += sizeof(value);
      return true;
    }
    bool count(size_t limit, size_t& value)
    {
      uint8_t encoded = 0;
      if (!pod(encoded) || encoded > limit)
        return false;
      value = encoded;
      return true;
    }
    bool u16(uint16_t& value)
    {
      uint8_t low = 0, high = 0;
      if (!pod(low) || !pod(high))
        return false;
      value = static_cast<uint16_t>(low) | (static_cast<uint16_t>(high) << 8);
      return true;
    }
    bool done() const { return offset_ == source_.size(); }
  private:
    const std::vector<uint8_t>& source_;
    size_t offset_ = 0;
  };

  void write_keys(writer& out, const rct::keyV& keys)
  {
    out.count(keys.size());
    for (const rct::key& key : keys)
      out.pod(key);
  }

  bool read_keys(reader& in, size_t limit, rct::keyV& keys)
  {
    size_t count = 0;
    if (!in.count(limit, count))
      return false;
    keys.resize(count);
    for (rct::key& key : keys)
      if (!in.pod(key))
        return false;
    return true;
  }

  void write_range_proof(writer& out, const rct::BulletproofPlus& proof)
  {
    write_keys(out, proof.V);
    out.pod(proof.A); out.pod(proof.A1); out.pod(proof.B);
    out.pod(proof.r1); out.pod(proof.s1); out.pod(proof.d1);
    write_keys(out, proof.L);
    write_keys(out, proof.R);
  }

  bool read_range_proof(reader& in, rct::BulletproofPlus& proof)
  {
    return read_keys(in, MAX_CONFIDENTIAL_ASSET_OUTPUTS, proof.V)
      && in.pod(proof.A) && in.pod(proof.A1) && in.pod(proof.B)
      && in.pod(proof.r1) && in.pod(proof.s1) && in.pod(proof.d1)
      && read_keys(in, 16, proof.L) && read_keys(in, 16, proof.R)
      && !proof.L.empty() && proof.L.size() == proof.R.size();
  }
}

bool validate_asset_transaction_payload_shape(const asset_transaction_payload& payload,
  std::string* error)
{
  if (payload.version != ASSET_TRANSACTION_WIRE_VERSION)
    return fail(error, "unsupported asset transaction wire version");
  if (payload.network != MAINNET && payload.network != TESTNET && payload.network != STAGENET)
    return fail(error, "asset transaction requires a public network");
  if (payload.carrier_prefix_hash == crypto::null_hash)
    return fail(error, "asset transaction has a zero carrier hash");
  if (payload.balances.empty() || payload.balances.size() > MAX_ASSET_BALANCE_GROUPS)
    return fail(error, "asset transaction has an invalid balance-group count");
  if (payload.output_recipients.size() != payload.balances.size())
    return fail(error, "asset transaction output recipients do not match balance groups");
  if (payload.ownership_proofs.size() > MAX_ASSET_OWNERSHIP_PROOFS)
    return fail(error, "asset transaction has too many ownership proofs");
  size_t total_inputs = 0, total_destinations = 0;
  for (size_t group = 0; group < payload.balances.size(); ++group)
  {
    const confidential_asset_balance& balance = payload.balances[group];
    if (balance.pseudo_inputs.empty()
        || balance.pseudo_inputs.size() > MAX_CONFIDENTIAL_ASSET_INPUTS
        || balance.outputs.size() + balance.burns.size() > MAX_CONFIDENTIAL_ASSET_OUTPUTS
        || balance.range_proofs.empty()
        || balance.range_proofs.size() > MAX_ASSET_RANGE_PROOFS)
      return fail(error, "asset balance group exceeds canonical limits");
    if (payload.output_recipients[group].size() != balance.outputs.size())
      return fail(error, "asset output recipient count does not match commitments");
    const rct::key zero = rct::zero();
    for (const asset_recipient_data& recipient : payload.output_recipients[group])
      if (std::memcmp(recipient.encrypted_amount.mask.bytes, zero.bytes,
            sizeof(zero.bytes)) != 0)
        return fail(error, "asset output uses a noncanonical encrypted mask");
    total_inputs += balance.pseudo_inputs.size();
    total_destinations += balance.outputs.size() + balance.burns.size();
    if (total_inputs > MAX_ASSET_TOTAL_INPUTS
        || total_destinations > MAX_ASSET_TOTAL_DESTINATIONS)
      return fail(error, "asset transaction exceeds aggregate input or destination limits");
  }
  for (const asset_ownership_proof& proof : payload.ownership_proofs)
    if (proof.ring.size() != CONFIDENTIAL_ASSET_RING_SIZE
        || proof.signature.s.size() != CONFIDENTIAL_ASSET_RING_SIZE)
      return fail(error, "asset ownership proof has a noncanonical ring size");
  return true;
}

bool encode_asset_transaction_payload(const asset_transaction_payload& payload,
  std::vector<uint8_t>& encoded, std::string* error)
{
  if (!validate_asset_transaction_payload_shape(payload, error))
    return false;
  writer out;
  out.pod(payload.version);
  out.pod(static_cast<uint8_t>(payload.network));
  out.pod(payload.carrier_prefix_hash);
  out.pod(static_cast<uint8_t>(payload.issuance ? 1 : 0));
  if (payload.issuance)
  {
    std::vector<uint8_t> issuance;
    if (!encode_issuance_payload(*payload.issuance, issuance, error))
      return false;
    if (issuance.size() > std::numeric_limits<uint16_t>::max())
      return fail(error, "asset issuance payload is too large");
    out.u16(static_cast<uint16_t>(issuance.size()));
    out.bytes.insert(out.bytes.end(), issuance.begin(), issuance.end());
  }
  out.count(payload.balances.size());
  for (size_t group = 0; group < payload.balances.size(); ++group)
  {
    const confidential_asset_balance& balance = payload.balances[group];
    out.pod(balance.asset_id);
    out.count(balance.pseudo_inputs.size());
    for (const confidential_pseudo_input& input : balance.pseudo_inputs)
    {
      out.pod(input.source_asset_id);
      out.pod(input.commitment);
    }
    out.count(balance.outputs.size());
    for (size_t index = 0; index < balance.outputs.size(); ++index)
    {
      const asset_recipient_data& recipient = payload.output_recipients[group][index];
      out.pod(recipient.destination);
      out.pod(balance.outputs[index]);
      out.pod(recipient.tx_public_key);
      out.pod(recipient.encrypted_amount.mask);
      out.pod(recipient.encrypted_amount.amount);
      out.pod(recipient.view_tag);
    }
    write_keys(out, balance.burns);
    out.count(balance.range_proofs.size());
    for (const rct::BulletproofPlus& proof : balance.range_proofs)
      write_range_proof(out, proof);
  }
  out.count(payload.ownership_proofs.size());
  for (const asset_ownership_proof& proof : payload.ownership_proofs)
  {
    out.pod(proof.asset_id);
    out.pod(proof.pseudo_input);
    out.pod(proof.key_image);
    for (const asset_ring_member& member : proof.ring)
    {
      out.pod(member.asset_id); out.pod(member.output_id);
      out.pod(member.public_output.dest); out.pod(member.public_output.mask);
    }
    out.pod(proof.signature.c1);
    out.pod(proof.signature.D);
    for (const rct::key& response : proof.signature.s)
      out.pod(response);
  }
  if (out.bytes.size() > MAX_ASSET_WIRE_BYTES)
    return fail(error, "asset transaction payload exceeds maximum size");
  encoded = std::move(out.bytes);
  return true;
}

bool decode_asset_transaction_payload(const std::vector<uint8_t>& encoded,
  asset_transaction_payload& payload, std::string* error)
{
  if (encoded.empty() || encoded.size() > MAX_ASSET_WIRE_BYTES)
    return fail(error, "asset transaction payload has an invalid size");
  reader in(encoded);
  asset_transaction_payload candidate;
  uint8_t network = 0, has_issuance = 0;
  if (!in.pod(candidate.version) || !in.pod(network)
      || !in.pod(candidate.carrier_prefix_hash) || !in.pod(has_issuance)
      || has_issuance > 1)
    return fail(error, "truncated asset transaction header");
  candidate.network = static_cast<network_type>(network);
  if (has_issuance)
  {
    uint16_t size = 0;
    if (!in.u16(size))
      return fail(error, "truncated asset issuance length");
    std::vector<uint8_t> issuance(size);
    for (uint8_t& byte : issuance)
      if (!in.pod(byte))
        return fail(error, "truncated asset issuance payload");
    issuance_payload decoded;
    if (!decode_issuance_payload(issuance, decoded, error))
      return false;
    candidate.issuance = decoded;
  }
  size_t groups = 0;
  if (!in.count(MAX_ASSET_BALANCE_GROUPS, groups) || groups == 0)
    return fail(error, "invalid asset balance-group count");
  candidate.balances.resize(groups);
  candidate.output_recipients.resize(groups);
  for (size_t group = 0; group < groups; ++group)
  {
    confidential_asset_balance& balance = candidate.balances[group];
    size_t inputs = 0, outputs = 0, proofs = 0;
    if (!in.pod(balance.asset_id) || !in.count(MAX_CONFIDENTIAL_ASSET_INPUTS, inputs) || inputs == 0)
      return fail(error, "truncated or invalid asset inputs");
    balance.pseudo_inputs.resize(inputs);
    for (confidential_pseudo_input& input : balance.pseudo_inputs)
      if (!in.pod(input.source_asset_id) || !in.pod(input.commitment))
        return fail(error, "truncated asset pseudo input");
    if (!in.count(MAX_CONFIDENTIAL_ASSET_OUTPUTS, outputs))
      return fail(error, "invalid asset output count");
    balance.outputs.resize(outputs);
    candidate.output_recipients[group].resize(outputs);
    for (size_t index = 0; index < outputs; ++index)
    {
      asset_recipient_data& recipient = candidate.output_recipients[group][index];
      if (!in.pod(recipient.destination) || !in.pod(balance.outputs[index])
          || !in.pod(recipient.tx_public_key)
          || !in.pod(recipient.encrypted_amount.mask)
          || !in.pod(recipient.encrypted_amount.amount)
          || !in.pod(recipient.view_tag))
        return fail(error, "truncated asset output");
    }
    if (!read_keys(in, MAX_CONFIDENTIAL_ASSET_OUTPUTS - outputs, balance.burns)
        || !in.count(MAX_ASSET_RANGE_PROOFS, proofs) || proofs == 0)
      return fail(error, "invalid asset burn or range-proof count");
    balance.range_proofs.resize(proofs);
    for (rct::BulletproofPlus& proof : balance.range_proofs)
      if (!read_range_proof(in, proof))
        return fail(error, "truncated or noncanonical asset range proof");
  }
  size_t ownership_count = 0;
  if (!in.count(MAX_ASSET_OWNERSHIP_PROOFS, ownership_count))
    return fail(error, "invalid asset ownership-proof count");
  candidate.ownership_proofs.resize(ownership_count);
  for (asset_ownership_proof& proof : candidate.ownership_proofs)
  {
    if (!in.pod(proof.asset_id) || !in.pod(proof.pseudo_input) || !in.pod(proof.key_image))
      return fail(error, "truncated asset ownership proof");
    proof.ring.resize(CONFIDENTIAL_ASSET_RING_SIZE);
    for (asset_ring_member& member : proof.ring)
      if (!in.pod(member.asset_id) || !in.pod(member.output_id)
          || !in.pod(member.public_output.dest) || !in.pod(member.public_output.mask))
        return fail(error, "truncated asset ownership ring");
    if (!in.pod(proof.signature.c1) || !in.pod(proof.signature.D))
      return fail(error, "truncated asset CLSAG header");
    proof.signature.s.resize(CONFIDENTIAL_ASSET_RING_SIZE);
    for (rct::key& response : proof.signature.s)
      if (!in.pod(response))
        return fail(error, "truncated asset CLSAG responses");
    std::memcpy(&proof.signature.I, &proof.key_image, sizeof(proof.signature.I));
  }
  if (!in.done() || !validate_asset_transaction_payload_shape(candidate, error))
    return fail(error, in.done() ? "invalid asset transaction payload" : "trailing asset transaction bytes");
  payload = std::move(candidate);
  return true;
}

bool verify_asset_transaction_payload(const asset_transaction_payload& payload,
  const std::set<crypto::hash>& known_assets, network_type expected_network,
  const crypto::hash& expected_carrier_prefix_hash, std::string* error)
{
  if (!validate_asset_transaction_payload_shape(payload, error))
    return false;
  if (payload.network != expected_network)
    return fail(error, "asset transaction belongs to a different network");
  if (payload.carrier_prefix_hash != expected_carrier_prefix_hash)
    return fail(error, "asset transaction carrier hash mismatch");
  boost::optional<issuance_descriptor> descriptor;
  if (payload.issuance)
  {
    if (!verify_issuance_authorization(payload.issuance->descriptor,
          payload.issuance->issuer_signature, error))
      return false;
    descriptor = payload.issuance->descriptor;
  }
  for (const std::vector<asset_recipient_data>& recipients : payload.output_recipients)
    for (const asset_recipient_data& recipient : recipients)
    {
      const rct::key identity = rct::identity();
      if (!rct::isInMainSubgroup(recipient.destination)
          || std::memcmp(recipient.destination.bytes, identity.bytes,
               sizeof(identity.bytes)) == 0
          || recipient.tx_public_key == crypto::null_pkey
          || !crypto::check_key(recipient.tx_public_key))
        return fail(error, "asset transaction contains invalid recipient data");
    }
  return verify_confidential_asset_transaction_with_ownership(
    payload.balances, payload.ownership_proofs, known_assets, descriptor,
    expected_network, expected_carrier_prefix_hash, error);
}

bool derive_asset_output_id(network_type network,
  const crypto::hash& carrier_prefix_hash,
  const crypto::hash& asset_id, uint32_t output_index,
  const confidential_asset_output& output, crypto::hash& output_id,
  std::string* error)
{
  if (network != MAINNET && network != TESTNET && network != STAGENET)
    return fail(error, "asset output identity requires a public network");
  if (carrier_prefix_hash == crypto::null_hash || asset_id == crypto::null_hash)
    return fail(error, "asset output identity has a zero carrier or asset id");
  if (!rct::isInMainSubgroup(output.destination)
      || !rct::isInMainSubgroup(output.commitment))
    return fail(error, "asset output identity contains an invalid point");
  writer bytes;
  bytes.bytes.insert(bytes.bytes.end(), OUTPUT_ID_DOMAIN,
    OUTPUT_ID_DOMAIN + sizeof(OUTPUT_ID_DOMAIN) - 1);
  bytes.pod(get_config(network).NETWORK_ID);
  bytes.pod(carrier_prefix_hash); bytes.pod(asset_id);
  bytes.u32(output_index); bytes.pod(output.destination); bytes.pod(output.commitment);
  output_id = crypto::cn_fast_hash(bytes.bytes.data(), bytes.bytes.size());
  return true;
}

bool parse_native_asset_transaction(const transaction_prefix& tx,
  uint8_t hard_fork_version, network_type expected_network,
  boost::optional<asset_transaction_payload>& payload, std::string* error)
{
  payload = boost::none;
  std::vector<uint8_t> encoded;
  bool found = false;
  if (!get_monzero_asset_tx_extra(tx.extra, encoded, found, error))
    return false;
  if (!found)
    return true;
  if (hard_fork_version < HF_VERSION_MONZERO_ASSETS)
    return fail(error, "Monzero asset envelope appears before activation");
  size_t normalized_extra_size = 0;
  if (!get_monzero_asset_normalized_extra_size(tx, normalized_extra_size, error))
    return false;
  if (normalized_extra_size > MAX_TX_EXTRA_SIZE)
    return fail(error, "non-asset transaction extra exceeds the standard limit");
  crypto::hash carrier{};
  if (!get_transaction_asset_carrier_hash(tx, carrier, error))
    return false;
  asset_transaction_payload decoded;
  if (!decode_asset_transaction_payload(encoded, decoded, error))
    return false;
  if (decoded.network != expected_network)
    return fail(error, "native asset envelope belongs to a different network");
  if (decoded.carrier_prefix_hash != carrier)
    return fail(error, "native asset envelope has the wrong carrier hash");
  payload = std::move(decoded);
  return true;
}
}
}
