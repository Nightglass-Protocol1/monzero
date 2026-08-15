#include "gtest/gtest.h"

#include "cryptonote_basic/asset_wire.h"
#include "ringct/bulletproofs_plus.h"
#include "ringct/rctOps.h"
#include "string_tools.h"

namespace
{
  cryptonote::assets::asset_transaction_payload make_payload()
  {
    cryptonote::assets::asset_transaction_payload payload;
    payload.network = cryptonote::TESTNET;
    payload.carrier_prefix_hash.data[0] = 0xc1;

    crypto::public_key issuer{};
    crypto::secret_key issuer_secret{};
    crypto::generate_keys(issuer, issuer_secret);
    cryptonote::assets::issuance_payload issuance;
    issuance.descriptor.network = cryptonote::TESTNET;
    issuance.descriptor.issuer_key = issuer;
    issuance.descriptor.issuance_nonce.data[0] = 0xc2;
    issuance.descriptor.atomic_supply = 10;
    issuance.descriptor.display_decimals = 0;
    issuance.descriptor.metadata_reference = "ipfs://monzero-wire-vector";
    crypto::hash authorization{};
    if (!cryptonote::assets::derive_issuance_authorization_hash(
          issuance.descriptor, authorization))
      throw std::runtime_error("failed to derive issuance authorization");
    crypto::generate_signature(authorization, issuer, issuer_secret,
      issuance.issuer_signature);
    payload.issuance = issuance;

    crypto::hash id{};
    if (!cryptonote::assets::derive_asset_id(issuance.descriptor, id))
      throw std::runtime_error("failed to derive asset id");
    cryptonote::assets::confidential_asset_balance balance;
    balance.asset_id = id;
    balance.pseudo_inputs.push_back({id, rct::commit(10, rct::zero())});
    balance.outputs.push_back(rct::commit(10, rct::zero()));
    balance.range_proofs.push_back(
      rct::bulletproof_plus_PROVE(10, rct::zero()));
    payload.balances.push_back(balance);
    rct::key secret{}, destination{};
    rct::skpkGen(secret, destination);
    payload.output_destinations.push_back({destination});
    return payload;
  }
}

TEST(asset_wire, canonical_round_trip_preserves_verified_issuance)
{
  const auto original = make_payload();
  std::vector<uint8_t> encoded, reencoded;
  std::string error;
  ASSERT_TRUE(cryptonote::assets::encode_asset_transaction_payload(
    original, encoded, &error)) << error;
  cryptonote::assets::asset_transaction_payload decoded;
  ASSERT_TRUE(cryptonote::assets::decode_asset_transaction_payload(
    encoded, decoded, &error)) << error;
  ASSERT_TRUE(cryptonote::assets::encode_asset_transaction_payload(
    decoded, reencoded, &error)) << error;
  ASSERT_EQ(encoded, reencoded);
  ASSERT_TRUE(decoded.issuance);
  ASSERT_TRUE(cryptonote::assets::verify_confidential_asset_transaction(
    decoded.balances, {}, decoded.issuance->descriptor, &error)) << error;
  ASSERT_TRUE(cryptonote::assets::verify_asset_transaction_payload(
    decoded, {}, cryptonote::TESTNET, decoded.carrier_prefix_hash, &error)) << error;
  EXPECT_FALSE(cryptonote::assets::verify_asset_transaction_payload(
    decoded, {}, cryptonote::MAINNET, decoded.carrier_prefix_hash, &error));
  crypto::hash other_carrier = decoded.carrier_prefix_hash;
  other_carrier.data[1] = 1;
  EXPECT_FALSE(cryptonote::assets::verify_asset_transaction_payload(
    decoded, {}, cryptonote::TESTNET, other_carrier, &error));
}

