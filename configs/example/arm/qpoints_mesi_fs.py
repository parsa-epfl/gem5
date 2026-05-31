# Copyright (c) 2026 EPFL
# All rights reserved.

"""Compatibility wrapper for the renamed QPoints timing-Ruby launcher.

The real implementation now lives in qpoints_timing_ruby_fs.py. Keep this
wrapper while older scripts and recorded command lines still refer to the
MESI-named path.
"""

from qpoints_timing_ruby_fs import *  # noqa: F401,F403
from qpoints_timing_ruby_fs import main


if __name__ == "__m5_main__":
    main()
