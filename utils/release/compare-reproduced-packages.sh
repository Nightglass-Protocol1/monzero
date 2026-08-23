#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: compare-reproduced-packages.sh \
  <reference-linux.tar.gz> <reproduced-linux.tar.gz> \
  <reference-windows.zip> <reproduced-windows.zip> <attestation.json>

MONZERO_REPRODUCER_ID and MONZERO_REPRODUCER_ENVIRONMENT must identify the
independent builder and clean build environment. The command verifies all four
packages and requires byte-for-byte equality for each platform before writing
a canonical JSON attestation. Sign that JSON with the independent builder key.
EOF
  exit 2
}

[[ $# -eq 5 ]] || usage
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
reference_linux=$(realpath "$1")
reproduced_linux=$(realpath "$2")
reference_windows=$(realpath "$3")
reproduced_windows=$(realpath "$4")
attestation=$(realpath -m "$5")
reproducer_id=${MONZERO_REPRODUCER_ID:-}
reproducer_environment=${MONZERO_REPRODUCER_ENVIRONMENT:-}

[[ -n $reproducer_id && ${#reproducer_id} -le 200 ]] || {
  echo "MONZERO_REPRODUCER_ID must contain 1-200 characters" >&2; exit 2;
}
[[ -n $reproducer_environment && ${#reproducer_environment} -le 500 ]] || {
  echo "MONZERO_REPRODUCER_ENVIRONMENT must contain 1-500 characters" >&2; exit 2;
}
[[ ! -e $attestation ]] || {
  echo "Refusing to overwrite existing attestation: $attestation" >&2; exit 2;
}

"$script_dir/verify-package.sh" "$reference_linux" >/dev/null
"$script_dir/verify-package.sh" "$reproduced_linux" >/dev/null
"$script_dir/verify-windows-package.sh" "$reference_windows" >/dev/null
"$script_dir/verify-windows-package.sh" "$reproduced_windows" >/dev/null

reference_linux_hash=$(sha256sum "$reference_linux" | awk '{print $1}')
reproduced_linux_hash=$(sha256sum "$reproduced_linux" | awk '{print $1}')
reference_windows_hash=$(sha256sum "$reference_windows" | awk '{print $1}')
reproduced_windows_hash=$(sha256sum "$reproduced_windows" | awk '{print $1}')

[[ $reference_linux_hash == "$reproduced_linux_hash" ]] || {
  echo "Linux packages are not byte-for-byte reproducible" >&2; exit 1;
}
[[ $reference_windows_hash == "$reproduced_windows_hash" ]] || {
  echo "Windows packages are not byte-for-byte reproducible" >&2; exit 1;
}

work_dir=$(mktemp -d "${TMPDIR:-/tmp}/monzero-reproduction.XXXXXX")
trap 'rm -rf -- "$work_dir"' EXIT
mkdir "$work_dir/linux" "$work_dir/windows"
tar -xzf "$reference_linux" -C "$work_dir/linux"
unzip -q "$reference_windows" -d "$work_dir/windows"
linux_root=$(find "$work_dir/linux" -mindepth 1 -maxdepth 1 -type d -print -quit)
windows_root=$(find "$work_dir/windows" -mindepth 1 -maxdepth 1 -type d -print -quit)
linux_commit=$(sed -n 's/^source_commit=//p' "$linux_root/BUILD-MANIFEST.txt")
windows_commit=$(sed -n 's/^source_commit=//p' "$windows_root/BUILD-MANIFEST.txt")
[[ $linux_commit =~ ^[0-9a-f]{40}$ && $linux_commit == "$windows_commit" ]] || {
  echo "Linux and Windows packages do not share one valid source commit" >&2; exit 1;
}
grep -qx 'source_tree_dirty=false' "$linux_root/BUILD-MANIFEST.txt" || {
  echo "Reference Linux package was built from a dirty tree" >&2; exit 1;
}
grep -qx 'source_tree_dirty=false' "$windows_root/BUILD-MANIFEST.txt" || {
  echo "Reference Windows package was built from a dirty tree" >&2; exit 1;
}

mkdir -p -- "$(dirname -- "$attestation")"
python3 - "$attestation" "$reproducer_id" "$reproducer_environment" \
  "$linux_commit" "$reference_linux" "$reference_linux_hash" \
  "$reference_windows" "$reference_windows_hash" <<'PY'
import datetime, json, pathlib, sys

(
    output, builder, environment, commit,
    linux_path, linux_hash, windows_path, windows_hash,
) = sys.argv[1:]
document = {
    "schema_version": 1,
    "project": "Monzero",
    "result": "byte-for-byte-match",
    "source_commit": commit,
    "reproducer": builder,
    "build_environment": environment,
    "compared_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "artifacts": [
        {
            "platform": "linux-x86_64",
            "filename": pathlib.Path(linux_path).name,
            "sha256": linux_hash,
        },
        {
            "platform": "windows-x64",
            "filename": pathlib.Path(windows_path).name,
            "sha256": windows_hash,
        },
    ],
}
pathlib.Path(output).write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
PY

echo "Independent reproduction matched for Linux and Windows at $linux_commit"
echo "$attestation"
