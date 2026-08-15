#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 1 ]] || { echo "Usage: $0 <monzero-linux.tar.gz>" >&2; exit 2; }
archive=$(realpath "$1")
[[ -f "$archive" ]] || { echo "Archive not found: $archive" >&2; exit 2; }

work_dir=$(mktemp -d "${TMPDIR:-/tmp}/monzero-verify.XXXXXX")
trap 'rm -rf -- "$work_dir"' EXIT
tar -xzf "$archive" -C "$work_dir"

mapfile -t roots < <(find "$work_dir" -mindepth 1 -maxdepth 1 -type d)
[[ ${#roots[@]} -eq 1 ]] || { echo "Archive must contain exactly one root directory" >&2; exit 1; }
root=${roots[0]}

[[ -x "$root/monzerod" && -x "$root/monzero-wallet-cli" ]] || {
  echo "Required Monzero executables are missing" >&2
  exit 1
}
[[ -f "$root/BUILD-MANIFEST.txt" && -f "$root/SHA256SUMS" ]] || {
  echo "Build or checksum manifest is missing" >&2
  exit 1
}

if find "$root" -type l -print -quit | grep -q .; then
  echo "Package contains symbolic links" >&2
  exit 1
fi

(
  cd "$root"
  sha256sum -c SHA256SUMS
)

binary_report=$(file "$root/monzerod" "$root/monzero-wallet-cli")
echo "$binary_report"
if [[ ${RELEASE_STRICT:-0} == 1 ]]; then
  if grep -Eq 'dynamically linked|not stripped|with debug_info' <<< "$binary_report"; then
    echo "Strict release verification rejects dynamic, unstripped, or debug binaries" >&2
    exit 1
  fi
  grep -qx 'source_tree_dirty=false' "$root/BUILD-MANIFEST.txt" || {
    echo "Strict release verification rejects a dirty source manifest" >&2
    exit 1
  }
  grep -qx 'binary_build_reproducibility=verified' "$root/BUILD-MANIFEST.txt" || {
    echo "Strict release verification requires independently verified binary reproducibility" >&2
    exit 1
  }
fi
"$root/monzerod" --version
"$root/monzero-wallet-cli" --version
echo "Package verification passed: $archive"
