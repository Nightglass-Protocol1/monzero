#include "asset_types.h"

#include <algorithm>
#include <cstring>
#include <limits>
#include <map>

#include "crypto/hash.h"

namespace cryptonote
{
namespace assets
{
  namespace
  {
    constexpr char DOMAIN[] = "MonzeroAssetIssuanceV2";
    constexpr char ISSUANCE_AUTHORIZATION_DOMAIN[] = "MonzeroAssetIssuanceAuthorizationV1";
    constexpr char COLLECTION_MEMBERSHIP_DOMAIN[] = "MonzeroCollectionMembershipV1";

    bool fail(std::string* error, const char* message)
    {
      if (error)
        *error = message;
      return false;
    }

    template<typename T>
    void append_pod(std::vector<uint8_t>& target, const T& value)
    {
      const auto* begin = reinterpret_cast<const uint8_t*>(&value);
      target.insert(target.end(), begin, begin + sizeof(value));
    }

    void append_u16_le(std::vector<uint8_t>& target, uint16_t value)
    {
      target.push_back(static_cast<uint8_t>(value));
      target.push_back(static_cast<uint8_t>(value >> 8));
    }

    void append_u64_le(std::vector<uint8_t>& target, uint64_t value)
    {
      for (unsigned shift = 0; shift < 64; shift += 8)
        target.push_back(static_cast<uint8_t>(value >> shift));
    }
  }

  bool validate_issuance_descriptor(const issuance_descriptor& descriptor, std::string* error)
  {
    if (descriptor.version != ISSUANCE_DESCRIPTOR_VERSION)
      return fail(error, "unsupported issuance descriptor version");
    if (descriptor.network != MAINNET && descriptor.network != TESTNET && descriptor.network != STAGENET)
      return fail(error, "issuance descriptor requires an explicit public network");
    if (descriptor.type != asset_class::fungible
        && descriptor.type != asset_class::non_fungible
        && descriptor.type != asset_class::collection
        && descriptor.type != asset_class::edition)
      return fail(error, "unsupported asset class");
    if (!crypto::check_key(descriptor.issuer_key))
      return fail(error, "invalid issuer public key");
    if (descriptor.atomic_supply == 0)
      return fail(error, "asset supply must be greater than zero");
    if (descriptor.display_decimals > MAX_DISPLAY_DECIMALS)
      return fail(error, "asset display precision exceeds XMZ precision");
    if ((descriptor.type == asset_class::non_fungible || descriptor.type == asset_class::collection)
        && (descriptor.atomic_supply != 1 || descriptor.display_decimals != 0))
      return fail(error, "NFT and collection supply must be exactly one indivisible unit");
    if (descriptor.type == asset_class::edition && descriptor.display_decimals != 0)
      return fail(error, "edition supply must be indivisible");
    if ((descriptor.type == asset_class::fungible || descriptor.type == asset_class::collection)
        && descriptor.collection_id != crypto::null_hash)
      return fail(error, "this asset class cannot reference a collection");
    if ((descriptor.type == asset_class::non_fungible || descriptor.type == asset_class::edition)
        && descriptor.metadata_hash == crypto::null_hash)
      return fail(error, "NFT and edition metadata must have a content hash");
    if (descriptor.metadata_reference.size() > MAX_METADATA_REFERENCE_BYTES)
      return fail(error, "metadata reference is too long");
    if (std::find(descriptor.metadata_reference.begin(), descriptor.metadata_reference.end(), '\0') != descriptor.metadata_reference.end())
      return fail(error, "metadata reference contains a NUL byte");
    return true;
  }

  bool encode_issuance_descriptor(const issuance_descriptor& descriptor, std::vector<uint8_t>& encoded, std::string* error)
  {
    if (!validate_issuance_descriptor(descriptor, error))
      return false;

    encoded.clear();
    encoded.reserve(sizeof(DOMAIN) - 1 + 1 + 16 + 1 + 32 + 32 + 8 + 1 + 32 + 32 + 2 + descriptor.metadata_reference.size());
    encoded.insert(encoded.end(), DOMAIN, DOMAIN + sizeof(DOMAIN) - 1);
    encoded.push_back(descriptor.version);
    const config_t& network = get_config(descriptor.network);
    append_pod(encoded, network.NETWORK_ID);
    encoded.push_back(static_cast<uint8_t>(descriptor.type));
    append_pod(encoded, descriptor.issuer_key);
    append_pod(encoded, descriptor.issuance_nonce);
    append_u64_le(encoded, descriptor.atomic_supply);
    encoded.push_back(descriptor.display_decimals);
    append_pod(encoded, descriptor.metadata_hash);
    append_pod(encoded, descriptor.collection_id);
    append_u16_le(encoded, static_cast<uint16_t>(descriptor.metadata_reference.size()));
    encoded.insert(encoded.end(), descriptor.metadata_reference.begin(), descriptor.metadata_reference.end());
    return true;
  }

