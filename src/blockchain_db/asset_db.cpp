#include "asset_db.h"

#include <algorithm>
#include <cstring>

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

  struct stored_issuance
  {
    crypto::hash id{};
    uint64_t height = 0;
    std::vector<uint8_t> payload;
  };
}

bool load_registry_from_db(const BlockchainDB& db, network_type expected_network,
  asset_registry& registry, std::string* error)
{
  std::vector<stored_issuance> records;
  if (!db.for_all_asset_records([&records](const crypto::hash& id, uint64_t height, const blobdata_ref& payload) {
        stored_issuance record;
        record.id = id;
        record.height = height;
        record.payload.assign(payload.begin(), payload.end());
        records.push_back(std::move(record));
        return true;
      }))
    return fail(error, "asset database enumeration was interrupted");

  std::sort(records.begin(), records.end(), [](const stored_issuance& left, const stored_issuance& right) {
    if (left.height != right.height)
      return left.height < right.height;
    return std::memcmp(&left.id, &right.id, sizeof(left.id)) < 0;
  });

  asset_registry candidate;
  for (const stored_issuance& stored : records)
  {
    issuance_payload payload;
    if (!decode_issuance_payload(stored.payload, payload, error))
      return false;
    if (payload.descriptor.network != expected_network)
      return fail(error, "stored asset belongs to a different network");
    crypto::hash derived{};
    if (!candidate.apply_issuance(payload, stored.height, derived, error))
      return false;
    if (derived != stored.id)
      return fail(error, "stored asset id does not match its authenticated payload");
  }
  registry = std::move(candidate);
  return true;
}

bool apply_block_extensions_to_db(BlockchainDB& db,
  const std::vector<transaction_extension>& extensions,
  const std::vector<crypto::hash>& carrier_prefix_hashes,
  network_type expected_network, uint64_t height,
  std::vector<crypto::hash>& asset_ids, std::string* error)
{
  asset_registry registry;
  if (!load_registry_from_db(db, expected_network, registry, error))
    return false;
  std::vector<crypto::hash> candidate_ids;
  if (!registry.apply_block_extensions(extensions, carrier_prefix_hashes,
        expected_network, height, candidate_ids, error))
    return false;

  std::vector<std::vector<uint8_t>> encoded;
  encoded.reserve(extensions.size());
  for (const transaction_extension& extension : extensions)
  {
    encoded.emplace_back();
    if (!encode_issuance_payload(extension.issuance, encoded.back(), error))
      return false;
  }
  for (size_t index = 0; index < encoded.size(); ++index)
  {
    const blobdata_ref bytes{reinterpret_cast<const char*>(encoded[index].data()), encoded[index].size()};
    db.add_asset_record(candidate_ids[index], height, bytes);
  }
  asset_ids = std::move(candidate_ids);
  return true;
}
}
}