TEST(asset_wire, rejects_every_truncation_trailing_bytes_and_noncanonical_counts)
{
  const auto payload = make_payload();
  std::vector<uint8_t> encoded;
  std::string error;
  ASSERT_TRUE(cryptonote::assets::encode_asset_transaction_payload(
    payload, encoded, &error)) << error;
  for (size_t size = 0; size < encoded.size(); ++size)
  {
    cryptonote::assets::asset_transaction_payload decoded;
    const std::vector<uint8_t> truncated(encoded.begin(), encoded.begin() + size);
    EXPECT_FALSE(cryptonote::assets::decode_asset_transaction_payload(
      truncated, decoded, &error)) << "accepted truncation at " << size;
  }
  auto trailing = encoded;
  trailing.push_back(0);
  cryptonote::assets::asset_transaction_payload decoded;
  EXPECT_FALSE(cryptonote::assets::decode_asset_transaction_payload(
    trailing, decoded, &error));
  auto unsupported = encoded;
  unsupported[0] = 2;
  EXPECT_FALSE(cryptonote::assets::decode_asset_transaction_payload(
    unsupported, decoded, &error));
  auto excessive = payload;
  excessive.balances.resize(cryptonote::assets::MAX_ASSET_BALANCE_GROUPS + 1,
    payload.balances.front());
  excessive.output_destinations.resize(excessive.balances.size(),
    payload.output_destinations.front());
  EXPECT_FALSE(cryptonote::assets::encode_asset_transaction_payload(
    excessive, trailing, &error));
}

TEST(asset_wire, deterministic_output_identity_binds_every_field)
{
  const auto payload = make_payload();
  cryptonote::assets::confidential_asset_output output{
    payload.output_destinations.front().front(),
    payload.balances.front().outputs.front()};
  crypto::hash first{}, repeated{}, changed{};
  std::string error;
  ASSERT_TRUE(cryptonote::assets::derive_asset_output_id(
    cryptonote::TESTNET, payload.carrier_prefix_hash, payload.balances.front().asset_id, 0,
    output, first, &error)) << error;
  ASSERT_TRUE(cryptonote::assets::derive_asset_output_id(
    cryptonote::TESTNET, payload.carrier_prefix_hash, payload.balances.front().asset_id, 0,
    output, repeated, &error));
  EXPECT_EQ(first, repeated);
  ASSERT_TRUE(cryptonote::assets::derive_asset_output_id(
    cryptonote::MAINNET, payload.carrier_prefix_hash, payload.balances.front().asset_id, 0,
    output, changed, &error));
  EXPECT_NE(first, changed);
  ASSERT_TRUE(cryptonote::assets::derive_asset_output_id(
    cryptonote::TESTNET, payload.carrier_prefix_hash, payload.balances.front().asset_id, 1,
    output, changed, &error));
  EXPECT_NE(first, changed);
  output.commitment = rct::commit(9, rct::zero());
  ASSERT_TRUE(cryptonote::assets::derive_asset_output_id(
    cryptonote::TESTNET, payload.carrier_prefix_hash, payload.balances.front().asset_id, 0,
    output, changed, &error));
  EXPECT_NE(first, changed);
}

TEST(asset_wire, fixed_wire_vector_has_stable_size_and_digest)
{
  cryptonote::assets::asset_transaction_payload payload;
  payload.network = cryptonote::STAGENET;
  payload.carrier_prefix_hash.data[0] = 0xe1;
  cryptonote::assets::confidential_asset_balance balance;
  balance.asset_id.data[0] = 0xe2;
  balance.pseudo_inputs.push_back({balance.asset_id, rct::key{}});
  balance.outputs.push_back(rct::key{});
  rct::BulletproofPlus proof;
  proof.A = rct::key{};
  proof.A1 = rct::key{};
  proof.B = rct::key{};
  proof.r1 = rct::key{};
  proof.s1 = rct::key{};
  proof.d1 = rct::key{};
  proof.V.resize(1);
  proof.L.resize(1);
  proof.R.resize(1);
  balance.range_proofs.push_back(proof);
  payload.balances.push_back(balance);
  payload.output_destinations.push_back({rct::key{}});
  std::vector<uint8_t> encoded;
  std::string error;
  ASSERT_TRUE(cryptonote::assets::encode_asset_transaction_payload(
    payload, encoded, &error)) << error;
  ASSERT_EQ(492u, encoded.size());
  const crypto::hash digest = crypto::cn_fast_hash(encoded.data(), encoded.size());
  ASSERT_EQ("7ad38e0c9b90d1d458f69df1ca5c4c27689ba0c86e0fbcb08a2149166b3d999b",
    epee::string_tools::pod_to_hex(digest));
}
