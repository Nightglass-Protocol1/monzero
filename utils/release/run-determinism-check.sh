#!/usr/bin/env bash
# Monzero Genesis pre15 same-host determinism check.
#
# IMPORTANT: this is NOT independent reproduction. Per
# docs/INDEPENDENT_REPRODUCTION.md: "Same-host candidate A/B builds are
# useful determinism tests but are not independent evidence and must never
# be identified as such." This script runs on the same machine that built
# the published release. It proves the build is repeatable, which is a
# necessary precondition for independent reproduction, but it is not a
# substitute for it. Real independent reproduction requires a separate
# person or organization, with no ties to this project, building on a
# machine they control -- see docs/INDEPENDENT_REPRODUCTION.md for the
# actual procedure and what to send back.
#
# This script:
#   1. Rebuilds core (Linux + Windows targets) from a clean worktree at the
#      pinned release commit, twice, inside the pinned podman build
#      environment (mirrors build-env/build-core.sh).
#   2. Packages both build runs and compares them to each other (mirrors
#      build-env/package-all.sh's existing A/B check).
#   3. Downloads the CURRENTLY LIVE published archives from monzero.org and
#      byte-compares them against this fresh rebuild using the repository's
#      own utils/release/compare-reproduced-packages.sh, producing a signed-
#      ready JSON attestation.
#
# Expect this to take several hours (the last same-host run took ~4-5).
# Requires podman and the monzero-build-env:jammy / :jammy-pkg images
# already built on this machine (see build-env/Containerfile*).
set -euo pipefail

RELEASE_LABEL=${1:-genesis-pre15}
RELEASE_COMMIT=85d922cb09a5731712f69f799a8bd8004ff00a35
P=$HOME/projects/Monzero-App
CORE=$P/core
WORK=$P/determinism-check-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$WORK"

echo "=== 1/4: fresh worktree at the release commit ==="
git -C "$CORE" worktree add --detach "$WORK/candidate" "$RELEASE_COMMIT"

echo "=== 2/4: build (this is the slow part) ==="
L="$WORK/logs"; mkdir -p "$L"
for target in x86_64-linux-gnu x86_64-w64-mingw32; do
  start=$(date +%s)
  podman run --rm --userns=keep-id \
    -v "$WORK/candidate":"$WORK/candidate" \
    -v "$CORE/.git":"$CORE/.git:ro" \
    -w "$WORK/candidate" monzero-build-env:jammy \
    bash -c "make depends target=$target -j\$(nproc)" > "$L/$target.log" 2>&1
  echo "$target exit=$? after $(( ($(date +%s)-start)/60 )) min"
done

echo "=== 3/4: package and compare against the reference archives ==="
mkdir -p "$WORK/reference"
for f in linux-x86_64.tar.gz windows-x64.zip windows-gui-x64.zip; do
  curl -sL --fail -o "$WORK/reference/monzero-$RELEASE_LABEL-$f" \
    "https://monzero.org/downloads/monzero-$RELEASE_LABEL-$f"
done
cd "$WORK/candidate"
bash utils/release/package-linux.sh build/x86_64-linux-gnu/release/bin "$WORK/reproduced-linux" "$RELEASE_LABEL"
bash utils/release/package-windows.sh build/x86_64-w64-mingw32/release/bin "$WORK/reproduced-windows" "$RELEASE_LABEL"

echo "=== 4/4: byte-for-byte comparison + attestation ==="
export MONZERO_REPRODUCER_ID="${MONZERO_REPRODUCER_ID:-SAME-HOST, NOT an independent reproducer -- see script header}"
export MONZERO_REPRODUCER_ENVIRONMENT="${MONZERO_REPRODUCER_ENVIRONMENT:-$(hostname), same machine and podman images that produced the published release}"
bash utils/release/compare-reproduced-packages.sh \
  "$WORK/reference/monzero-$RELEASE_LABEL-linux-x86_64.tar.gz" \
  "$WORK/reproduced-linux/monzero-$RELEASE_LABEL-linux-x86_64.tar.gz" \
  "$WORK/reference/monzero-$RELEASE_LABEL-windows-x64.zip" \
  "$WORK/reproduced-windows/monzero-$RELEASE_LABEL-windows-x64.zip" \
  "$WORK/determinism-check.json"

echo
echo "Wrote $WORK/determinism-check.json"
echo "This attests SAME-HOST repeatability. It is not signed with any"
echo "'Monzero key' -- no such key should ever be generated on this"
echo "machine (see docs/RELEASE_SIGNING.md). To countersign this file as"
echo "yourself for your own records:"
echo "  gpg --armor --detach-sign $WORK/determinism-check.json"
echo
echo "Worktree left at $WORK/candidate for inspection; remove with:"
echo "  git -C $CORE worktree remove --force $WORK/candidate"