  bool derive_asset_id(const issuance_descriptor& descriptor, crypto::hash& asset_id, std::string* error)
  {
    std::vector<uint8_t> encoded;
    if (!encode_issuance_descriptor(descriptor, encoded, error))
      return false;
    asset_id = crypto::cn_fast_hash(encoded.data(), encoded.size());
    return true;
  }

  bool derive_issuance_authorization_hash(const issuance_descriptor& descriptor, crypto::hash& message, std::string* error)
  {
    std::vector<uint8_t> encoded;
    if (!encode_issuance_descriptor(descriptor, encoded, error))
      return false;
    std::vector<uint8_t> authorization;
    authorization.reserve(sizeof(ISSUANCE_AUTHORIZATION_DOMAIN) - 1 + encoded.size());
    authorization.insert(authorization.end(), ISSUANCE_AUTHORIZATION_DOMAIN,
      ISSUANCE_AUTHORIZATION_DOMAIN + sizeof(ISSUANCE_AUTHORIZATION_DOMAIN) - 1);
    authorization.insert(authorization.end(), encoded.begin(), encoded.end());
    message = crypto::cn_fast_hash(authorization.data(), authorization.size());
    return true;
  }

  bool verify_issuance_authorization(const issuance_descriptor& descriptor, const crypto::signature& signature, std::string* error)
  {
    crypto::hash message{};
    if (!derive_issuance_authorization_hash(descriptor, message, error))
      return false;
    if (!crypto::check_signature(message, descriptor.issuer_key, signature))
      return fail(error, "invalid asset issuer authorization signature");
    return true;
  }

  bool derive_collection_membership_hash(const crypto::hash& collection_id, const crypto::hash& member_asset_id, crypto::hash& message, std::string* error)
  {
    if (collection_id == crypto::null_hash || member_asset_id == crypto::null_hash)
      return fail(error, "collection and member asset IDs must be non-zero");
    std::vector<uint8_t> encoded;
    encoded.reserve(sizeof(COLLECTION_MEMBERSHIP_DOMAIN) - 1 + sizeof(collection_id) + sizeof(member_asset_id));
    encoded.insert(encoded.end(), COLLECTION_MEMBERSHIP_DOMAIN,
      COLLECTION_MEMBERSHIP_DOMAIN + sizeof(COLLECTION_MEMBERSHIP_DOMAIN) - 1);
    append_pod(encoded, collection_id);
    append_pod(encoded, member_asset_id);
    message = crypto::cn_fast_hash(encoded.data(), encoded.size());
    return true;
  }

  bool verify_collection_membership(
    const crypto::hash& collection_id,
    const crypto::hash& member_asset_id,
    const crypto::public_key& collection_controller,
    const crypto::signature& signature,
    std::string* error)
  {
    if (!crypto::check_key(collection_controller))
      return fail(error, "invalid collection controller public key");
    crypto::hash message{};
    if (!derive_collection_membership_hash(collection_id, member_asset_id, message, error))
      return false;
    if (!crypto::check_signature(message, collection_controller, signature))
      return fail(error, "invalid collection membership signature");
    return true;
  }

  bool asset_registry::apply_issuance(
    const issuance_descriptor& descriptor,
    const crypto::signature& issuer_signature,
    const boost::optional<crypto::signature>& collection_signature,
    uint64_t height,
    crypto::hash& asset_id,
    std::string* error)
  {
    if (!derive_asset_id(descriptor, asset_id, error))
      return false;
    if (contains(asset_id))
      return fail(error, "asset ID is already registered");
    if (!verify_issuance_authorization(descriptor, issuer_signature, error))
      return false;

    const bool claims_collection = descriptor.collection_id != crypto::null_hash;
    if (claims_collection)
    {
      const asset_record* collection = find(descriptor.collection_id);
      if (!collection || collection->descriptor.type != asset_class::collection)
        return fail(error, "referenced collection is unknown or not a collection");
      if (collection->descriptor.network != descriptor.network)
        return fail(error, "collection and member must use the same network");
      if (collection->issuance_height > height)
        return fail(error, "collection membership cannot precede collection issuance");
      if (!collection_signature)
        return fail(error, "collection membership requires controller authorization");
      if (!verify_collection_membership(
            descriptor.collection_id,
            asset_id,
            collection->descriptor.issuer_key,
            *collection_signature,
            error))
        return false;
    }
    else if (collection_signature)
      return fail(error, "unexpected collection signature for an uncollected asset");

    records_.emplace(asset_id, asset_record{descriptor, height});
    return true;
  }

