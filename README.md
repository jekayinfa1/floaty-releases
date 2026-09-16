# floaty-releases

Public Floaty desktop downloads are published in [Releases](https://github.com/jekayinfa1/floaty-releases/releases).

## Windows release transfer

The manual [Assemble verified Windows release](.github/workflows/assemble-windows.yml)
workflow transfers already-built installers when large uploads are unreliable.
It does not compile the app or execute downloaded installers. Only installer
bytes belong here; keep private application source and credentials out of this
repository and its release assets.

Split each versioned EXE, its setup blockmap, and `latest.yml` into ordered chunks
of at most 16 MiB. Upload them and `manifest.json` to a temporary draft release
named `upload-windows-VERSION-NUMBER`. The manifest contains `version` and `files`;
each file declares `name`, `size`, `sha256`, and ordered `parts` with the same
fields. Part names are `FILENAME.part-0000`, increasing from zero. Stable EXE
aliases declare `aliasOf` after their source files instead of uploading duplicate
bytes. The script accepts only the six expected Windows release filenames.

Dispatch with `runner_only=false`, the draft's `source_tag`, an existing public
`target_tag` such as `v3.0.84`, and the independently reviewed `manifest_sha256`.
The runner checks every chunk, assembled file, and uploaded asset against that
manifest. It refuses to replace mismatched published assets. Its repository
`GITHUB_TOKEN` needs `contents: write`; no personal token is required.

After a successful run, verify the public assets, separately promote global
latest and website download targets, then delete the temporary draft release.
Existing Mac assets are preserved. `runner_only=true` confirms runner availability
without downloading or publishing anything. No Actions cache or artifact storage
is used.
