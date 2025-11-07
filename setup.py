from setuptools import setup, Extension
import sys

try:
    import numpy as _np
except Exception as exc:
    print("[setup] numpy is required at build time: ", exc, file=sys.stderr)
    raise

# qpSWIFT C extension sources and includes (vendored from src/qp-tools).
# Use POSIX-style, relative paths (required by setuptools).
qp_sources = [
    "src/qp-tools/python/pyqpSWIFT.c",
    "src/qp-tools/src/amd_1.c",
    "src/qp-tools/src/amd_2.c",
    "src/qp-tools/src/amd_aat.c",
    "src/qp-tools/src/amd_control.c",
    "src/qp-tools/src/amd_defaults.c",
    "src/qp-tools/src/amd_dump.c",
    "src/qp-tools/src/amd_global.c",
    "src/qp-tools/src/amd_info.c",
    "src/qp-tools/src/amd_order.c",
    "src/qp-tools/src/amd_post_tree.c",
    "src/qp-tools/src/amd_postorder.c",
    "src/qp-tools/src/amd_preprocess.c",
    "src/qp-tools/src/amd_valid.c",
    "src/qp-tools/src/ldl.c",
    "src/qp-tools/src/timer.c",
    "src/qp-tools/src/Auxilary.c",
    "src/qp-tools/src/qpSWIFT.c",
]

qp_include_dirs = [
    "src/qp-tools/include",
    _np.get_include(),
]

ext_modules = [
    Extension(
        name="qpSWIFT",
        sources=qp_sources,
        include_dirs=qp_include_dirs,
    )
]

# Delegate metadata to pyproject.toml (PEP 621). Packages are configured via pyproject.
setup(
    include_package_data=True,
    ext_modules=ext_modules,
)
