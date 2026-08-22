#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 1 ]] || { echo "Usage: $0 <monzero-windows.zip>" >&2; exit 2; }
archive=$(realpath "$1")
[[ -f "$archive" ]] || { echo "Archive not found: $archive" >&2; exit 2; }
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/monzero-windows-verify.XXXXXX")
trap 'rm -rf -- "$work_dir"' EXIT

mapfile -t entries < <(zipinfo -1 "$archive")
[[ ${#entries[@]} -gt 0 ]] || { echo "Archive is empty" >&2; exit 1; }
for entry in "${entries[@]}"; do
  [[ $entry != /* && $entry != ../* && $entry != */../* && $entry != */.. && $entry != *\\* ]] || {
    echo "Archive contains an unsafe path: $entry" >&2; exit 1;
  }
done
unzip -q "$archive" -d "$work_dir"
mapfile -t roots < <(find "$work_dir" -mindepth 1 -maxdepth 1 -type d)
[[ ${#roots[@]} -eq 1 ]] || { echo "Archive must contain exactly one root directory" >&2; exit 1; }
root=${roots[0]}

for required in monzerod.exe monzero-wallet-cli.exe monzero-wallet-rpc.exe BUILD-MANIFEST.txt SHA256SUMS README.md UPGRADE.md RELEASE_STATUS.md RELEASE_CHECKLIST.md LICENSE; do
  [[ -f "$root/$required" ]] || { echo "Required package file is missing: $required" >&2; exit 1; }
done
[[ $(sed -n 's/^package=//p' "$root/BUILD-MANIFEST.txt") == "$(basename "$root")" ]] || {
  echo "Build manifest package name does not match archive root" >&2; exit 1;
}
if find "$root" -type l -print -quit | grep -q .; then echo "Package contains symbolic links" >&2; exit 1; fi
(cd "$root" && sha256sum -c SHA256SUMS)

source_commit=$(sed -n 's/^source_commit=//p' "$root/BUILD-MANIFEST.txt")
[[ $source_commit =~ ^[0-9a-f]{40}$ ]] || { echo "Invalid source commit in manifest" >&2; exit 1; }
source_short=${source_commit:0:9}
for binary in monzerod.exe monzero-wallet-cli.exe monzero-wallet-rpc.exe; do
  report=$(file "$root/$binary")
  echo "$report"
  grep -Fq 'PE32+ executable' <<< "$report" || { echo "Not a Windows x64 PE binary: $binary" >&2; exit 1; }
  strings "$root/$binary" | grep -Fq "0.18.5.1-$source_short" || { echo "Version mismatch: $binary" >&2; exit 1; }
  while read -r library; do
    case ${library^^} in
      ADVAPI32.DLL|BCRYPT.DLL|CRYPT32.DLL|IPHLPAPI.DLL|KERNEL32.DLL|MSVCRT.DLL|MSWSOCK.DLL|SHELL32.DLL|USER32.DLL|WS2_32.DLL) ;;
      *) echo "Unexpected runtime dependency $library in $binary" >&2; exit 1 ;;
    esac
  done < <(x86_64-w64-mingw32-objdump -p "$root/$binary" | sed -n 's/^\s*DLL Name: //p')
done
grep -Fqx "binary_version=Monzero 'Fluorine Fermi' (v0.18.5.1-${source_short})" "$root/BUILD-MANIFEST.txt" || {
  echo "Binary version does not match manifest" >&2; exit 1;
}

if [[ ${RELEASE_STRICT:-0} == 1 ]]; then
  grep -qx 'source_tree_dirty=false' "$root/BUILD-MANIFEST.txt" || { echo "Strict verification rejects dirty source" >&2; exit 1; }
  grep -qx 'binaries_stripped=true' "$root/BUILD-MANIFEST.txt" || { echo "Strict verification requires stripped binaries" >&2; exit 1; }
  grep -qx 'binary_build_reproducibility=verified' "$root/BUILD-MANIFEST.txt" || {
    echo "Strict verification requires independently verified binary reproducibility" >&2; exit 1;
  }
fi
echo "Package verification passed: $archive"
