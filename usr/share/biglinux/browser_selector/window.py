"""BigLinux Browser Selector — Main window."""

from __future__ import annotations

import os
import select
import subprocess
import threading

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from utils import APP_PATH  # noqa: E402
from widgets import BrowserCard, InstallPanel  # noqa: E402


def _flush_line_buffer(buf: bytes, panel: InstallPanel) -> bytes:
    """Flush a line buffer to the install panel."""
    while b"\n" in buf:
        line, buf = buf.split(b"\n", 1)
        try:
            text = line.decode("utf-8")
            GLib.idle_add(panel.append_log, text)
        except UnicodeDecodeError:
            pass
    return buf


class BrowserSelectorWindow(Gtk.Window):
    """Main window for the browser selector."""

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.browser_cards = []
        self._install_proc: subprocess.Popen[bytes] | None = None
        self._browser_loading_overlay: Gtk.Box | None = None

        self.set_application(app)
        self.set_default_size(900, 700)
        self.set_title("BigLinux Browser Selector")

        self._build_ui()
        GLib.idle_add(self.refresh_browser_states)

    def _build_ui(self) -> None:
        """Build the UI."""
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=26)
        main.set_margin_top(28)
        main.set_margin_bottom(32)
        main.set_margin_start(40)
        main.set_margin_end(40)
        scroll.set_child(main)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        header.set_halign(Gtk.Align.CENTER)
        main.append(header)

        title = Gtk.Label(label="Choose your default browser")
        title.add_css_class("page-title")
        header.append(title)

        subtitle = "Select and install the web browser of your choice."
        sub = Gtk.Label(label=subtitle)
        sub.add_css_class("page-subtitle")
        sub.set_wrap(True)
        sub.set_max_width_chars(55)
        sub.set_justify(Gtk.Justification.CENTER)
        header.append(sub)

        # Browser stack
        self.browser_stack = Gtk.Stack()
        self.browser_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.browser_stack.set_transition_duration(280)
        self.browser_stack.set_vexpand(True)
        main.append(self.browser_stack)

        # Cards grid
        cards_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        cards_container.set_halign(Gtk.Align.CENTER)
        cards_container.set_valign(Gtk.Align.START)

        browsers = self._load_browsers_config()
        items_per_row = 5
        for i in range(0, len(browsers), items_per_row):
            row_browsers = browsers[i : i + items_per_row]
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
            row.set_halign(Gtk.Align.CENTER)
            cards_container.append(row)

            for browser in row_browsers:
                card = BrowserCard(browser, self._on_browser_select)
                self.browser_cards.append(card)
                row.append(card)

        self.browser_stack.add_named(cards_container, "browsers")

        # Install panel placeholder
        placeholder = Gtk.Box()
        self.browser_stack.add_named(placeholder, "installing")

        # Loading overlay for "set default"
        self._browser_loading_overlay = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=12
        )
        self._browser_loading_overlay.set_halign(Gtk.Align.CENTER)
        self._browser_loading_overlay.set_valign(Gtk.Align.CENTER)
        self._browser_loading_overlay.set_visible(False)
        self._browser_loading_overlay.add_css_class("browser-loading-overlay")

        self._browser_loading_spinner = Gtk.Spinner()
        self._browser_loading_spinner.set_size_request(48, 48)
        self._browser_loading_overlay.append(self._browser_loading_spinner)

        self._browser_loading_label = Gtk.Label(label="")
        self._browser_loading_label.add_css_class("page-subtitle")
        self._browser_loading_overlay.append(self._browser_loading_label)

        page_overlay = Gtk.Overlay()
        page_overlay.set_child(scroll)
        page_overlay.add_overlay(self._browser_loading_overlay)

        self.set_content(page_overlay)

    def _load_browsers_config(self) -> list[dict]:
        """Load browser configuration from YAML."""
        yaml_path = os.path.join(APP_PATH, "pages.yaml")
        browsers = []

        try:
            with open(yaml_path, encoding="utf-8") as f:
                content = f.read()

            # Simple YAML parsing for our specific format
            current_browser = {}
            current_variant = None

            for line in content.split("\n"):
                line = line.strip()

                if line.startswith("- label:"):
                    if current_browser and "label" in current_browser:
                        browsers.append(current_browser)
                    current_browser = {"variants": []}
                    current_variant = None
                    value = line[8:].strip().strip('"\'')
                    current_browser["label"] = value

                elif line.startswith("package:") and current_browser is not None:
                    value = line[8:].strip().strip('"\'')
                    if value:
                        current_browser["package"] = value

                elif line.startswith("- {"):
                    # New variant object
                    current_variant = {}
                    current_browser["variants"].append(current_variant)

                elif "check:" in line and current_variant is not None:
                    start = line.find('check:') + 6
                    end = line.find('"', start)
                    if end == -1:
                        end = line.find("'", start)
                    check_path = line[start:end].strip()
                    current_variant["check"] = check_path

                elif "desktop:" in line and current_variant is not None:
                    start = line.find('desktop:') + 8
                    end = line.find('"', start)
                    if end == -1:
                        end = line.find("'", start)
                    desktop = line[start:end].strip()
                    current_variant["desktop"] = desktop

            # Add last browser
            if current_browser and "label" in current_browser:
                browsers.append(current_browser)

        except Exception as e:
            print(f"Error loading browsers config: {e}")

        return browsers

    def _run_browser_script(self, args: list[str]) -> str:
        """Run browser script and return output."""
        script_path = os.path.join(APP_PATH, "scripts", "browser.sh")
        try:
            cmd = [script_path] + args
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=300
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
            print(f"Error running browser script {args}: {e}")
            return ""

    def refresh_browser_states(self) -> bool:
        """Refresh the state of all browser cards."""
        current_browser_default = self._run_browser_script(["getBrowser"])

        for card in self.browser_cards:
            is_installed = False
            installed_desktop = None

            for variant in card.browser.get("variants", []):
                check_path = variant.get("check", "")
                if check_path and os.path.exists(check_path):
                    is_installed = True
                    installed_desktop = variant.get("desktop", "")
                    break

            card.set_installed(is_installed)
            card.detected_desktop = installed_desktop
            card.set_selected(
                is_installed and installed_desktop == current_browser_default
            )

        return GLib.SOURCE_REMOVE

    def _on_browser_select(self, selected_card: BrowserCard) -> None:
        """Handle browser selection."""
        browser = selected_card.browser

        # If already installed, just set as default (no panel needed)
        is_installed = any(
            os.path.exists(v.get("check", "")) for v in browser.get("variants", [])
        )
        if is_installed:
            thread = threading.Thread(
                target=self._set_default_browser, args=(selected_card,), daemon=True
            )
            thread.start()
            return

        # Not installed → show integrated install panel
        self._start_install(selected_card)

    def _set_default_browser(self, card: BrowserCard) -> None:
        """Set an already-installed browser as default (background thread)."""
        browser_label = card.browser.get("label", "")
        GLib.idle_add(self._show_browser_loading, browser_label)
        try:
            desktop_to_set = None
            for variant in card.browser.get("variants", []):
                if os.path.exists(variant.get("check", "")):
                    desktop_to_set = variant.get("desktop", "")
                    break
            if desktop_to_set:
                self._run_browser_script(["setBrowser", desktop_to_set])
        finally:
            GLib.idle_add(self._hide_browser_loading, browser_label)
            GLib.idle_add(self.refresh_browser_states)

    def _show_browser_loading(self, browser_label: str) -> None:
        """Show loading overlay."""
        self._browser_loading_label.set_label(
            f"Setting {browser_label} as default…"
        )
        self._browser_loading_overlay.set_visible(True)
        self._browser_loading_spinner.start()
        for card in self.browser_cards:
            card.set_sensitive(False)

    def _hide_browser_loading(self, browser_label: str = "") -> None:
        """Hide loading overlay."""
        self._browser_loading_spinner.stop()
        for card in self.browser_cards:
            card.set_sensitive(True)
        if browser_label:
            self._browser_loading_label.set_label(
                f"{browser_label} set as default"
            )
            GLib.timeout_add(1500, self._dismiss_browser_overlay)
        else:
            self._browser_loading_overlay.set_visible(False)

    def _dismiss_browser_overlay(self) -> bool:
        """Dismiss the loading overlay."""
        self._browser_loading_overlay.set_visible(False)
        return GLib.SOURCE_REMOVE

    def _start_install(self, card: BrowserCard) -> None:
        """Show the install panel and start the installation process."""
        browser = card.browser
        browser_label = browser.get("label", "")
        package = browser.get("package", "")
        icon_path = (
            os.path.join(APP_PATH, "image", "browsers", f"{package}.svg")
            if package
            else None
        )

        # Create and attach the install panel
        panel = InstallPanel(browser_label, icon_path)
        panel.set_done_callback(lambda: self._finish_install(browser_label))
        panel.set_cancel_callback(self._cancel_install)

        # Replace the installing page in the stack
        old = self.browser_stack.get_child_by_name("installing")
        if old:
            self.browser_stack.remove(old)
        self.browser_stack.add_named(panel, "installing")
        self.browser_stack.set_visible_child_name("installing")

    def _cancel_install(self) -> None:
        """Cancel the running installation."""
        proc = getattr(self, "_install_proc", None)
        if proc and proc.poll() is None:
            proc.terminate()

    def _perform_browser_install(
        self, card: BrowserCard, panel: InstallPanel
    ) -> None:
        """Run browser installation script."""
        browser = card.browser
        package = browser.get("package", "")
        script_path = os.path.join(APP_PATH, "scripts", "browser.sh")

        try:
            proc = subprocess.Popen(
                [script_path, "install", package],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                bufsize=0,
            )
            self._install_proc = proc

            if proc.stdout is None:
                raise OSError("Failed to capture process output")

            self._read_process_output(proc, panel)
            proc.wait(timeout=600)

        except (OSError, subprocess.TimeoutExpired) as e:
            GLib.idle_add(panel.append_log, str(e))

    @staticmethod
    def _read_process_output(
        proc: subprocess.Popen[bytes], panel: InstallPanel
    ) -> None:
        """Read subprocess output and display it."""
        assert proc.stdout is not None
        buf = b""
        fd = proc.stdout.fileno()

        while True:
            ready, _, _ = select.select([fd], [], [], 5.0)
            if not ready:
                continue
            chunk = os.read(fd, 4096)
            if not chunk:
                break
            buf += chunk
            buf = _flush_line_buffer(buf, panel)

    def _finish_install(self, browser_label: str) -> None:
        """Called when user clicks Done on the install panel."""
        self.browser_stack.set_visible_child_name("browsers")
        self.refresh_browser_states()
