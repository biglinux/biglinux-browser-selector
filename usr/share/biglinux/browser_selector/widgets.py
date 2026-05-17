"""BigLinux Browser Selector — Custom GTK4 widgets."""

from __future__ import annotations

import os
import select
import threading

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from utils import APP_PATH, load_browser_icon  # noqa: E402
import gettext
_ = gettext.gettext


# ---------------------------------------------------------------------------
# BrowserCard
# ---------------------------------------------------------------------------
class BrowserCard(Gtk.Button):
    """Browser selection card with accessible state announcements."""

    def __init__(self, browser: dict, on_select) -> None:
        super().__init__()
        self.browser = browser
        self.on_select = on_select
        self.selected = False
        self.installed = self._check_installed()
        self.detected_desktop: str | None = None

        self.add_css_class("flat")
        self.add_css_class("browser-card")

        if not self.installed:
            self.add_css_class("dimmed")

        browser_label = browser.get("label", "")
        self.set_tooltip_text(browser_label)
        self._update_accessible_name()
        self.connect("clicked", self._on_click)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_halign(Gtk.Align.CENTER)
        content.set_valign(Gtk.Align.CENTER)
        content.set_margin_top(10)
        content.set_margin_bottom(10)
        self.set_child(content)

        overlay = Gtk.Overlay()
        overlay.set_halign(Gtk.Align.CENTER)
        content.append(overlay)

        icon_bg = Gtk.Box()
        icon_bg.add_css_class("browser-icon-bg")
        overlay.set_child(icon_bg)

        icon = load_browser_icon(browser.get("package", ""), 56)
        icon.add_css_class("browser-icon")
        icon_bg.append(icon)

        self.check_badge = Gtk.Box()
        self.check_badge.add_css_class("check-badge")
        self.check_badge.set_halign(Gtk.Align.END)
        self.check_badge.set_valign(Gtk.End)
        self.check_badge.set_visible(False)

        check_icon = Gtk.Image.new_from_icon_name("object-select-symbolic")
        check_icon.set_pixel_size(12)
        self.check_badge.append(check_icon)
        overlay.add_overlay(self.check_badge)

        self.spinner = Gtk.Spinner(spinning=False)
        self.spinner.set_halign(Gtk.Align.CENTER)
        self.spinner.set_valign(Gtk.Align.CENTER)
        self.spinner.set_visible(False)
        overlay.add_overlay(self.spinner)

        label = Gtk.Label(label=browser_label)
        label.add_css_class("browser-label")
        label.set_max_width_chars(12)
        label.set_wrap(True)
        content.append(label)

    def _check_installed(self) -> bool:
        for variant in self.browser.get("variants", []):
            check_path = variant.get("check", "")
            if check_path and os.path.exists(check_path):
                return True
        return False

    def _update_accessible_name(self) -> None:
        """Build a descriptive accessible name reflecting current state."""
        name = self.browser.get("label", "")
        parts = [name]
        if self.installed:
            parts.append(_("installed"))
        else:
            parts.append(_("not installed"))
        if self.selected:
            parts.append(_("default browser"))
        self.update_property([Gtk.AccessibleProperty.LABEL], [", ".join(parts)])

    def set_installed(self, installed: bool) -> None:
        self.installed = installed
        if installed:
            self.remove_css_class("dimmed")
        else:
            self.add_css_class("dimmed")
        self._update_accessible_name()

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        if selected:
            self.add_css_class("selected")
            self.check_badge.set_visible(True)
        else:
            self.remove_css_class("selected")
            self.check_badge.set_visible(False)
        self._update_accessible_name()

    def set_loading(self, loading: bool) -> None:
        self.spinner.set_visible(loading)
        if loading:
            self.spinner.start()
            self.add_css_class("dimmed")
        else:
            self.spinner.stop()
            if self.installed:
                self.remove_css_class("dimmed")
        # Accessibility: announce busy state to screen readers
        self.update_state([Gtk.AccessibleState.BUSY], [loading])

    def _on_click(self, _btn: Gtk.Button) -> None:
        self.on_select(self)


