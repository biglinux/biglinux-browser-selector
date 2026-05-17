#!/usr/bin/env python3

"""BigLinux Browser Selector — Entry point.

Simplified version with only browser selection functionality.
"""

from __future__ import annotations

import gettext
import locale
import sys

# Internationalization
DOMAIN = "biglinux-browser-selector"
LOCALE_DIR = "/usr/share/locale"
locale.setlocale(locale.LC_ALL, "")
locale.bindtextdomain(DOMAIN, LOCALE_DIR)
gettext.bindtextdomain(DOMAIN, LOCALE_DIR)
gettext.textdomain(DOMAIN)

from app import BigLinuxBrowserSelectorApp  # noqa: E402


def main() -> None:
    """Entry point."""
    app = BigLinuxBrowserSelectorApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
