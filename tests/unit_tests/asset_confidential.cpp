#include "gtest/gtest.h"

#include "cryptonote_basic/asset_confidential.h"
#include "ringct/bulletproofs_plus.h"
#include "ringct/rctOps.h"

namespace
{
  crypto::hash asset_id(unsigned char value)
  {
    crypto::hash id{};
    id.data[0] = value;
    return id;
  }

  cryptonote::assets::confidential_asset_balance make_balance(
    const crypto::hash& id, uint64_t input_amount,
    const std::vector<uint64_t>& outputs, const std::vector<uint64_t>& burns)
  {
    rct::keyV masks = rct::skvGen(outputs.size() + burns.size());
    rct::key input_mask = rct::zero();
    for (const rct::key& mask : masks)
      sc_add(input_mask.bytes, input_mask.bytes, mask.bytes);
    cryptonote::assets::confidential_asset_balance balance;
    balance.asset_id = id;
    balance.pseudo_inputs.push_back({id, rct::commit(input_amount, input_mask)});
    size_t index = 0;
    for (const uint64_t amount : outputs)
      balance.outputs.push_back(rct::commit(amount, masks[index++]));
    for (const uint64_t amount : burns)
      balance.burns.push_back(rct::commit(amount, masks[index++]));
    std::vector<uint64_t> amounts = outputs;
    amounts.insert(amounts.end(), burns.begin(), burns.end());
    balance.range_proofs.push_back(rct::bulletproof_plus_PROVE(amounts, masks));
    return balance;
  }
}

TEST(asset_confidential, verifies_private_transfer_and_explicit_burn)
{
  const crypto::hash id = asset_id(1);
  const auto balance = make_balance(id, 10, {7}, {3});
  std::string error;
  ASSERT_TRUE(cryptonote::assets::verify_confidential_asset_balance(balance, &error)) << error;
  ASSERT_TRUE(cryptonote::assets::verify_confidential_asset_transaction({balance}, {id}, boost::none, &error)) << error;
}

TEST(asset_confidential, rejects_inflation_and_commitment_substitution)
{
  const crypto::hash id = asset_id(2);
  std::string error;
  auto inflated = make_balance(id, 10, {11}, {});
  EXPECT_FALSE(cryptonote::assets::verify_confidential_asset_balance(inflated, &error));
  auto substituted = make_balance(id, 10, {10}, {});
  substituted.outputs.front() = rct::commit(10, rct::skGen());
  EXPECT_FALSE(cryptonote::assets::verify_confidential_asset_balance(substituted, &error));
  auto malformed = make_balance(id, 10, {10}, {});
  malformed.range_proofs.front().A.bytes[0] ^= 1;
  EXPECT_FALSE(cryptonote::assets::verify_confidential_asset_balance(malformed, &error));
}

TEST(asset_confidential, rejects_cross_asset_and_duplicate_balance_domains)
{
  const crypto::hash first = asset_id(3);
  const crypto::hash second = asset_id(4);
  std::string error;
  auto crossed = make_balance(first, 9, {9}, {});
  crossed.pseudo_inputs.front().source_asset_id = second;
  EXPECT_FALSE(cryptonote::assets::verify_confidential_asset_balance(crossed, &error));
  const auto valid = make_balance(first, 9, {9}, {});
  EXPECT_FALSE(cryptonote::assets::verify_confidential_asset_transaction({valid, valid}, {first}, boost::none, &error));
  EXPECT_FALSE(cryptonote::assets::verify_confidential_asset_transaction({valid}, {second}, boost::none, &error));
}

TEST(asset_confidential, validates_fixed_supply_issuance_commitment)
{
  crypto::public_key issuer{};
  crypto::secret_key secret{};
  crypto::generate_keys(issuer, secret);
  cryptonote::assets::issuance_descriptor descriptor;
  descriptor.network = cryptonote::TESTNET;
  descriptor.issuer_key = issuer;
  descriptor.atomic_supply = 10;
  descriptor.issuance_nonce.data[0] = 9;
  crypto::hash id{};
  ASSERT_TRUE(cryptonote::assets::derive_asset_id(descriptor, id));
  cryptonote::assets::confidential_asset_balance balance;
  balance.asset_id = id;
  balance.pseudo_inputs.push_back({id, rct::commit(10, rct::zero())});
  balance.outputs.push_back(rct::commit(10, rct::zero()));
  balance.range_proofs.push_back(rct::bulletproof_plus_PROVE(10, rct::zero()));
  std::string error;
  ASSERT_TRUE(cryptonote::assets::verify_confidential_asset_transaction({balance}, {}, descriptor, &error)) << error;
  balance.pseudo_inputs.front().commitment = rct::commit(11, rct::zero());
  EXPECT_FALSE(cryptonote::assets::verify_confidential_asset_transaction({balance}, {}, descriptor, &error));
}
