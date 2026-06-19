#!/usr/bin/env python3
"""Build a tar.gz update package and emit a Python runner script.

The emitted script decodes the embedded base64 payload, extracts it, and runs
the package entrypoint.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import stat
import sys
import tarfile
import textwrap


DEFAULT_TARGET = Path("/home/kipr/updater.tar.gz")
DEFAULT_STAGING_DIR = Path("/home/kipr/.updater-staging")


def check_relative_path(label: str, value: str) -> None:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} must be a relative path without '..': {value}")


def validate_payload(payload_dir: Path) -> None:
    if not payload_dir.is_dir():
        raise ValueError(f"payload path is not a directory: {payload_dir}")

    manifest_path = payload_dir / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"payload is missing manifest.json: {manifest_path}")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid manifest.json: {exc}") from exc

    if not isinstance(manifest, dict):
        raise ValueError("manifest.json must contain a JSON object")

    entrypoint = manifest.get("entrypoint")
    if not isinstance(entrypoint, str) or not entrypoint:
        raise ValueError("manifest.json must set a non-empty string entrypoint")

    check_relative_path("manifest entrypoint", entrypoint)
    entrypoint_path = payload_dir / entrypoint
    if not entrypoint_path.is_file():
        raise ValueError(f"entrypoint does not exist: {entrypoint_path}")


def build_tar_gz(payload_dir: Path, arcname: str, compression_level: int) -> bytes:
    validate_payload(payload_dir)
    check_relative_path("archive name", arcname)

    def package_filter(member: tarfile.TarInfo) -> tarfile.TarInfo | None:
        parts = Path(member.name).parts
        if "__pycache__" in parts or member.name.endswith((".pyc", ".pyo")):
            return None
        return member

    archive = io.BytesIO()
    with tarfile.open(
        fileobj=archive,
        mode="w:gz",
        compresslevel=compression_level,
    ) as tar:
        tar.add(payload_dir, arcname=arcname, recursive=True, filter=package_filter)
    return archive.getvalue()


def render_writer_script(
    encoded_payload: str,
    target: Path,
    staging_dir: Path,
    package_dirname: str,
    expected_size: int,
    expected_sha256: str,
) -> str:
    wrapped_payload = "\n".join(textwrap.wrap(encoded_payload, width=76))
    return f"""#!/usr/bin/env python
# Put this file next to main.py as updater.py, then copy/paste this into main.py:
#
# from updater import update
# update()

import base64
import hashlib
import json
import os
import runpy
import shutil
import sys
import tarfile


TARGET = {str(target)!r}
STAGING_DIR = {str(staging_dir)!r}
PACKAGE_DIRNAME = {package_dirname!r}
EXPECTED_SIZE = {expected_size}
EXPECTED_SHA256 = {expected_sha256!r}
UPDATER_TAR_GZ_B64 = \"\"\"\\
{wrapped_payload}
\"\"\"


def verify_payload(label, data):
    actual_size = len(data)
    actual_sha256 = hashlib.sha256(data).hexdigest()

    if actual_size != EXPECTED_SIZE:
        raise RuntimeError(
            "%s size mismatch: expected %d bytes, got %d bytes"
            % (label, EXPECTED_SIZE, actual_size)
        )

    if actual_sha256 != EXPECTED_SHA256:
        raise RuntimeError(
            "%s sha256 mismatch: expected %s, got %s"
            % (label, EXPECTED_SHA256, actual_sha256)
        )


def write_file(path, data):
    updater_file = open(path, "wb")
    try:
        updater_file.write(data)
    finally:
        updater_file.close()


def read_file(path):
    updater_file = open(path, "rb")
    try:
        return updater_file.read()
    finally:
        updater_file.close()


def make_parent_dir(path):
    target_dir = os.path.dirname(path)
    if target_dir and not os.path.isdir(target_dir):
        try:
            os.makedirs(target_dir)
        except OSError:
            if not os.path.isdir(target_dir):
                raise


