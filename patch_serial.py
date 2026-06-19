#!/usr/bin/env python
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


TARGET = '/home/kipr/updater.tar.gz'
STAGING_DIR = '/home/kipr/.updater-staging'
PACKAGE_DIRNAME = 'serial_update'
EXPECTED_SIZE = 2420
EXPECTED_SHA256 = 'eb97a2ee2fe2097dfc74a8ed42ad57d8abb6bab45279bffc6f250937a4556dff'
UPDATER_TAR_GZ_B64 = """\
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
qKCCCiqooIIKKqigggo+GX4Hipd8vABQAAA=
"""


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
    parts = value.replace("\\", "/").split("/")
    if value.startswith("/") or value.startswith("\\") or ".." in parts or "" in parts:
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
    context = {
        "archive_path": TARGET,
        "staging_dir": STAGING_DIR,
        "package_dir": package_dir,
        "manifest": manifest,
    }

    namespace = runpy.run_path(
        entrypoint_path,
        init_globals={"UPDATE_CONTEXT": context},
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
        "finished update from %s (%d bytes, sha256 %s)\n"
        % (TARGET, len(data), EXPECTED_SHA256)
    )


if __name__ == "__main__":
    try:
        update()
    except Exception:
        exc = sys.exc_info()[1]
        sys.stderr.write("update failed: %s\n" % (exc,))
        sys.exit(1)
