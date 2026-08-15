#include "gtest/gtest.h"

#include <cstring>
#include <limits>
#include <set>
#include <string>
#include <vector>

#include "cryptonote_basic/asset_types.h"
#include "string_tools.h"

namespace
{
  cryptonote::assets::issuance_descriptor make_descriptor(cryptonote::network_type network)
  {
    cryptonote::assets::issuance_descriptor descriptor;
    descriptor.network = network;
    if (!epee::string_tools::hex_to_pod(
          "9b2e4c0281c0b02e7c53291a94d1d0cbff8883f8024f5142ee494ffbbd088071",
          descriptor.issuer_key))
      throw std::runtime_error("invalid fixed issuer key test vector");
    std::memset(descriptor.issuance_nonce.data, 0x42, sizeof(descriptor.issuance_nonce.data));
    descriptor.atomic_supply = UINT64_C(2100000000000000);
    descriptor.display_decimals = 8;
    std::memset(descriptor.metadata_hash.data, 0x24, sizeof(descriptor.metadata_hash.data));
    descriptor.metadata_reference = "ipfs://bafy-monzero-test-vector";
    return descriptor;
  }

  crypto::signature authorize(const cryptonote::assets::issuance_descriptor& descriptor,
    const crypto::public_key& public_key, const crypto::secret_key& secret_key)
  {
    crypto::hash message{};
    if (!cryptonote::assets::derive_issuance_authorization_hash(descriptor, message))
      throw std::runtime_error("could not derive issuance authorization test message");
    crypto::signature signature{};
    crypto::generate_signature(message, public_key, secret_key, signature);
    return signature;
  }
}

TEST(asset_types, deterministic_canonical_identity)
{
  const auto descriptor = make_descriptor(cryptonote::MAINNET);
  crypto::hash first{};
  crypto::hash second{};
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(descriptor, first));
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(descriptor, second));
  EXPECT_EQ(first, second);
  EXPECT_EQ("1a83e64b6ec56327a06ae1d25387b6f1762120e0ec0b532351395d770a9896ce",
    epee::string_tools::pod_to_hex(first));

  std::vector<uint8_t> encoded;
  ASSERT_TRUE(cryptonote::assets::encode_issuance_descriptor(descriptor, encoded));
  ASSERT_GT(encoded.size(), descriptor.metadata_reference.size());
}

TEST(asset_types, canonical_descriptor_round_trip)
{
  for (const auto network : {cryptonote::MAINNET, cryptonote::TESTNET, cryptonote::STAGENET})
  {
    const auto original = make_descriptor(network);
    std::vector<uint8_t> encoded;
    ASSERT_TRUE(cryptonote::assets::encode_issuance_descriptor(original, encoded));

    cryptonote::assets::issuance_descriptor decoded;
    ASSERT_TRUE(cryptonote::assets::decode_issuance_descriptor(encoded, decoded));
    EXPECT_EQ(original.version, decoded.version);
    EXPECT_EQ(original.network, decoded.network);
    EXPECT_EQ(original.type, decoded.type);
    EXPECT_EQ(original.issuer_key, decoded.issuer_key);
    EXPECT_EQ(original.issuance_nonce, decoded.issuance_nonce);
    EXPECT_EQ(original.atomic_supply, decoded.atomic_supply);
    EXPECT_EQ(original.display_decimals, decoded.display_decimals);
    EXPECT_EQ(original.metadata_hash, decoded.metadata_hash);
    EXPECT_EQ(original.collection_id, decoded.collection_id);
    EXPECT_EQ(original.metadata_reference, decoded.metadata_reference);

    std::vector<uint8_t> reencoded;
    ASSERT_TRUE(cryptonote::assets::encode_issuance_descriptor(decoded, reencoded));
    EXPECT_EQ(encoded, reencoded);
  }
}

