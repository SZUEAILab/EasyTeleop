from __future__ import annotations

import os
from pathlib import Path


_SDK_DIR_ENV = "EASYTELEOP_TRRO_SDK_DIR"
_SDK_DIRNAME = "trro-gateway-sdk-x64-release"
_DEFAULT_LIB_REL = Path("sdk_lib") / "libtrro_field.so"
_DEFAULT_CFG_REL = Path("config.json")


def _find_trro_sdk_dir() -> Path | None:
    """
    Resolve TRRO SDK directory in the following order:
      1) $EASYTELEOP_TRRO_SDK_DIR
      2) Vendored runtime assets inside the EasyTeleop package
      3) Repository layout: <repo>/third-party/trro-gateway-sdk-x64-release
    """
    env_dir = os.getenv(_SDK_DIR_ENV)
    if env_dir:
        p = Path(env_dir).expanduser().resolve()
        if p.is_dir():
            return p

    # Installed package layout: EasyTeleop/third_party/trro-gateway-sdk-x64-release
    package_root = Path(__file__).resolve().parents[2]  # .../EasyTeleop
    packaged = package_root / "third_party" / _SDK_DIRNAME
    if packaged.is_dir():
        return packaged

    # Dev layout: <repo>/third-party/trro-gateway-sdk-x64-release
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "third-party" / _SDK_DIRNAME
        if candidate.is_dir():
            return candidate

    return None


def get_trro_default_paths() -> tuple[str, str]:
    """
    Returns (lib_path, config_path).
    If no SDK directory is found, returns repo-relative defaults for compatibility.
    """
    sdk_dir = _find_trro_sdk_dir()
    if sdk_dir is None:
        base = Path("third-party") / _SDK_DIRNAME
        return (str(base / _DEFAULT_LIB_REL), str(base / _DEFAULT_CFG_REL))

    return (str(sdk_dir / _DEFAULT_LIB_REL), str(sdk_dir / _DEFAULT_CFG_REL))

