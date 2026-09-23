# Monzero release build environment

These files pin the environment used to build and package Genesis releases,
so that a second builder can reproduce the published archives.

| Image | Built from | Purpose |
| --- | --- | --- |
| `monzero-build-env:jammy` | `Containerfile` (Ubuntu 22.04 by digest, GCC 11, mingw-w64 posix, glibc 2.35) | core `contrib/depends` builds for Linux and Windows |
| `monzero-build-env:jammy-pkg` | `Containerfile.pkg` | adds `zip`/`unzip` for packaging |
| `monzero-gui-build-env:windows` | the GUI repository's `Dockerfile.windows`, plus `ENV TAR_OPTIONS=--no-same-owner` under rootless podman | static Qt Windows GUI |

Build paths are embedded in the binaries, so build at the same absolute path
as the build you are reproducing (mount the checkout at that path).

```sh
podman build -t monzero-build-env:jammy -f contrib/release-env/Containerfile contrib/release-env
podman build -t monzero-build-env:jammy-pkg -f contrib/release-env/Containerfile.pkg contrib/release-env

# From a clean checkout of the release commit with submodules:
for target in x86_64-linux-gnu x86_64-w64-mingw32; do
  podman run --rm --userns=keep-id -v "$PWD":"$SRC_PATH" -w "$SRC_PATH" \
    monzero-build-env:jammy bash -c "make depends target=$target -j$(nproc)"
done

# Package inside the packaging image (same mount):
bash utils/release/package-linux.sh build/x86_64-linux-gnu/release/bin OUT genesis-preNN
bash utils/release/package-windows.sh build/x86_64-w64-mingw32/release/bin OUT genesis-preNN
bash utils/release/package-source.sh "$(git rev-parse HEAD)" OUT genesis-preNN
```

The Windows GUI is built in the GUI repository with `MANUAL_SUBMODULES=1`
and its `monero/` directory checked out at the same core commit, then
packaged with `utils/release/package-windows-gui.sh`.

Reproducibility observed for Genesis pre15 (commit `85d922cb0`): a second,
from-scratch build in these images, from a fresh clone at the same path,
reproduced the Linux and Windows command-line archives and all four
executables of the Windows GUI package byte for byte. Windows executables did
not match until MinGW executables were linked with `--no-insert-timestamp`
(`098550894`), because ld stamped the export table with the link time. The GUI
image sets `SOURCE_DATE_EPOCH`, which the older GUI linker already honours.
