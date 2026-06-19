# Backdoor Updater

Simple controller update handoff for teachers.

This project packages update files into a single `updater.py` script that can be
copied onto a KIPR/Wombat controller. A teacher can place that file next to
`main.py`, add two lines, and let the controller run the embedded update
package.

## Files

- `emit_updater_script.py` - build tool. Packages a payload directory as
  `tar.gz`, embeds it as base64, and emits a runner script.
- `updater.py` - generated runner script. This is the file teachers copy to the
  controller.
- `serial_update/` - test update package for the serial scripts.

## Build a New Updater

```sh
./emit_updater_script.py path/to/payload -o updater.py
```

Optional flags:

- `--target PATH` changes where the controller writes the temporary archive.
- `--staging-dir PATH` changes where the controller extracts the package.
- `--arcname NAME` changes the top-level directory inside the archive.
- `--compression-level N` changes the gzip compression level, 0-9.

## Use on a Controller

1. Copy `updater.py` next to `main.py`.
2. Add this to `main.py`:

   ```python
   from updater import update
   update()
   ```

3. Run the program once.
4. Confirm it prints the written path, size, and sha256.

The generated updater verifies the decoded payload and the written file,
extracts the package to `/home/kipr/.updater-staging`, then runs the package
entrypoint.

## Package Layout

An update package is a directory with this minimum shape:

```text
payload/
  manifest.json
  update.py
  other files needed by update.py
```

The whole directory is embedded into `updater.py` as a `tar.gz` archive.

## manifest.json

`manifest.json` is intentionally small:

```json
{
  "name": "serial_update",
  "version": "2026-06-19",
  "entrypoint": "update.py"
}
```

- `name` is a human-readable package name.
- `version` is a human-readable package version.
- `entrypoint` is the relative Python file the generated updater loads.

Only `entrypoint` is required by the runner.

## update.py

The entrypoint must define:

```python
def run(context):
    ...
```

`context` contains:

- `archive_path` - path where the generated updater wrote the embedded tarball.
- `staging_dir` - directory where the tarball was extracted.
- `package_dir` - extracted package directory.
- `manifest` - parsed `manifest.json`.

`update.py` owns the real update behavior: copy files, set permissions, and
print useful status.

## serial_update Payload

Build it with:

```sh
./emit_updater_script.py serial_update -o updater.py
```

It installs:

- `serial_update/balancer.sh` to `/home/kipr/wombat-os/configFiles/balancer.sh`
- `serial_update/wallaby_get_serial.sh` to `/home/kipr/wombat-os/flashFiles/wallaby_get_serial.sh`

Both files overwrite existing versions and finish with permissions `766`.

## Ignored Features

Skipped on purpose:

- cryptographic signatures
- rollback or backups
- dependency resolution
- service restart orchestration
- manifest-driven file maps
- remote downloads
- `tar.xz` compression

Add these only when a real update needs them.