TEST(asset_types, descriptor_decoder_rejects_truncation_and_noncanonical_lengths)
{
  std::vector<uint8_t> encoded;
  ASSERT_TRUE(cryptonote::assets::encode_issuance_descriptor(
    make_descriptor(cryptonote::TESTNET), encoded));

  cryptonote::assets::issuance_descriptor decoded;
  std::string error;
  for (size_t size = 0; size < encoded.size(); ++size)
  {
    const std::vector<uint8_t> truncated(encoded.begin(), encoded.begin() + size);
    EXPECT_FALSE(cryptonote::assets::decode_issuance_descriptor(truncated, decoded, &error))
      << "accepted truncated size " << size;
  }

  auto trailing = encoded;
  trailing.push_back(0);
  EXPECT_FALSE(cryptonote::assets::decode_issuance_descriptor(trailing, decoded, &error));

  auto bad_domain = encoded;
  bad_domain[0] ^= 1;
  EXPECT_FALSE(cryptonote::assets::decode_issuance_descriptor(bad_domain, decoded, &error));

  auto bad_version = encoded;
  bad_version[sizeof("MonzeroAssetIssuanceV2") - 1]++;
  EXPECT_FALSE(cryptonote::assets::decode_issuance_descriptor(bad_version, decoded, &error));

  // The final two bytes before the reference are its little-endian length.
  const size_t length_offset = encoded.size() - make_descriptor(cryptonote::TESTNET).metadata_reference.size() - 2;
  auto oversized = encoded;
  oversized[length_offset] = 1;
  oversized[length_offset + 1] = 1;
  EXPECT_FALSE(cryptonote::assets::decode_issuance_descriptor(oversized, decoded, &error));
}

TEST(asset_types, authenticated_issuance_payload_round_trip)
{
  crypto::public_key issuer_public{};
  crypto::secret_key issuer_secret{};
  crypto::generate_keys(issuer_public, issuer_secret);

  cryptonote::assets::issuance_payload original;
  original.descriptor = make_descriptor(cryptonote::TESTNET);
  original.descriptor.issuer_key = issuer_public;
  original.issuer_signature = authorize(original.descriptor, issuer_public, issuer_secret);

  std::vector<uint8_t> encoded;
  ASSERT_TRUE(cryptonote::assets::encode_issuance_payload(original, encoded));
  cryptonote::assets::issuance_payload decoded;
  ASSERT_TRUE(cryptonote::assets::decode_issuance_payload(encoded, decoded));
  EXPECT_EQ(original.descriptor.issuer_key, decoded.descriptor.issuer_key);
  EXPECT_EQ(original.issuer_signature, decoded.issuer_signature);
  EXPECT_FALSE(decoded.collection_signature);

  cryptonote::assets::asset_registry registry;
  crypto::hash asset_id{};
  EXPECT_TRUE(registry.apply_issuance(decoded, 1, asset_id));
  EXPECT_TRUE(registry.contains(asset_id));
}

TEST(asset_types, issuance_payload_rejects_tampering_and_signature_shape_errors)
{
  crypto::public_key issuer_public{};
  crypto::secret_key issuer_secret{};
  crypto::generate_keys(issuer_public, issuer_secret);

  cryptonote::assets::issuance_payload payload;
  payload.descriptor = make_descriptor(cryptonote::STAGENET);
  payload.descriptor.issuer_key = issuer_public;
  payload.issuer_signature = authorize(payload.descriptor, issuer_public, issuer_secret);

  std::vector<uint8_t> encoded;
  ASSERT_TRUE(cryptonote::assets::encode_issuance_payload(payload, encoded));
  cryptonote::assets::issuance_payload decoded;
  std::string error;

  for (size_t size = 0; size < encoded.size(); ++size)
  {
    const std::vector<uint8_t> truncated(encoded.begin(), encoded.begin() + size);
    EXPECT_FALSE(cryptonote::assets::decode_issuance_payload(truncated, decoded, &error))
      << "accepted truncated payload size " << size;
  }

  auto tampered = encoded;
  tampered[tampered.size() - 2] ^= 1;
  EXPECT_FALSE(cryptonote::assets::decode_issuance_payload(tampered, decoded, &error));

  payload.collection_signature = crypto::signature{};
  EXPECT_FALSE(cryptonote::assets::encode_issuance_payload(payload, encoded, &error));

  auto member = make_descriptor(cryptonote::STAGENET);
  member.type = cryptonote::assets::asset_class::non_fungible;
  member.atomic_supply = 1;
  member.display_decimals = 0;
  member.issuer_key = issuer_public;
  member.collection_id.data[0] = 1;
  payload.descriptor = member;
  payload.issuer_signature = authorize(member, issuer_public, issuer_secret);
  payload.collection_signature = boost::none;
  EXPECT_FALSE(cryptonote::assets::encode_issuance_payload(payload, encoded, &error));
}

