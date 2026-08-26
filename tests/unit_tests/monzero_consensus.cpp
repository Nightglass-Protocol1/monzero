#include "gtest/gtest.h"

#include <array>
#include <cstdint>
#include <string>

#include <boost/uuid/uuid_io.hpp>

#include "cryptonote_basic/cryptonote_format_utils.h"
#include "cryptonote_config.h"
#include "cryptonote_core/cryptonote_tx_utils.h"
#include "hardforks/hardforks.h"
#include "string_tools.h"

namespace
{
  struct network_vector
  {
    cryptonote::network_type type;
    const char* uuid;
    uint64_t standard_prefix;
    uint64_t integrated_prefix;
    uint64_t subaddress_prefix;
    uint16_t p2p_port;
    uint16_t rpc_port;
    uint16_t zmq_port;
    uint32_t genesis_nonce;
    const char* genesis_hash;
  };

  const std::array<network_vector, 3> networks{{
    {cryptonote::MAINNET, "94834264-d0b2-41dd-b0f2-0ada675c7710", 86, 87, 88,
      6174, 6175, 6176, 2271206363, "84f9ebdac8924806f037482ec16fd59b271e954d3e00363dd6c7e4ce9dd659e4"},
    {cryptonote::TESTNET, "adc2a271-5539-43d9-b3c2-7aadaf6b938c", 111, 112, 113,
      16174, 16175, 16176, 818137481, "d89bd4d42729aa9f68fd8d6bc86c3b12686a3fcd5ec83a392844efc067d5c040"},
    {cryptonote::STAGENET, "b1dcac5a-9d11-4653-8122-e67eec8b59ac", 131, 132, 133,
      26174, 26175, 26176, 818137482, "0d917308bb74557f9ccefd1360b9875a39df00363474fe4da9ae8e5f989170b7"}
  }};
}

TEST(monzero_consensus, monetary_policy)
{
  EXPECT_EQ(11, CRYPTONOTE_DISPLAY_DECIMAL_POINT);
  EXPECT_EQ(UINT64_C(100000000000), COIN);
  EXPECT_EQ(UINT64_C(10000000000000000000), MONEY_SUPPLY);
  EXPECT_EQ(20, EMISSION_SPEED_FACTOR_PER_MINUTE);
  EXPECT_EQ(UINT64_C(163000000000), FINAL_SUBSIDY_PER_MINUTE);
  EXPECT_EQ(120, DIFFICULTY_TARGET_V1);
  EXPECT_EQ(120, DIFFICULTY_TARGET_V2);
  EXPECT_EQ(60, CRYPTONOTE_MINED_MONEY_UNLOCK_WINDOW);
  EXPECT_EQ(10, CRYPTONOTE_DEFAULT_TX_SPENDABLE_AGE);
  EXPECT_EQ(2, CURRENT_TRANSACTION_VERSION);
}

TEST(monzero_consensus, protected_network_vectors)
{
  for (const network_vector& expected : networks)
  {
    const cryptonote::config_t& actual = cryptonote::get_config(expected.type);
    EXPECT_EQ(expected.uuid, boost::uuids::to_string(actual.NETWORK_ID));
    EXPECT_EQ(expected.standard_prefix, actual.CRYPTONOTE_PUBLIC_ADDRESS_BASE58_PREFIX);
    EXPECT_EQ(expected.integrated_prefix, actual.CRYPTONOTE_PUBLIC_INTEGRATED_ADDRESS_BASE58_PREFIX);
    EXPECT_EQ(expected.subaddress_prefix, actual.CRYPTONOTE_PUBLIC_SUBADDRESS_BASE58_PREFIX);
    EXPECT_EQ(expected.p2p_port, actual.P2P_DEFAULT_PORT);
    EXPECT_EQ(expected.rpc_port, actual.RPC_DEFAULT_PORT);
    EXPECT_EQ(expected.zmq_port, actual.ZMQ_RPC_DEFAULT_PORT);
    EXPECT_EQ(expected.genesis_nonce, actual.GENESIS_NONCE);

    cryptonote::block genesis;
    ASSERT_TRUE(cryptonote::generate_genesis_block(genesis, actual.GENESIS_TX, actual.GENESIS_NONCE));
    EXPECT_EQ(expected.genesis_hash,
      epee::string_tools::pod_to_hex(cryptonote::get_block_hash(genesis)));
  }
}

TEST(monzero_consensus, protected_hard_fork_schedule)
{
  const std::array<std::pair<const hardfork_t*, size_t>, 3> schedules{{
    {mainnet_hard_forks, num_mainnet_hard_forks},
    {testnet_hard_forks, num_testnet_hard_forks},
    {stagenet_hard_forks, num_stagenet_hard_forks}
  }};

  for (const auto& schedule : schedules)
  {
    ASSERT_EQ(16, schedule.second);
    for (size_t index = 0; index < schedule.second; ++index)
    {
      const uint8_t expected_version = static_cast<uint8_t>(index + 1);
      EXPECT_EQ(expected_version, schedule.first[index].version);
      EXPECT_EQ(index + 1, schedule.first[index].height);
      EXPECT_EQ(0, schedule.first[index].threshold);
    }
  }
}
