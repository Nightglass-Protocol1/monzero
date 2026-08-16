#include "gtest/gtest.h"

#include "cryptonote_basic/asset_wire.h"
#include "cryptonote_basic/cryptonote_format_utils.h"
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
    crypto::public_key tx_public{};
    crypto::secret_key tx_secret{};
    crypto::generate_keys(tx_public, tx_secret);
    cryptonote::assets::asset_recipient_data recipient{};
    recipient.destination = destination;
    recipient.tx_public_key = tx_public;
    payload.output_recipients.push_back({recipient});
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
  excessive.output_recipients.resize(excessive.balances.size(),
    payload.output_recipients.front());
  EXPECT_FALSE(cryptonote::assets::encode_asset_transaction_payload(
    excessive, trailing, &error));
}

TEST(asset_wire, deterministic_output_identity_binds_every_field)
{
  const auto payload = make_payload();
  cryptonote::assets::confidential_asset_output output{
    payload.output_recipients.front().front().destination,
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
  payload.output_recipients.push_back({cryptonote::assets::asset_recipient_data{}});
  std::vector<uint8_t> encoded;
  std::string error;
  ASSERT_TRUE(cryptonote::assets::encode_asset_transaction_payload(
    payload, encoded, &error)) << error;
  ASSERT_EQ(589u, encoded.size());
  const crypto::hash digest = crypto::cn_fast_hash(encoded.data(), encoded.size());
  ASSERT_EQ("35006295aa9f7fe02efc24d0ba9dd10bc1c498b3f1466fad35fb677a4bea3994",
    epee::string_tools::pod_to_hex(digest));
}

TEST(asset_wire, rejects_noncanonical_recipient_encryption)
{
  auto payload = make_payload();
  payload.output_recipients.front().front().encrypted_amount.mask.bytes[0] = 1;
  std::vector<uint8_t> encoded;
  std::string error;
  EXPECT_FALSE(cryptonote::assets::encode_asset_transaction_payload(
    payload, encoded, &error));

  payload = make_payload();
  payload.output_recipients.front().front().tx_public_key = crypto::public_key{};
  EXPECT_FALSE(cryptonote::assets::verify_asset_transaction_payload(payload, {},
    cryptonote::TESTNET, payload.carrier_prefix_hash, &error));
}

TEST(asset_wire, native_extra_envelope_has_non_circular_carrier_and_rejects_duplicates)
{
  cryptonote::transaction tx;
  tx.version = 2;
  tx.unlock_time = 0;
  crypto::public_key public_key{};
  crypto::secret_key secret_key{};
  crypto::generate_keys(public_key, secret_key);
  ASSERT_TRUE(cryptonote::add_tx_pub_key_to_extra(tx, public_key));
  crypto::hash carrier_before{};
  std::string error;
  ASSERT_TRUE(cryptonote::get_transaction_asset_carrier_hash(
    tx, carrier_before, &error)) << error;

  auto payload = make_payload();
  payload.carrier_prefix_hash = carrier_before;
  std::vector<uint8_t> encoded;
  ASSERT_TRUE(cryptonote::assets::encode_asset_transaction_payload(
    payload, encoded, &error)) << error;
  ASSERT_TRUE(cryptonote::add_monzero_asset_tx_extra(tx.extra, encoded, &error)) << error;
  EXPECT_NE(carrier_before, cryptonote::get_transaction_prefix_hash(tx));
  crypto::hash carrier_after{};
  ASSERT_TRUE(cryptonote::get_transaction_asset_carrier_hash(
    tx, carrier_after, &error)) << error;
  EXPECT_EQ(carrier_before, carrier_after);

  std::vector<uint8_t> extracted;
  bool found = false;
  ASSERT_TRUE(cryptonote::get_monzero_asset_tx_extra(
    tx.extra, extracted, found, &error)) << error;
  ASSERT_TRUE(found);
  EXPECT_EQ(encoded, extracted);
  boost::optional<cryptonote::assets::asset_transaction_payload> native_payload;
  EXPECT_FALSE(cryptonote::assets::parse_native_asset_transaction(tx,
    HF_VERSION_MONZERO_ASSETS - 1, cryptonote::TESTNET, native_payload, &error));
  ASSERT_TRUE(cryptonote::assets::parse_native_asset_transaction(tx,
    HF_VERSION_MONZERO_ASSETS, cryptonote::TESTNET, native_payload, &error)) << error;
  ASSERT_TRUE(native_payload);
  EXPECT_EQ(carrier_before, native_payload->carrier_prefix_hash);
  EXPECT_FALSE(cryptonote::assets::parse_native_asset_transaction(tx,
    HF_VERSION_MONZERO_ASSETS, cryptonote::MAINNET, native_payload, &error));
  EXPECT_FALSE(cryptonote::add_monzero_asset_tx_extra(tx.extra, encoded, &error));

  std::vector<uint8_t> encoded_field;
  ASSERT_TRUE(cryptonote::add_monzero_asset_tx_extra(encoded_field, encoded, &error));
  tx.extra.insert(tx.extra.end(), encoded_field.begin(), encoded_field.end());
  EXPECT_FALSE(cryptonote::get_monzero_asset_tx_extra(
    tx.extra, extracted, found, &error));
  EXPECT_FALSE(cryptonote::get_transaction_asset_carrier_hash(
    tx, carrier_after, &error));
}

TEST(asset_wire, native_envelope_does_not_expand_standard_extra_allowance)
{
  cryptonote::transaction tx;
  tx.version = 2;
  for (size_t index = 0; index < 5; ++index)
    ASSERT_TRUE(cryptonote::add_extra_nonce_to_tx_extra(tx.extra,
      cryptonote::blobdata(TX_EXTRA_NONCE_MAX_COUNT, static_cast<char>(index + 1))));
  ASSERT_GT(tx.extra.size(), MAX_TX_EXTRA_SIZE);

  crypto::hash carrier{};
  std::string error;
  ASSERT_TRUE(cryptonote::get_transaction_asset_carrier_hash(tx, carrier, &error)) << error;
  auto payload = make_payload();
  payload.carrier_prefix_hash = carrier;
  std::vector<uint8_t> encoded;
  ASSERT_TRUE(cryptonote::assets::encode_asset_transaction_payload(
    payload, encoded, &error)) << error;
  ASSERT_TRUE(cryptonote::add_monzero_asset_tx_extra(tx.extra, encoded, &error)) << error;

  boost::optional<cryptonote::assets::asset_transaction_payload> native_payload;
  EXPECT_FALSE(cryptonote::assets::parse_native_asset_transaction(tx,
    HF_VERSION_MONZERO_ASSETS, cryptonote::TESTNET, native_payload, &error));
  EXPECT_NE(std::string::npos, error.find("standard limit"));
}