TEST(asset_types, network_domain_separation)
{
  auto mainnet = make_descriptor(cryptonote::MAINNET);
  auto testnet = mainnet;
  testnet.network = cryptonote::TESTNET;
  crypto::hash mainnet_id{};
  crypto::hash testnet_id{};
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(mainnet, mainnet_id));
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(testnet, testnet_id));
  EXPECT_NE(mainnet_id, testnet_id);
}

TEST(asset_types, every_identity_field_is_committed)
{
  const auto original = make_descriptor(cryptonote::MAINNET);
  crypto::hash original_id{};
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(original, original_id));

  auto changed = original;
  changed.atomic_supply++;
  crypto::hash changed_id{};
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(changed, changed_id));
  EXPECT_NE(original_id, changed_id);

  changed = original;
  changed.metadata_reference.push_back('2');
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(changed, changed_id));
  EXPECT_NE(original_id, changed_id);

  changed = original;
  changed.issuance_nonce.data[0] ^= 1;
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(changed, changed_id));
  EXPECT_NE(original_id, changed_id);

  changed = original;
  changed.type = cryptonote::assets::asset_class::edition;
  changed.display_decimals = 0;
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(changed, changed_id));
  EXPECT_NE(original_id, changed_id);

  changed = original;
  changed.type = cryptonote::assets::asset_class::non_fungible;
  changed.atomic_supply = 1;
  changed.display_decimals = 0;
  std::memset(changed.collection_id.data, 0x11, sizeof(changed.collection_id.data));
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(changed, changed_id));
  EXPECT_NE(original_id, changed_id);
}

TEST(asset_types, rejects_invalid_descriptors)
{
  std::string error;
  auto descriptor = make_descriptor(cryptonote::MAINNET);

  descriptor.version++;
  EXPECT_FALSE(cryptonote::assets::validate_issuance_descriptor(descriptor, &error));
  descriptor = make_descriptor(cryptonote::MAINNET);
  descriptor.network = cryptonote::FAKECHAIN;
  EXPECT_FALSE(cryptonote::assets::validate_issuance_descriptor(descriptor, &error));
  descriptor = make_descriptor(cryptonote::MAINNET);
  descriptor.atomic_supply = 0;
  EXPECT_FALSE(cryptonote::assets::validate_issuance_descriptor(descriptor, &error));
  descriptor = make_descriptor(cryptonote::MAINNET);
  descriptor.display_decimals = cryptonote::assets::MAX_DISPLAY_DECIMALS + 1;
  EXPECT_FALSE(cryptonote::assets::validate_issuance_descriptor(descriptor, &error));
  descriptor = make_descriptor(cryptonote::MAINNET);
  descriptor.metadata_reference.assign(cryptonote::assets::MAX_METADATA_REFERENCE_BYTES + 1, 'x');
  EXPECT_FALSE(cryptonote::assets::validate_issuance_descriptor(descriptor, &error));
  descriptor = make_descriptor(cryptonote::MAINNET);
  descriptor.metadata_reference = std::string("bad\0reference", 13);
  EXPECT_FALSE(cryptonote::assets::validate_issuance_descriptor(descriptor, &error));
}

TEST(asset_types, enforces_nft_collection_and_edition_rules)
{
  std::string error;
  auto nft = make_descriptor(cryptonote::TESTNET);
  nft.type = cryptonote::assets::asset_class::non_fungible;
  nft.atomic_supply = 1;
  nft.display_decimals = 0;
  EXPECT_TRUE(cryptonote::assets::validate_issuance_descriptor(nft, &error));

  nft.atomic_supply = 2;
  EXPECT_FALSE(cryptonote::assets::validate_issuance_descriptor(nft, &error));
  nft.atomic_supply = 1;
  nft.display_decimals = 1;
  EXPECT_FALSE(cryptonote::assets::validate_issuance_descriptor(nft, &error));

  auto collection = make_descriptor(cryptonote::TESTNET);
  collection.type = cryptonote::assets::asset_class::collection;
  collection.atomic_supply = 1;
  collection.display_decimals = 0;
  EXPECT_TRUE(cryptonote::assets::validate_issuance_descriptor(collection, &error));
  collection.collection_id.data[0] = 1;
  EXPECT_FALSE(cryptonote::assets::validate_issuance_descriptor(collection, &error));

  auto edition = make_descriptor(cryptonote::TESTNET);
  edition.type = cryptonote::assets::asset_class::edition;
  edition.display_decimals = 0;
  std::memset(edition.collection_id.data, 0x33, sizeof(edition.collection_id.data));
  EXPECT_TRUE(cryptonote::assets::validate_issuance_descriptor(edition, &error));
  edition.display_decimals = 1;
  EXPECT_FALSE(cryptonote::assets::validate_issuance_descriptor(edition, &error));

  auto fungible = make_descriptor(cryptonote::TESTNET);
  fungible.collection_id.data[0] = 1;
  EXPECT_FALSE(cryptonote::assets::validate_issuance_descriptor(fungible, &error));
}

