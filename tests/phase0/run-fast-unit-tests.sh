#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
build_dir="${1:-${project_root}/build}"
unit_tests="${build_dir}/tests/unit_tests/unit_tests"

if [[ ! -x "${unit_tests}" ]]; then
  echo "Unit-test binary not found: ${unit_tests}" >&2
  echo "Build it with: cmake --build ${build_dir} --target unit_tests -j2" >&2
  exit 1
fi

# Keep external DNS behavior reproducible across developer and CI resolvers.
export DNS_PUBLIC="${DNS_PUBLIC:-tcp://1.1.1.1}"

# This pruning-boundary concurrency scenario creates about 9,600 blocks and is
# kept in the separate stress gate. It is not a fast unit test.
exec "${unit_tests}" \
  --gtest_color=no \
  --gtest_filter=-cryptonote_protocol_handler.race_condition