# ---------------------------------------------------------------------------
# InstallPanel
# ---------------------------------------------------------------------------
class InstallPanel(Gtk.Box):
    """Installation panel with progress display and controls."""

    def __init__(
        self, browser_label: str, icon_path: str | None = None
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.browser_label = browser_label
        self.cancelled = False
        self._done_callback = None
        self._cancel_callback = None

        self.set_margin_top(28)
        self.set_margin_bottom(32)
        self.set_margin_start(40)
        self.set_margin_end(40)

        # Header with icon and label
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        header.set_halign(Gtk.Align.CENTER)

        if icon_path and os.path.exists(icon_path):
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_path, 48, 48)
                icon = Gtk.Image.new_from_pixbuf(pb)
            except GLib.Error:
                icon = Gtk.Image.new_from_icon_name("package-install-symbolic")
        else:
            icon = Gtk.Image.new_from_icon_name("package-install-symbolic")

        icon.set_pixel_size(48)
        header.append(icon)

        label = Gtk.Label(label=browser_label)
        label.add_css_class("panel-title")
        header.append(label)
        self.append(header)

        # Log area
        self.log_text = Gtk.TextView()
        self.log_text.set_editable(False)
        self.log_text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_buffer = self.log_text.get_buffer()

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.append(self.log_text)
        scrolled.add_css_class("log-box")
        self.append(scrolled)

        # Progress dots with title
        self.progress_dots = None  # Will be initialized later
        self._dot_timer_id: int | None = None

        # Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER)

        cancel_btn = Gtk.Button(label=_("Cancel"))
        cancel_btn.add_css_class("suggested-action")
        cancel_btn.connect("clicked", self._on_cancel)
        self.cancel_btn = cancel_btn
        btn_box.append(cancel_btn)

        done_btn = Gtk.Button(label=_("Done"))
        done_btn.add_css_class("success")
        done_btn.set_visible(False)
        done_btn.connect("clicked", self._on_done)
        self.done_btn = done_btn
        btn_box.append(done_btn)

        self.append(btn_box)

    def start_pulse(self) -> None:
        """Start the pulse animation."""
        if not hasattr(self, "_pulse_label"):
            return
        self._pulse_label.set_visible(True)
        self.cancel_btn.set_sensitive(False)

    def stop_pulse(self) -> None:
        """Stop the pulse animation."""
        if not hasattr(self, "_pulse_label"):
            return
        self._pulse_label.set_visible(False)
        self.cancel_btn.set_sensitive(True)

    @property
    def cancelled(self) -> bool:
        return getattr(self, "_cancelled", False)

    @cancelled.setter
    def cancelled(self, value: bool) -> None:
        self._cancelled = value
        if value and hasattr(self, "cancel_btn"):
            self.cancel_btn.set_visible(False)
            if hasattr(self, "done_btn"):
                self.done_btn.set_visible(True)

    def append_log(self, line: str) -> None:
        """Append a log line to the text view."""
        tag = self._get_line_tag(line)
        iter_end = self.log_buffer.get_iter_at_mark(
            self.log_buffer.get_insert()
        )
        if tag:
            self.log_buffer.apply_tag(tag, iter_end, iter_end)
        else:
            self.log_buffer.insert(iter_end, line + "\n")

    def _get_line_tag(self, line: str) -> Gtk.TextTag | None:
        """Create a text tag for special log lines."""
        if "STATUS:" in line:
            tag = self.log_buffer.create_tag("status", foreground="red")
            return tag
        return None

    def set_progress(self, percent: int) -> None:
        """Set progress percentage (0-100)."""
        pass  # Simplified version

    def set_success(self, browser_label: str) -> None:
        """Show success state."""
        self.append_log(f"STATUS:success")

    def set_error(self, _browser_label: str) -> None:
        """Show error state."""
        if hasattr(self, "cancel_btn"):
            self.cancel_btn.set_visible(False)
        if hasattr(self, "done_btn"):
            self.done_btn.set_visible(True)

    def set_done_callback(self, callback: callable) -> None:
        """Set callback for done button."""
        self._done_callback = callback

    def set_cancel_callback(self, callback: callable) -> None:
        """Set callback for cancel button."""
        self._cancel_callback = callback

    def _on_toggle_details(self, _btn: Gtk.Button) -> None:
        pass  # Simplified version

    def _on_cancel(self, _btn: Gtk.Button) -> None:
        self.cancelled = True
        if self._cancel_callback:
            self._cancel_callback()

    def _on_done(self, _btn: Gtk.Button) -> None:
        if self._done_callback:
            self._done_callback()


# ---------------------------------------------------------------------------
# AnimatedLogo (simplified version)
# ---------------------------------------------------------------------------
class AnimatedLogo(Gtk.DrawingArea):
    """Animated logo drawing area."""

    def __init__(self) -> None:
        super().__init__()
        self.set_size_request(128, 128)
        self._animating = False
        self._frame = 0
        self._timer_id: int | None = None
        self.connect("draw", self._draw)

    def _animate(self) -> bool:
        if not self._animating:
            return False
        self._frame = (self._frame + 1) % 60
        self.queue_draw()
        return True

    def _draw(self, _widget: Gtk.DrawingArea, cr: cairo.Context) -> bool:
        if not hasattr(self, "_animating") or not self._animating:
            return False
        return True

    def start_animation(self) -> None:
        """Start the animation."""
        if not self._animating:
            self._animating = True
            self._frame = 0
            self._timer_id = GLib.timeout_add(16, self._animate)

    def stop(self) -> None:
        """Stop the animation."""
        self._animating = False
        if self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = None