TEST(asset_types, verifies_issuer_and_collection_authorizations)
{
  crypto::public_key issuer_public{};
  crypto::secret_key issuer_secret{};
  crypto::generate_keys(issuer_public, issuer_secret);

  auto collection = make_descriptor(cryptonote::TESTNET);
  collection.type = cryptonote::assets::asset_class::collection;
  collection.atomic_supply = 1;
  collection.display_decimals = 0;
  collection.issuer_key = issuer_public;
  crypto::hash collection_id{};
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(collection, collection_id));

  crypto::hash issuance_message{};
  ASSERT_TRUE(cryptonote::assets::derive_issuance_authorization_hash(collection, issuance_message));
  crypto::signature issuance_signature{};
  crypto::generate_signature(issuance_message, issuer_public, issuer_secret, issuance_signature);
  EXPECT_TRUE(cryptonote::assets::verify_issuance_authorization(collection, issuance_signature));
  collection.issuance_nonce.data[0] ^= 1;
  EXPECT_FALSE(cryptonote::assets::verify_issuance_authorization(collection, issuance_signature));
  collection.issuance_nonce.data[0] ^= 1;

  auto nft = make_descriptor(cryptonote::TESTNET);
  nft.type = cryptonote::assets::asset_class::non_fungible;
  nft.atomic_supply = 1;
  nft.display_decimals = 0;
  nft.collection_id = collection_id;
  crypto::hash nft_id{};
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(nft, nft_id));

  crypto::hash membership_message{};
  ASSERT_TRUE(cryptonote::assets::derive_collection_membership_hash(collection_id, nft_id, membership_message));
  crypto::signature membership_signature{};
  crypto::generate_signature(membership_message, issuer_public, issuer_secret, membership_signature);
  EXPECT_TRUE(cryptonote::assets::verify_collection_membership(
    collection_id, nft_id, issuer_public, membership_signature));

  nft_id.data[0] ^= 1;
  EXPECT_FALSE(cryptonote::assets::verify_collection_membership(
    collection_id, nft_id, issuer_public, membership_signature));
  EXPECT_FALSE(cryptonote::assets::derive_collection_membership_hash(
    crypto::null_hash, nft_id, membership_message));
}

TEST(asset_types, registry_authenticates_collection_membership_and_reorgs)
{
  crypto::public_key collection_public{};
  crypto::secret_key collection_secret{};
  crypto::generate_keys(collection_public, collection_secret);
  crypto::public_key member_public{};
  crypto::secret_key member_secret{};
  crypto::generate_keys(member_public, member_secret);

  cryptonote::assets::asset_registry registry;
  auto collection = make_descriptor(cryptonote::TESTNET);
  collection.type = cryptonote::assets::asset_class::collection;
  collection.atomic_supply = 1;
  collection.display_decimals = 0;
  collection.issuer_key = collection_public;
  const auto collection_auth = authorize(collection, collection_public, collection_secret);
  crypto::hash collection_id{};
  ASSERT_TRUE(registry.apply_issuance(collection, collection_auth, boost::none, 10, collection_id));
  EXPECT_TRUE(registry.contains(collection_id));

  auto nft = make_descriptor(cryptonote::TESTNET);
  nft.type = cryptonote::assets::asset_class::non_fungible;
  nft.atomic_supply = 1;
  nft.display_decimals = 0;
  nft.collection_id = collection_id;
  nft.issuer_key = member_public;
  crypto::hash nft_id{};
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(nft, nft_id));
  const auto nft_auth = authorize(nft, member_public, member_secret);
  crypto::hash membership_message{};
  ASSERT_TRUE(cryptonote::assets::derive_collection_membership_hash(collection_id, nft_id, membership_message));
  crypto::signature membership_signature{};
  crypto::generate_signature(membership_message, collection_public, collection_secret, membership_signature);

  crypto::hash registered_nft{};
  EXPECT_FALSE(registry.apply_issuance(nft, nft_auth, membership_signature, 9, registered_nft));
  ASSERT_TRUE(registry.apply_issuance(nft, nft_auth, membership_signature, 12, registered_nft));
  EXPECT_EQ(nft_id, registered_nft);
  EXPECT_EQ(2u, registry.size());
  EXPECT_EQ(2u, registry.known_assets().size());
  ASSERT_NE(nullptr, registry.find(nft_id));
  EXPECT_EQ(12u, registry.find(nft_id)->issuance_height);

  crypto::hash duplicate{};
  EXPECT_FALSE(registry.apply_issuance(nft, nft_auth, membership_signature, 13, duplicate));

  registry.detach(12);
  EXPECT_TRUE(registry.contains(collection_id));
  EXPECT_FALSE(registry.contains(nft_id));
  EXPECT_EQ(1u, registry.size());
  EXPECT_TRUE(registry.apply_issuance(nft, nft_auth, membership_signature, 14, registered_nft));
  registry.detach(10);
  EXPECT_EQ(0u, registry.size());
}