  void asset_registry::detach(uint64_t height)
  {
    for (auto it = records_.begin(); it != records_.end();)
    {
      if (it->second.issuance_height >= height)
        it = records_.erase(it);
      else
        ++it;
    }
  }

  bool asset_registry::contains(const crypto::hash& asset_id) const
  {
    return records_.count(asset_id) != 0;
  }

  const asset_record* asset_registry::find(const crypto::hash& asset_id) const
  {
    const auto found = records_.find(asset_id);
    return found == records_.end() ? nullptr : &found->second;
  }

  std::set<crypto::hash> asset_registry::known_assets() const
  {
    std::set<crypto::hash> result;
    for (const auto& record : records_)
      result.insert(record.first);
    return result;
  }

  bool validate_transparent_balance_statement(
    const transparent_balance_statement& statement,
    const std::set<crypto::hash>& known_assets,
    std::string* error)
  {
    if (statement.xmz_outputs > std::numeric_limits<uint64_t>::max() - statement.xmz_fee
        || statement.xmz_inputs != statement.xmz_outputs + statement.xmz_fee)
      return fail(error, "XMZ inputs must equal XMZ outputs plus the XMZ fee");

    using balances = std::map<crypto::hash, uint64_t>;
    balances inputs;
    balances outputs;
    balances burns;

    const auto aggregate = [error](const std::vector<transparent_amount>& entries, balances& totals) {
      for (const transparent_amount& entry : entries)
      {
        if (entry.asset_id == crypto::null_hash)
          return fail(error, "the zero asset ID is reserved and invalid");
        if (entry.amount == 0)
          return fail(error, "zero-valued asset entries are not canonical");
        uint64_t& total = totals[entry.asset_id];
        if (entry.amount > std::numeric_limits<uint64_t>::max() - total)
          return fail(error, "asset amount aggregation overflow");
        total += entry.amount;
      }
      return true;
    };

    if (!aggregate(statement.asset_inputs, inputs)
        || !aggregate(statement.asset_outputs, outputs)
        || !aggregate(statement.asset_burns, burns))
      return false;

    boost::optional<crypto::hash> issued_asset;
    if (statement.issuance)
    {
      crypto::hash asset_id{};
      if (!derive_asset_id(*statement.issuance, asset_id, error))
        return false;
      if (known_assets.count(asset_id) != 0)
        return fail(error, "asset ID is already issued");
      if (inputs.count(asset_id) != 0 || burns.count(asset_id) != 0)
        return fail(error, "newly issued supply cannot have inputs or burns");
      const auto issued_outputs = outputs.find(asset_id);
      if (issued_outputs == outputs.end() || issued_outputs->second != statement.issuance->atomic_supply)
        return fail(error, "issuance outputs must equal the complete fixed supply");
      issued_asset = asset_id;
    }

    std::set<crypto::hash> touched;
    for (const auto& entry : inputs) touched.insert(entry.first);
    for (const auto& entry : outputs) touched.insert(entry.first);
    for (const auto& entry : burns) touched.insert(entry.first);
    if (touched.empty())
      return fail(error, "asset statement contains no issuance, transfer, or burn");

    for (const crypto::hash& asset_id : touched)
    {
      if (issued_asset && asset_id == *issued_asset)
        continue;
      if (known_assets.count(asset_id) == 0)
        return fail(error, "statement references an unknown asset ID");

      const uint64_t input = inputs.count(asset_id) ? inputs[asset_id] : 0;
      const uint64_t output = outputs.count(asset_id) ? outputs[asset_id] : 0;
      const uint64_t burn = burns.count(asset_id) ? burns[asset_id] : 0;
      if (output > std::numeric_limits<uint64_t>::max() - burn || input != output + burn)
        return fail(error, "asset inputs must equal outputs plus explicit burns");
    }
    return true;
  }
}
}
