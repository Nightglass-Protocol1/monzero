#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 1 ]] || { echo "Usage: $0 <monzero-linux.tar.gz>" >&2; exit 2; }
archive=$(realpath "$1")
[[ -f "$archive" ]] || { echo "Archive not found: $archive" >&2; exit 2; }

work_dir=$(mktemp -d "${TMPDIR:-/tmp}/monzero-verify.XXXXXX")
trap 'rm -rf -- "$work_dir"' EXIT

# Screen the archive before extraction. GNU tar strips dangerous prefixes by
# default, but a release verifier must reject them rather than silently alter
# what it is verifying.
mapfile -t archive_entries < <(tar -tzf "$archive")
[[ ${#archive_entries[@]} -gt 0 ]] || { echo "Archive is empty" >&2; exit 1; }
for entry in "${archive_entries[@]}"; do
  [[ $entry != /* && $entry != ../* && $entry != */../* && $entry != */.. ]] || {
    echo "Archive contains an unsafe path: $entry" >&2
    exit 1
  }
done
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
for required_document in README.md UPGRADE.md RELEASE_STATUS.md RELEASE_CHECKLIST.md LICENSE; do
  [[ -f "$root/$required_document" ]] || {
    echo "Required release document is missing: $required_document" >&2
    exit 1
  }
done

manifest_package=$(sed -n 's/^package=//p' "$root/BUILD-MANIFEST.txt")
[[ $manifest_package == "$(basename "$root")" ]] || {
  echo "Build manifest package name does not match archive root" >&2
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
daemon_version=$("$root/monzerod" --version | head -n 1)
wallet_version=$("$root/monzero-wallet-cli" --version | head -n 1)
[[ -n $daemon_version && $daemon_version == "$wallet_version" ]] || {
  echo "Packaged executables report inconsistent versions" >&2
  exit 1
}
grep -Fqx "binary_version=$daemon_version" "$root/BUILD-MANIFEST.txt" || {
  echo "Packaged executable version does not match the build manifest" >&2
  exit 1
}
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
echo "$daemon_version"
echo "$wallet_version"
echo "Package verification passed: $archive"
