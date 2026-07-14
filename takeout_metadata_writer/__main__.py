"""Entry point for ``python -m takeout_metadata_writer``.

Simply delegates to :func:`takeout_metadata_writer.cli.main`, which uses
:mod:`argparse` to parse ``sys.argv`` and drives the full pipeline.
"""

from __future__ import annotations

import sys

from takeout_metadata_writer.cli import main

sys.exit(main())