TEST(asset_types, registry_snapshot_round_trip_preserves_authenticated_state)
{
  crypto::public_key collection_public{};
  crypto::secret_key collection_secret{};
  crypto::generate_keys(collection_public, collection_secret);
  crypto::public_key member_public{};
  crypto::secret_key member_secret{};
  crypto::generate_keys(member_public, member_secret);

  cryptonote::assets::asset_registry original;
  auto collection = make_descriptor(cryptonote::TESTNET);
  collection.type = cryptonote::assets::asset_class::collection;
  collection.atomic_supply = 1;
  collection.display_decimals = 0;
  collection.issuer_key = collection_public;
  crypto::hash collection_id{};
  ASSERT_TRUE(original.apply_issuance(
    collection, authorize(collection, collection_public, collection_secret), boost::none, 7, collection_id));

  auto member = make_descriptor(cryptonote::TESTNET);
  member.type = cryptonote::assets::asset_class::non_fungible;
  member.atomic_supply = 1;
  member.display_decimals = 0;
  member.issuer_key = member_public;
  member.collection_id = collection_id;
  crypto::hash member_id{};
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(member, member_id));
  crypto::hash membership_message{};
  ASSERT_TRUE(cryptonote::assets::derive_collection_membership_hash(
    collection_id, member_id, membership_message));
  crypto::signature membership_signature{};
  crypto::generate_signature(membership_message, collection_public, collection_secret, membership_signature);
  ASSERT_TRUE(original.apply_issuance(
    member, authorize(member, member_public, member_secret), membership_signature, 7, member_id));

  std::vector<uint8_t> snapshot;
  ASSERT_TRUE(original.encode_snapshot(cryptonote::TESTNET, snapshot));
  cryptonote::assets::asset_registry restored;
  ASSERT_TRUE(restored.decode_snapshot(snapshot, cryptonote::TESTNET));
  EXPECT_EQ(original.known_assets(), restored.known_assets());
  ASSERT_NE(nullptr, restored.find(collection_id));
  ASSERT_NE(nullptr, restored.find(member_id));
  EXPECT_EQ(7u, restored.find(member_id)->issuance_height);
  EXPECT_TRUE(restored.find(member_id)->collection_signature);

  std::vector<uint8_t> second;
  ASSERT_TRUE(restored.encode_snapshot(cryptonote::TESTNET, second));
  EXPECT_EQ(snapshot, second);
}

TEST(asset_types, registry_snapshot_rejects_corruption_and_preserves_existing_state)
{
  crypto::public_key issuer_public{};
  crypto::secret_key issuer_secret{};
  crypto::generate_keys(issuer_public, issuer_secret);
  auto descriptor = make_descriptor(cryptonote::STAGENET);
  descriptor.issuer_key = issuer_public;

  cryptonote::assets::asset_registry registry;
  crypto::hash asset_id{};
  ASSERT_TRUE(registry.apply_issuance(
    descriptor, authorize(descriptor, issuer_public, issuer_secret), boost::none, 3, asset_id));
  std::vector<uint8_t> snapshot;
  ASSERT_TRUE(registry.encode_snapshot(cryptonote::STAGENET, snapshot));

  auto corrupted = snapshot;
  corrupted.back() ^= 1;
  EXPECT_FALSE(registry.decode_snapshot(corrupted, cryptonote::STAGENET));
  EXPECT_TRUE(registry.contains(asset_id));
  EXPECT_EQ(1u, registry.size());
  EXPECT_FALSE(registry.decode_snapshot(snapshot, cryptonote::TESTNET));
  EXPECT_TRUE(registry.contains(asset_id));

  auto trailing = snapshot;
  trailing.push_back(0);
  EXPECT_FALSE(registry.decode_snapshot(trailing, cryptonote::STAGENET));
  EXPECT_TRUE(registry.contains(asset_id));
}

