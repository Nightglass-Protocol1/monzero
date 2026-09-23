#!/usr/bin/env bash
# Assembles the Windows GUI archive the same way package-windows.sh assembles
# the CLI archive, adding the fields verify-windows-gui-package.sh checks.
# Run from a clean core tree at the release commit; the GUI build tree's
# monero/ checkout must be the same commit.
set -euo pipefail

[[ $# -eq 4 ]] || {
  echo "Usage: $0 <gui-source-root> <gui-build-bin-dir> <output-dir> <version>" >&2
  echo "Set BUILD_ENVIRONMENT_IMAGE_ID to the GUI build-environment image id." >&2
  exit 2
}
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
source_root=$(cd -- "$script_dir/../.." && pwd -P)
gui_root=$(realpath "$1")
build_bin=$(realpath "$2")
extras=$source_root/utils/release/windows
output_dir=$(realpath -m "$3")
version=$4
build_environment_image_id=${BUILD_ENVIRONMENT_IMAGE_ID:?set BUILD_ENVIRONMENT_IMAGE_ID}

[[ $version =~ ^[0-9A-Za-z][0-9A-Za-z._-]*$ ]] || { echo "Invalid version label" >&2; exit 2; }
grep -Fqx "Release label: $version" "$source_root/docs/RELEASE_NOTES.md" || {
  echo "RELEASE_NOTES.md does not match release label: $version" >&2; exit 1;
}
for tree in "$source_root" "$gui_root" "$gui_root/monero"; do
  [[ -z $(git -C "$tree" status --porcelain --untracked-files=normal) ]] || {
    echo "Refusing to package a dirty source tree: $tree" >&2; exit 1;
  }
done

core_commit=$(git -C "$source_root" rev-parse HEAD)
[[ $(git -C "$gui_root/monero" rev-parse HEAD) == "$core_commit" ]] || {
  echo "GUI build tree's core is not the packaged core commit" >&2; exit 1;
}
gui_commit=$(git -C "$gui_root" rev-parse HEAD)
core_version="0.18.5.1-${core_commit:0:9}"
source_epoch=${SOURCE_DATE_EPOCH:-$(git -C "$source_root" show -s --format=%ct "$core_commit")}

binaries=(monzero-wallet-gui.exe monzerod.exe monzero-wallet-cli.exe monzero-wallet-rpc.exe)
for binary in "${binaries[@]}"; do
  [[ -f "$build_bin/$binary" ]] || { echo "Missing executable: $build_bin/$binary" >&2; exit 1; }
  strings "$build_bin/$binary" | grep -Fx "$core_version" >/dev/null || {
    echo "Binary version does not match core commit: $binary" >&2; exit 1;
  }
done

package_name="monzero-${version}-windows-gui-x64"
mkdir -p "$output_dir"
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/monzero-windows-gui-package.XXXXXX")
trap 'rm -rf -- "$work_dir"' EXIT
package_dir="$work_dir/$package_name"
mkdir -p "$package_dir"

for binary in "${binaries[@]}"; do
  install -m 0755 "$build_bin/$binary" "$package_dir/$binary"
done
SOURCE_DATE_EPOCH=$source_epoch "${STRIP:-x86_64-w64-mingw32-strip}" --strip-all "$package_dir"/*.exe

for document in LICENSE README.md WHITEPAPER.md MONZERO_CHAIN_SPEC.md; do
  install -m 0644 "$source_root/$document" "$package_dir/$document"
done
for document in INDEPENDENT_REPRODUCTION.md RELEASE_CHECKLIST.md RELEASE_NOTES.md RELEASE_STATUS.md UPGRADE.md; do
  install -m 0644 "$source_root/docs/$document" "$package_dir/$document"
done
install -m 0644 "$source_root/utils/release/windows/README-WINDOWS.txt" "$package_dir/README-WINDOWS.txt"
for launcher in start-node.bat start-wallet-cli.bat start-mining.bat stop-mining.bat; do
  install -m 0644 "$source_root/utils/release/windows/$launcher" "$package_dir/$launcher"
done
install -m 0644 "$source_root/utils/release/windows/monzero-miner-reporter.ps1" "$package_dir/monzero-miner-reporter.ps1"
install -m 0644 "$extras/start-wallet-gui.bat" "$package_dir/start-wallet-gui.bat"
release_short=${version#genesis-}
release_title=$(tr '[:lower:]-' '[:upper:] ' <<< "$version")
sed -e "s/@GUI_COMMIT@/$gui_commit/" -e "s/@CORE_COMMIT@/$core_commit/" \
    -e "s/@RELEASE_TITLE@/$release_title/" -e "s/@RELEASE_SHORT@/$release_short/" "$extras/README-GUI.txt.in" > "$package_dir/README-GUI.txt"

{
  echo "package=$package_name"
  echo "created_utc=$(TZ=UTC date -d "@$source_epoch" +%Y-%m-%dT%H:%M:%SZ)"
  echo "gui_source_commit=$gui_commit"
  echo "core_source_commit=$core_commit"
  echo "core_version=$core_version"
  echo "build_target=x86_64-w64-mingw32"
  echo "build_tag=win-x64"
  echo "build_type=Release"
  echo "static=true"
  echo "dev_mode=false"
  echo "manual_core_pin=true"
  echo "build_environment_image_id=$build_environment_image_id"
  echo "gui_sha256=$(sha256sum "$package_dir/monzero-wallet-gui.exe" | awk '{print $1}')"
  echo "gui_pe_subsystem=Windows_GUI"
  echo "native_windows_tested=false"
  echo "code_signed=false"
  echo "independently_reproduced=false"
  echo "security_audited=false"
  echo "release_tests_run=false"
} > "$package_dir/GUI_BUILD_MANIFEST.txt"

(
  cd "$package_dir"
  find . -maxdepth 1 -type f ! -name SHA256SUMS -printf '%P\n' | LC_ALL=C sort |
    xargs -r sha256sum > SHA256SUMS
  sha256sum -c SHA256SUMS >/dev/null
  TZ=UTC find . -type f -exec touch -d "@$source_epoch" {} +
)

archive="$output_dir/$package_name.zip"
(cd "$work_dir" && TZ=UTC find "$package_name" -type f -printf '%p\n' | LC_ALL=C sort | zip -X -9 -q "$archive" -@)
(cd "$output_dir" && sha256sum "$(basename "$archive")" > "$(basename "$archive").sha256")
echo "$archive"
echo "$archive.sha256"