def recreate_dir(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.remove(path)
    os.makedirs(path)


def check_relative_path(label, value):
    parts = value.replace("\\\\", "/").split("/")
    if value.startswith("/") or value.startswith("\\\\") or ".." in parts or "" in parts:
        raise RuntimeError("%s must be a relative path without '..': %s" % (label, value))


def safe_extract(archive_path, dest):
    archive = tarfile.open(archive_path, "r:gz")
    try:
        dest_abs = os.path.abspath(dest)
        members = archive.getmembers()
        for member in members:
            if member.issym() or member.islnk():
                raise RuntimeError("archive links not supported: %s" % (member.name,))

            member_abs = os.path.abspath(os.path.join(dest, member.name))
            if member_abs != dest_abs and not member_abs.startswith(dest_abs + os.sep):
                raise RuntimeError("unsafe archive path: %s" % (member.name,))

        archive.extractall(dest, members)
    finally:
        archive.close()


def load_manifest(package_dir):
    manifest_path = os.path.join(package_dir, "manifest.json")
    manifest_file = open(manifest_path, "r")
    try:
        manifest = json.load(manifest_file)
    finally:
        manifest_file.close()

    if not hasattr(manifest, "get"):
        raise RuntimeError("manifest.json must contain an object")

    entrypoint = manifest.get("entrypoint")
    if not entrypoint:
        raise RuntimeError("manifest.json must set entrypoint")

    check_relative_path("manifest entrypoint", entrypoint)
    entrypoint_path = os.path.join(package_dir, entrypoint)
    if not os.path.isfile(entrypoint_path):
        raise RuntimeError("entrypoint does not exist: %s" % (entrypoint_path,))

    return manifest, entrypoint_path


def run_package(package_dir):
    manifest, entrypoint_path = load_manifest(package_dir)
    context = {{
        "archive_path": TARGET,
        "staging_dir": STAGING_DIR,
        "package_dir": package_dir,
        "manifest": manifest,
    }}

    namespace = runpy.run_path(
        entrypoint_path,
        init_globals={{"UPDATE_CONTEXT": context}},
        run_name="__updater_package__",
    )
    run_func = namespace.get("run")
    if not hasattr(run_func, "__call__"):
        raise RuntimeError("entrypoint must define run(context)")
    run_func(context)


def update():
    data = base64.b64decode(UPDATER_TAR_GZ_B64)
    verify_payload("decoded payload", data)

    make_parent_dir(TARGET)
    write_file(TARGET, data)
    written_data = read_file(TARGET)
    verify_payload("written payload", written_data)

    recreate_dir(STAGING_DIR)
    safe_extract(TARGET, STAGING_DIR)

    check_relative_path("package directory", PACKAGE_DIRNAME)
    package_dir = os.path.join(STAGING_DIR, PACKAGE_DIRNAME)
    if not os.path.isdir(package_dir):
        raise RuntimeError("package directory does not exist: %s" % (package_dir,))

    run_package(package_dir)

    sys.stdout.write(
        "finished update from %s (%d bytes, sha256 %s)\\n"
        % (TARGET, len(data), EXPECTED_SHA256)
    )


if __name__ == "__main__":
    try:
        update()
    except Exception:
        exc = sys.exc_info()[1]
        sys.stderr.write("update failed: %s\\n" % (exc,))
        sys.exit(1)
"""


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compress an update package as tar.gz, base64-encode it, and "
            "emit a Python script that extracts and runs it."
        )
    )
    parser.add_argument("payload_dir", type=Path, help="directory to package")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="path for the emitted Python script; defaults to stdout",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET,
        help=f"archive path written by the emitted script (default: {DEFAULT_TARGET})",
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=DEFAULT_STAGING_DIR,
        help=(
            "directory where the emitted script extracts the package "
            f"(default: {DEFAULT_STAGING_DIR})"
        ),
    )
    parser.add_argument(
        "--arcname",
        help="top-level archive name; defaults to the payload directory name",
    )
    parser.add_argument(
        "--compression-level",
        type=int,
        default=6,
        choices=range(10),
        metavar="0-9",
        help="gzip compression level passed to tarfile (default: 6)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    payload_dir = args.payload_dir.resolve()
    arcname = args.arcname or payload_dir.name

    try:
        archive_bytes = build_tar_gz(payload_dir, arcname, args.compression_level)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    encoded_payload = base64.b64encode(archive_bytes).decode("ascii")
    archive_sha256 = hashlib.sha256(archive_bytes).hexdigest()
    writer_script = render_writer_script(
        encoded_payload,
        args.target,
        args.staging_dir,
        arcname,
        len(archive_bytes),
        archive_sha256,
    )

    if args.output:
        args.output.write_text(writer_script, encoding="utf-8")
        current_mode = args.output.stat().st_mode
        args.output.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    else:
        sys.stdout.write(writer_script)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