TEST(asset_types, block_issuance_application_is_atomic_and_ordered)
{
  crypto::public_key collection_public{};
  crypto::secret_key collection_secret{};
  crypto::generate_keys(collection_public, collection_secret);
  crypto::public_key member_public{};
  crypto::secret_key member_secret{};
  crypto::generate_keys(member_public, member_secret);

  cryptonote::assets::issuance_payload collection_payload;
  collection_payload.descriptor = make_descriptor(cryptonote::TESTNET);
  collection_payload.descriptor.type = cryptonote::assets::asset_class::collection;
  collection_payload.descriptor.atomic_supply = 1;
  collection_payload.descriptor.display_decimals = 0;
  collection_payload.descriptor.issuer_key = collection_public;
  collection_payload.issuer_signature = authorize(
    collection_payload.descriptor, collection_public, collection_secret);
  crypto::hash collection_id{};
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(collection_payload.descriptor, collection_id));

  cryptonote::assets::issuance_payload member_payload;
  member_payload.descriptor = make_descriptor(cryptonote::TESTNET);
  member_payload.descriptor.type = cryptonote::assets::asset_class::non_fungible;
  member_payload.descriptor.atomic_supply = 1;
  member_payload.descriptor.display_decimals = 0;
  member_payload.descriptor.issuer_key = member_public;
  member_payload.descriptor.collection_id = collection_id;
  member_payload.issuer_signature = authorize(
    member_payload.descriptor, member_public, member_secret);
  crypto::hash member_id{};
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(member_payload.descriptor, member_id));
  crypto::hash membership_message{};
  ASSERT_TRUE(cryptonote::assets::derive_collection_membership_hash(
    collection_id, member_id, membership_message));
  crypto::signature membership_signature{};
  crypto::generate_signature(
    membership_message, collection_public, collection_secret, membership_signature);
  member_payload.collection_signature = membership_signature;

  cryptonote::assets::asset_registry registry;
  std::vector<crypto::hash> ids;
  ASSERT_TRUE(registry.apply_block_issuances(
    {collection_payload, member_payload}, 20, ids));
  ASSERT_EQ(2u, ids.size());
  EXPECT_EQ(collection_id, ids[0]);
  EXPECT_EQ(member_id, ids[1]);
  EXPECT_EQ(2u, registry.size());

  registry.detach(20);
  EXPECT_EQ(0u, registry.size());
  EXPECT_FALSE(registry.apply_block_issuances(
    {member_payload, collection_payload}, 21, ids));
  EXPECT_EQ(0u, registry.size());

  auto invalid_member = member_payload;
  invalid_member.issuer_signature.c.data[0] ^= 1;
  EXPECT_FALSE(registry.apply_block_issuances(
    {collection_payload, invalid_member}, 22, ids));
  EXPECT_EQ(0u, registry.size());
}

TEST(asset_types, registry_snapshot_commitment_is_deterministic_and_state_sensitive)
{
  crypto::public_key issuer_public{};
  crypto::secret_key issuer_secret{};
  crypto::generate_keys(issuer_public, issuer_secret);
  auto descriptor = make_descriptor(cryptonote::STAGENET);
  descriptor.issuer_key = issuer_public;

  cryptonote::assets::asset_registry first;
  cryptonote::assets::asset_registry second;
  crypto::hash asset_id{};
  const crypto::signature signature = authorize(descriptor, issuer_public, issuer_secret);
  ASSERT_TRUE(first.apply_issuance(descriptor, signature, boost::none, 5, asset_id));
  ASSERT_TRUE(second.apply_issuance(descriptor, signature, boost::none, 5, asset_id));

  crypto::hash first_hash{};
  crypto::hash second_hash{};
  ASSERT_TRUE(first.derive_snapshot_hash(cryptonote::STAGENET, first_hash));
  ASSERT_TRUE(second.derive_snapshot_hash(cryptonote::STAGENET, second_hash));
  EXPECT_EQ(first_hash, second_hash);

  second.detach(5);
  ASSERT_TRUE(second.derive_snapshot_hash(cryptonote::STAGENET, second_hash));
  EXPECT_NE(first_hash, second_hash);
  EXPECT_FALSE(first.derive_snapshot_hash(cryptonote::TESTNET, second_hash));
}

