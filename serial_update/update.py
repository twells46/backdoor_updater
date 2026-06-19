import os
import shutil
import sys


MODE = int("766", 8)
FILES = (
    ("balancer.sh", "/home/kipr/wombat-os/configFiles/balancer.sh"),
    ("wallaby_get_serial.sh", "/home/kipr/wombat-os/flashFiles/wallaby_get_serial.sh"),
)


def under_root(root_dir, path):
    if not root_dir:
        return path
    return os.path.join(root_dir, path.lstrip(os.sep))


def install_file(package_dir, source_name, target_path, root_dir):
    source_path = os.path.join(package_dir, source_name)
    if not os.path.isfile(source_path):
        raise RuntimeError("missing package file: %s" % (source_name,))

    real_target = under_root(root_dir, target_path)
    target_dir = os.path.dirname(real_target)
    if target_dir and not os.path.isdir(target_dir):
        os.makedirs(target_dir)

    temp_path = real_target + ".updater-tmp"
    try:
        shutil.copyfile(source_path, temp_path)
        os.chmod(temp_path, MODE)
        os.rename(temp_path, real_target)
        os.chmod(real_target, MODE)
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise

    sys.stdout.write("installed %s mode 766\n" % (target_path,))


def run(context):
    package_dir = context.get("package_dir")
    if not package_dir:
        raise RuntimeError("missing package_dir in update context")

    root_dir = context.get("root_dir")
    for source_name, target_path in FILES:
        install_file(package_dir, source_name, target_path, root_dir)