TEST(asset_types, registry_rejects_fake_or_missing_collection_authority)
{
  crypto::public_key issuer_public{};
  crypto::secret_key issuer_secret{};
  crypto::generate_keys(issuer_public, issuer_secret);
  crypto::public_key attacker_public{};
  crypto::secret_key attacker_secret{};
  crypto::generate_keys(attacker_public, attacker_secret);

  cryptonote::assets::asset_registry registry;
  auto collection = make_descriptor(cryptonote::STAGENET);
  collection.type = cryptonote::assets::asset_class::collection;
  collection.atomic_supply = 1;
  collection.display_decimals = 0;
  collection.issuer_key = issuer_public;
  crypto::hash collection_id{};
  ASSERT_TRUE(registry.apply_issuance(
    collection, authorize(collection, issuer_public, issuer_secret), boost::none, 1, collection_id));

  auto nft = make_descriptor(cryptonote::STAGENET);
  nft.type = cryptonote::assets::asset_class::non_fungible;
  nft.atomic_supply = 1;
  nft.display_decimals = 0;
  nft.collection_id = collection_id;
  nft.issuer_key = attacker_public;
  const auto nft_auth = authorize(nft, attacker_public, attacker_secret);
  crypto::hash nft_id{};
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(nft, nft_id));
  crypto::hash ignored{};
  EXPECT_FALSE(registry.apply_issuance(nft, nft_auth, boost::none, 2, ignored));

  crypto::hash membership_message{};
  ASSERT_TRUE(cryptonote::assets::derive_collection_membership_hash(collection_id, nft_id, membership_message));
  crypto::signature fake_membership{};
  crypto::generate_signature(membership_message, attacker_public, attacker_secret, fake_membership);
  EXPECT_FALSE(registry.apply_issuance(nft, nft_auth, fake_membership, 2, ignored));

  nft.collection_id.data[0] ^= 1;
  EXPECT_FALSE(registry.apply_issuance(
    nft, authorize(nft, attacker_public, attacker_secret), boost::none, 2, ignored));
}

TEST(asset_types, validates_fixed_supply_issuance_and_xmz_fee)
{
  const auto descriptor = make_descriptor(cryptonote::TESTNET);
  crypto::hash asset_id{};
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(descriptor, asset_id));

  cryptonote::assets::transparent_balance_statement statement;
  statement.xmz_inputs = 5000;
  statement.xmz_outputs = 4500;
  statement.xmz_fee = 500;
  statement.issuance = descriptor;
  statement.asset_outputs.push_back({asset_id, descriptor.atomic_supply});
  EXPECT_TRUE(cryptonote::assets::validate_transparent_balance_statement(statement, {}));

  statement.asset_outputs[0].amount++;
  EXPECT_FALSE(cryptonote::assets::validate_transparent_balance_statement(statement, {}));
}

TEST(asset_types, validates_transfer_and_explicit_burn)
{
  const auto descriptor = make_descriptor(cryptonote::TESTNET);
  crypto::hash asset_id{};
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(descriptor, asset_id));
  const std::set<crypto::hash> known{asset_id};

  cryptonote::assets::transparent_balance_statement statement;
  statement.xmz_inputs = 1000;
  statement.xmz_outputs = 900;
  statement.xmz_fee = 100;
  statement.asset_inputs.push_back({asset_id, 100});
  statement.asset_outputs.push_back({asset_id, 60});
  statement.asset_burns.push_back({asset_id, 40});
  EXPECT_TRUE(cryptonote::assets::validate_transparent_balance_statement(statement, known));

  statement.asset_burns[0].amount = 39;
  EXPECT_FALSE(cryptonote::assets::validate_transparent_balance_statement(statement, known));
}

TEST(asset_types, rejects_cross_asset_conversion_and_unknown_assets)
{
  auto first_descriptor = make_descriptor(cryptonote::TESTNET);
  auto second_descriptor = first_descriptor;
  second_descriptor.issuance_nonce.data[0] ^= 1;
  crypto::hash first{};
  crypto::hash second{};
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(first_descriptor, first));
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(second_descriptor, second));

  cryptonote::assets::transparent_balance_statement statement;
  statement.asset_inputs.push_back({first, 100});
  statement.asset_outputs.push_back({second, 100});
  EXPECT_FALSE(cryptonote::assets::validate_transparent_balance_statement(statement, {first, second}));

  statement.asset_outputs[0].asset_id = first;
  EXPECT_FALSE(cryptonote::assets::validate_transparent_balance_statement(statement, {}));
}

TEST(asset_types, rejects_duplicate_issuance_and_native_inflation)
{
  const auto descriptor = make_descriptor(cryptonote::STAGENET);
  crypto::hash asset_id{};
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(descriptor, asset_id));

  cryptonote::assets::transparent_balance_statement statement;
  statement.xmz_inputs = 100;
  statement.xmz_outputs = 100;
  statement.issuance = descriptor;
  statement.asset_outputs.push_back({asset_id, descriptor.atomic_supply});
  EXPECT_FALSE(cryptonote::assets::validate_transparent_balance_statement(statement, {asset_id}));

  statement.xmz_outputs = 101;
  EXPECT_FALSE(cryptonote::assets::validate_transparent_balance_statement(statement, {}));
}

TEST(asset_types, rejects_noncanonical_and_overflowing_amounts)
{
  const auto descriptor = make_descriptor(cryptonote::MAINNET);
  crypto::hash asset_id{};
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(descriptor, asset_id));
  const std::set<crypto::hash> known{asset_id};

  cryptonote::assets::transparent_balance_statement statement;
  statement.asset_inputs.push_back({asset_id, std::numeric_limits<uint64_t>::max()});
  statement.asset_inputs.push_back({asset_id, 1});
  statement.asset_outputs.push_back({asset_id, std::numeric_limits<uint64_t>::max()});
  EXPECT_FALSE(cryptonote::assets::validate_transparent_balance_statement(statement, known));

  statement = {};
  statement.asset_inputs.push_back({crypto::null_hash, 1});
  statement.asset_outputs.push_back({crypto::null_hash, 1});
  EXPECT_FALSE(cryptonote::assets::validate_transparent_balance_statement(statement, known));

  statement = {};
  statement.asset_inputs.push_back({asset_id, 0});
  statement.asset_outputs.push_back({asset_id, 0});
  EXPECT_FALSE(cryptonote::assets::validate_transparent_balance_statement(statement, known));

  statement = {};
  EXPECT_FALSE(cryptonote::assets::validate_transparent_balance_statement(statement, known));
}

TEST(asset_types, rejects_sum_overflow_and_unrelated_unknown_assets_during_issuance)
{
  const auto descriptor = make_descriptor(cryptonote::TESTNET);
  auto unrelated_descriptor = descriptor;
  unrelated_descriptor.issuance_nonce.data[0] ^= 1;
  crypto::hash issued_id{};
  crypto::hash unknown_id{};
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(descriptor, issued_id));
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(unrelated_descriptor, unknown_id));

  cryptonote::assets::transparent_balance_statement statement;
  statement.xmz_inputs = std::numeric_limits<uint64_t>::max();
  statement.xmz_outputs = std::numeric_limits<uint64_t>::max();
  statement.xmz_fee = 1;
  statement.issuance = descriptor;
  statement.asset_outputs.push_back({issued_id, descriptor.atomic_supply});
  EXPECT_FALSE(cryptonote::assets::validate_transparent_balance_statement(statement, {}));

  statement.xmz_inputs = 0;
  statement.xmz_outputs = 0;
  statement.xmz_fee = 0;
  statement.asset_inputs.push_back({unknown_id, 1});
  statement.asset_outputs.push_back({unknown_id, 1});
  EXPECT_FALSE(cryptonote::assets::validate_transparent_balance_statement(statement, {}));

  statement.asset_inputs.clear();
  statement.asset_outputs.clear();
  statement.issuance = boost::none;
  statement.asset_inputs.push_back({issued_id, std::numeric_limits<uint64_t>::max()});
  statement.asset_outputs.push_back({issued_id, std::numeric_limits<uint64_t>::max()});
  statement.asset_burns.push_back({issued_id, 1});
  EXPECT_FALSE(cryptonote::assets::validate_transparent_balance_statement(statement, {issued_id}));
}
