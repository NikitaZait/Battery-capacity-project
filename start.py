import sys
import math
import numpy as np
import tkinter as tk
from tkinter import messagebox
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.collections import LineCollection

try:
    import customtkinter as ctk
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    USE_CTK = True
except ImportError:
    USE_CTK = False

from battery_model import BatterySimulator
from f1_tracks import F1_TRACKS, get_track_keys, get_track_display_name, get_track_info_text


class BatteryApp:
    # Track mode constants
    MODE_CUSTOM = "custom"

    def __init__(self, root):
        self.root = root
        self.root.title("Formula SAE - Battery Capacity & Thermal Model")
        self.root.geometry("1280x850")

        if not USE_CTK:
            self.root.configure(bg="#1e1e1e")

        self.inputs_visible = True
        self.track_mode = self.MODE_CUSTOM  # "custom" or an F1 track key
        self._saved_custom_values = {}  # store custom field values when switching to preset
        self._build_ui()
        self.run_sim()

    def _build_ui(self):
        # Main layout container
        if USE_CTK:
            self.main_container = ctk.CTkFrame(self.root)
            self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

            # Left Panel Container (Fixed width 360)
            self.left_panel = ctk.CTkFrame(self.main_container, width=360)
            self.left_panel.pack(side="left", fill="y", padx=5, pady=5)
            self.left_panel.pack_propagate(False)

            # Header Button (Toggles between Input Parameters and Performance Graphs)
            self.btn_toggle = ctk.CTkButton(
                self.left_panel,
                text="⚙️ Input Parameters  ▲ (Click for Graphs)",
                command=self.toggle_inputs,
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color="#1f538d",
                hover_color="#14375e",
                height=36
            )
            self.btn_toggle.pack(fill="x", padx=5, pady=(5, 5))

            # Sub-frame 1: Inputs Scrollable Frame (visible by default)
            self.inputs_frame = ctk.CTkScrollableFrame(self.left_panel)
            self.inputs_frame.pack(fill="both", expand=True, padx=2, pady=2)

            # Sub-frame 2: Performance Graphs Frame (hidden initially, shown on toggle)
            self.graphs_frame = ctk.CTkFrame(self.left_panel)

            # Right Content Area (Summary Cards & Main Track View Canvas)
            content_area = ctk.CTkFrame(self.main_container)
            content_area.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        else:
            self.main_container = tk.Frame(self.root, bg="#1e1e1e")
            self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

            self.left_panel = tk.Frame(self.main_container, bg="#2d2d2d", width=360)
            self.left_panel.pack(side="left", fill="y", padx=5, pady=5)
            self.left_panel.pack_propagate(False)

            self.btn_toggle = tk.Button(
                self.left_panel,
                text="⚙️ Input Parameters  ▲ (Click for Graphs)",
                command=self.toggle_inputs,
                bg="#007acc",
                fg="#ffffff",
                font=("Arial", 10, "bold"),
                height=2
            )
            self.btn_toggle.pack(fill="x", padx=5, pady=(5, 5))

            self.inputs_frame = tk.Frame(self.left_panel, bg="#2d2d2d")
            self.inputs_frame.pack(fill="both", expand=True, padx=2, pady=2)

            self.graphs_frame = tk.Frame(self.left_panel, bg="#2d2d2d")

            content_area = tk.Frame(self.main_container, bg="#1e1e1e")
            content_area.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        # --- Track Selector Dropdown at top of Inputs Frame ---
        dropdown_values = ["🔧 Custom Track"]
        self._dropdown_key_map = {"🔧 Custom Track": self.MODE_CUSTOM}
        for key in get_track_keys():
            display = get_track_display_name(key)
            dropdown_values.append(display)
            self._dropdown_key_map[display] = key

        if USE_CTK:
            lbl_select = ctk.CTkLabel(self.inputs_frame, text="🏁 Select Circuit / Mode", font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
            lbl_select.pack(fill="x", pady=(4, 2), padx=4)
            self.track_mode_var = ctk.StringVar(value=dropdown_values[0])
            self.track_dropdown = ctk.CTkComboBox(
                self.inputs_frame,
                values=dropdown_values,
                variable=self.track_mode_var,
                command=self._on_track_mode_changed,
                font=ctk.CTkFont(size=11, weight="bold"),
                dropdown_font=ctk.CTkFont(size=11),
                height=32,
                state="readonly",
                fg_color="#1a1a2e",
                border_color="#16213e",
                button_color="#0f3460",
                button_hover_color="#1a508b",
                dropdown_fg_color="#16213e",
                dropdown_hover_color="#1a508b",
            )
            self.track_dropdown.pack(fill="x", pady=(0, 8), padx=4)
        else:
            lbl_select = tk.Label(self.inputs_frame, text="🏁 Select Circuit / Mode", fg="#ffffff", bg="#2d2d2d", font=("Arial", 10, "bold"), anchor="w")
            lbl_select.pack(fill="x", pady=(4, 2), padx=4)
            self.track_mode_var = tk.StringVar(value=dropdown_values[0])
            self.track_dropdown = tk.OptionMenu(
                self.inputs_frame,
                self.track_mode_var,
                *dropdown_values,
                command=self._on_track_mode_changed,
            )
            self.track_dropdown.configure(bg="#1a1a2e", fg="#ffffff", font=("Arial", 9, "bold"))
            self.track_dropdown.pack(fill="x", pady=(0, 8), padx=4)

        self.entries = {}

        # Parameter groups
        groups = [
            ("🏎️ Track Geometry", [
                ("num_straights", "Number of Straights", "4", "cnt"),
                ("straight_length", "Straight Length", "100.0", "m"),
                ("num_turns", "Number of Turns", "4", "cnt"),
                ("turn_radius", "Turn Radius", "15.0", "m"),
                ("turn_angle", "Turn Angle", "90.0", "deg"),
                ("num_laps", "Total Laps", "10", "laps"),
            ]),
            ("⚡ Battery & Thermal", [
                ("v_pack", "Nominal Pack Voltage", "300.0", "V"),
                ("capacity_ah", "Pack Capacity", "15.0", "Ah"),
                ("r_int", "Internal Resistance", "0.05", "Ω"),
                ("bat_mass", "Battery Pack Mass", "35.0", "kg"),
                ("t_ambient", "Ambient Temp", "25.0", "°C"),
            ]),
            ("🚘 Vehicle Dynamics", [
                ("mass", "Vehicle + Driver Mass", "250.0", "kg"),
                ("mu", "Tire Friction (μ)", "1.2", "coef"),
                ("p_max_kw", "Max Motor Power", "80.0", "kW"),
                ("cd_a", "Aero Drag (Cd*A)", "1.0", "m²"),
                ("c_rr", "Rolling Resistance", "0.015", "coef"),
            ]),
        ]

        # Track geometry keys — these get locked when a preset is selected
        self._track_geometry_keys = ["num_straights", "straight_length", "num_turns", "turn_radius", "turn_angle"]

        for group_title, items in groups:
            if USE_CTK:
                lbl_group = ctk.CTkLabel(self.inputs_frame, text=group_title, font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
                lbl_group.pack(fill="x", pady=(8, 4), padx=4)
            else:
                lbl_group = tk.Label(self.inputs_frame, text=group_title, fg="#ffffff", bg="#2d2d2d", font=("Arial", 10, "bold"), anchor="w")
                lbl_group.pack(fill="x", pady=(8, 4), padx=4)

            for key, label, default, unit in items:
                row_frame = ctk.CTkFrame(self.inputs_frame) if USE_CTK else tk.Frame(self.inputs_frame, bg="#2d2d2d")
                row_frame.pack(fill="x", pady=2, padx=4)

                if USE_CTK:
                    lbl = ctk.CTkLabel(row_frame, text=label, font=ctk.CTkFont(size=11), width=135, anchor="w")
                    lbl.pack(side="left", padx=2)
                    entry = ctk.CTkEntry(row_frame, width=80)
                    entry.insert(0, default)
                    entry.pack(side="left", padx=2)
                    unit_lbl = ctk.CTkLabel(row_frame, text=unit, font=ctk.CTkFont(size=10), fg_color="transparent")
                    unit_lbl.pack(side="left", padx=2)
                else:
                    lbl = tk.Label(row_frame, text=label, fg="#cccccc", bg="#2d2d2d", width=18, anchor="w", font=("Arial", 9))
                    lbl.pack(side="left", padx=2)
                    entry = tk.Entry(row_frame, width=10)
                    entry.insert(0, default)
                    entry.pack(side="left", padx=2)
                    unit_lbl = tk.Label(row_frame, text=unit, fg="#888888", bg="#2d2d2d", font=("Arial", 9))
                    unit_lbl.pack(side="left", padx=2)

                self.entries[key] = entry

        # Run Button at bottom of Inputs
        if USE_CTK:
            btn_run = ctk.CTkButton(self.inputs_frame, text="🚀 Run Simulation", command=self.run_sim, font=ctk.CTkFont(size=13, weight="bold"))
            btn_run.pack(fill="x", pady=12, padx=4)
        else:
            btn_run = tk.Button(self.inputs_frame, text="🚀 Run Simulation", command=self.run_sim, bg="#007acc", fg="#ffffff", font=("Arial", 10, "bold"))
            btn_run.pack(fill="x", pady=12, padx=4)

        # Build Performance Plots inside graphs_frame (stacked vertically for Left Panel)
        self.fig = Figure(figsize=(3.8, 6.5), facecolor="#1e1e1e")
        self.ax1 = self.fig.add_subplot(211)
        self.ax2 = self.fig.add_subplot(212)
        self.fig.tight_layout(pad=2.5)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graphs_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=2, pady=2)

        # --- Right Area: Summary Cards ---
        if USE_CTK:
            self.cards_frame = ctk.CTkFrame(content_area)
            self.cards_frame.pack(fill="x", pady=5)
        else:
            self.cards_frame = tk.Frame(content_area, bg="#1e1e1e")
            self.cards_frame.pack(fill="x", pady=5)

        self.cards = {}
        card_defs = [
            ("soc", "Capacity Left", "-- %", "#28a745"),
            ("temp", "Max Temp", "-- °C", "#ffc107"),
            ("energy", "Energy Consumed", "-- kWh", "#17a2b8"),
            ("time", "Total Run Time", "-- s", "#6c757d"),
            ("peak_i", "Peak Current", "-- A", "#dc3545"),
        ]

        for key, title, val, color in card_defs:
            if USE_CTK:
                card = ctk.CTkFrame(self.cards_frame)
                card.pack(side="left", expand=True, fill="both", padx=4, pady=4)
                t_lbl = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11), text_color="#aaaaaa")
                t_lbl.pack(pady=(5, 0))
                v_lbl = ctk.CTkLabel(card, text=val, font=ctk.CTkFont(size=15, weight="bold"), text_color=color)
                v_lbl.pack(pady=(0, 5))
            else:
                card = tk.Frame(self.cards_frame, bg="#2d2d2d", bd=1, relief="solid")
                card.pack(side="left", expand=True, fill="both", padx=4, pady=4)
                t_lbl = tk.Label(card, text=title, fg="#aaaaaa", bg="#2d2d2d", font=("Arial", 9))
                t_lbl.pack(pady=(5, 0))
                v_lbl = tk.Label(card, text=val, fg=color, bg="#2d2d2d", font=("Arial", 11, "bold"))
                v_lbl.pack(pady=(0, 5))

            self.cards[key] = v_lbl

        # --- Right Area: Main Bird's Eye View Track Frame (always visible) ---
        if USE_CTK:
            self.track_frame = ctk.CTkFrame(content_area)
            self.track_frame.pack(fill="both", expand=True, pady=5)
        else:
            self.track_frame = tk.Frame(content_area, bg="#1e1e1e")
            self.track_frame.pack(fill="both", expand=True, pady=5)

        self._build_track_view_widgets()

    def _build_track_view_widgets(self):
        """Creates the info header banner and main Matplotlib Bird's Eye View canvas inside track_frame."""

        # --- Track Info Banner Header ---
        if USE_CTK:
            self.track_info_lbl = ctk.CTkLabel(
                self.track_frame,
                text="Total Lap Distance: -- m",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#17a2b8",
                justify="left",
                anchor="w",
            )
            self.track_info_lbl.pack(fill="x", pady=(6, 4), padx=12)
        else:
            self.track_info_lbl = tk.Label(
                self.track_frame,
                text="Total Lap Distance: -- m",
                fg="#17a2b8",
                bg="#2d2d2d",
                font=("Arial", 10, "bold"),
                justify="left",
                anchor="w",
            )
            self.track_info_lbl.pack(fill="x", pady=(6, 4), padx=12)

        # --- Main Track View Matplotlib Canvas ---
        self.fig_track = Figure(figsize=(8, 6), facecolor="#181818")
        self.ax_track = self.fig_track.add_subplot(111)
        self.fig_track.tight_layout(pad=1.0)

        self.canvas_track = FigureCanvasTkAgg(self.fig_track, master=self.track_frame)
        self.canvas_track.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)

    def _on_track_mode_changed(self, selected_value):
        """Called when the track dropdown selection changes."""
        new_mode = self._dropdown_key_map.get(selected_value, self.MODE_CUSTOM)

        if new_mode == self.track_mode:
            return

        if new_mode != self.MODE_CUSTOM and self.track_mode == self.MODE_CUSTOM:
            # Switching FROM custom TO preset — save current custom values
            self._saved_custom_values = {}
            for key in self._track_geometry_keys:
                self._saved_custom_values[key] = self.entries[key].get()

        self.track_mode = new_mode

        if new_mode == self.MODE_CUSTOM:
            # Restore custom values and re-enable fields
            self._set_track_fields_editable(True)
            if self._saved_custom_values:
                for key in self._track_geometry_keys:
                    entry = self.entries[key]
                    if USE_CTK:
                        entry.delete(0, "end")
                        entry.insert(0, self._saved_custom_values.get(key, ""))
                    else:
                        entry.delete(0, tk.END)
                        entry.insert(0, self._saved_custom_values.get(key, ""))
        else:
            # Fill in representative values from the F1 track and lock fields
            track_data = F1_TRACKS[new_mode]
            segments = track_data["segments"]
            num_straights = sum(1 for s in segments if s[0] == "straight")
            num_turns = sum(1 for s in segments if s[0] == "turn")
            straight_lengths = [s[1] for s in segments if s[0] == "straight"]
            turn_radii = [s[1] for s in segments if s[0] == "turn"]
            turn_angles = [s[2] for s in segments if s[0] == "turn"]

            avg_straight = sum(straight_lengths) / max(1, len(straight_lengths))
            avg_radius = sum(turn_radii) / max(1, len(turn_radii))
            avg_angle = sum(turn_angles) / max(1, len(turn_angles))

            preset_values = {
                "num_straights": str(num_straights),
                "straight_length": f"{avg_straight:.1f}",
                "num_turns": str(num_turns),
                "turn_radius": f"{avg_radius:.1f}",
                "turn_angle": f"{avg_angle:.1f}",
            }

            for key in self._track_geometry_keys:
                entry = self.entries[key]
                if USE_CTK:
                    entry.configure(state="normal")
                    entry.delete(0, "end")
                    entry.insert(0, preset_values.get(key, ""))
                    entry.configure(state="disabled")
                else:
                    entry.configure(state="normal")
                    entry.delete(0, tk.END)
                    entry.insert(0, preset_values.get(key, ""))
                    entry.configure(state="disabled", disabledforeground="#666666")

        # Re-run sim & update track view
        self.run_sim()

    def _set_track_fields_editable(self, editable):
        """Enable or disable the track geometry input fields."""
        for key in self._track_geometry_keys:
            entry = self.entries[key]
            if USE_CTK:
                entry.configure(state="normal" if editable else "disabled")
            else:
                entry.configure(state="normal" if editable else "disabled")

    def toggle_inputs(self):
        """Toggles between showing Input Parameters and Performance Graphs in the Left Panel."""
        if self.inputs_visible:
            # Hide Inputs, Show Performance Graphs in Left Panel
            self.inputs_frame.pack_forget()
            self.graphs_frame.pack(fill="both", expand=True, padx=2, pady=2)
            if USE_CTK:
                self.btn_toggle.configure(text="📈 Performance Graphs  ▲ (Click for Inputs)", fg_color="#28a745", hover_color="#1e7e34")
            else:
                self.btn_toggle.configure(text="📈 Performance Graphs  ▲ (Click for Inputs)", bg="#28a745")
            self.inputs_visible = False
        else:
            # Show Inputs, Hide Performance Graphs in Left Panel
            self.graphs_frame.pack_forget()
            self.inputs_frame.pack(fill="both", expand=True, padx=2, pady=2)
            if USE_CTK:
                self.btn_toggle.configure(text="⚙️ Input Parameters  ▲ (Click for Graphs)", fg_color="#1f538d", hover_color="#14375e")
            else:
                self.btn_toggle.configure(text="⚙️ Input Parameters  ▲ (Click for Graphs)", bg="#007acc")
            self.inputs_visible = True

    def _get_current_track_coords(self):
        """Returns (x_coords, y_coords, total_len, track_label, info_text, segments_or_none)."""
        if self.track_mode != self.MODE_CUSTOM:
            # F1 preset track
            track_data = F1_TRACKS[self.track_mode]
            segments = track_data["segments"]
            x_coords, y_coords, total_len = BatterySimulator.get_track_coordinates_from_segments(segments)
            track_label = f"{track_data['flag']} {track_data['name']}"
            info_text = get_track_info_text(self.track_mode)
            return x_coords, y_coords, total_len, track_label, info_text, segments
        else:
            # Custom track — use the old parameter-based approach
            try:
                get_val = lambda k: float(self.entries[k].get())
                track_config = {
                    'num_straights': int(get_val('num_straights')),
                    'straight_length': get_val('straight_length'),
                    'num_turns': int(get_val('num_turns')),
                    'turn_radius': get_val('turn_radius'),
                    'turn_angle': get_val('turn_angle'),
                    'num_laps': int(get_val('num_laps')),
                }
            except (ValueError, tk.TclError):
                return None, None, 0, "", "", None

            sim = BatterySimulator(track_config=track_config)
            x_coords, y_coords, total_len = sim.get_track_coordinates()
            info_text = f"Custom Track\nLength: {total_len:,.0f} m   |   Turns: {track_config['num_turns']}"
            return x_coords, y_coords, total_len, "Custom Track", info_text, None

    def draw_track_view(self):
        """Draws the bird's eye view track layout with realistic road-style rendering."""
        x_coords, y_coords, total_len, track_label, info_text, segments = self._get_current_track_coords()

        if x_coords is None or not x_coords:
            return

        self.track_info_lbl.configure(text=info_text)

        self.ax_track.clear()
        self.ax_track.set_facecolor("#181818")

        # Convert to numpy for efficient processing
        xs = np.array(x_coords)
        ys = np.array(y_coords)

        # --- Compute track normals for edge lines & curb markers ---
        # Tangent vectors (forward differences, wrapped)
        dx = np.diff(xs, append=xs[0])
        dy = np.diff(ys, append=ys[0])
        lengths = np.sqrt(dx**2 + dy**2)
        lengths[lengths < 1e-9] = 1e-9
        tx = dx / lengths
        ty = dy / lengths

        # Normal vectors (perpendicular to tangent, pointing left)
        nx = -ty
        ny = tx

        # --- Determine scale-adaptive line widths ---
        x_range = xs.max() - xs.min()
        y_range = ys.max() - ys.min()
        track_extent = max(x_range, y_range, 1.0)
        # Scale the road width relative to the track extent
        road_half_width = track_extent * 0.012
        edge_offset = road_half_width * 1.05

        # Build edge line coordinates
        left_xs = xs + nx * edge_offset
        left_ys = ys + ny * edge_offset
        right_xs = xs - nx * edge_offset
        right_ys = ys - ny * edge_offset

        # --- Draw track layers (bottom to top) ---

        # 1. Track surface shadow/glow (subtle outer glow)
        self.ax_track.plot(xs, ys, color="#0a0a0a", linewidth=road_half_width * 0.65, solid_capstyle="round", zorder=1)

        # 2. Main asphalt ribbon
        self.ax_track.plot(xs, ys, color="#3a3a3a", linewidth=road_half_width * 0.5, solid_capstyle="round", zorder=2)

        # 3. White edge lines
        self.ax_track.plot(left_xs, left_ys, color="#ffffff", linewidth=0.6, alpha=0.7, zorder=3)
        self.ax_track.plot(right_xs, right_ys, color="#ffffff", linewidth=0.6, alpha=0.7, zorder=3)

        # 4. Racing line (center, subtle)
        self.ax_track.plot(xs, ys, color="#00e676", linewidth=0.5, alpha=0.25, linestyle="--", zorder=4)

        # 5. Curb markers at turn entries (red-white on inside of turns)
        if segments is not None:
            self._draw_curb_markers(xs, ys, nx, ny, segments, road_half_width, zorder=5)

        # 6. Start/Finish line
        self._draw_start_finish(xs, ys, nx, ny, road_half_width, zorder=6)

        # 7. Track name label
        self.ax_track.text(
            0.03, 0.97, track_label,
            transform=self.ax_track.transAxes,
            color="#ffffff",
            fontsize=9,
            fontweight="bold",
            verticalalignment="top",
            alpha=0.75,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#000000", alpha=0.4, edgecolor="none"),
            zorder=10,
        )

        # --- Remove all graph elements ---
        self.ax_track.set_aspect("equal", adjustable="box")
        self.ax_track.axis("off")

        # Add a small margin
        margin = track_extent * 0.08
        self.ax_track.set_xlim(xs.min() - margin, xs.max() + margin)
        self.ax_track.set_ylim(ys.min() - margin, ys.max() + margin)

        self.fig_track.tight_layout(pad=0.5)
        self.canvas_track.draw()

    def _draw_start_finish(self, xs, ys, nx, ny, road_half_width, zorder=6):
        """Draws a bold red start/finish line perpendicular to the track at the first point."""
        sf_x = xs[0]
        sf_y = ys[0]
        sf_nx = nx[0]
        sf_ny = ny[0]

        # Perpendicular line endpoints
        offset = road_half_width * 1.3
        x1 = sf_x + sf_nx * offset
        y1 = sf_y + sf_ny * offset
        x2 = sf_x - sf_nx * offset
        y2 = sf_y - sf_ny * offset

        self.ax_track.plot([x1, x2], [y1, y2], color="#ff1744", linewidth=2.5, zorder=zorder, solid_capstyle="butt")

        # Checkered flag emoji label
        self.ax_track.annotate(
            "🏁",
            xy=(sf_x, sf_y),
            xytext=(sf_x + sf_nx * offset * 2.5, sf_y + sf_ny * offset * 2.5),
            fontsize=12,
            ha="center", va="center",
            color="#ffffff",
            zorder=zorder + 1,
        )

    def _draw_curb_markers(self, xs, ys, nx, ny, segments, road_half_width, zorder=5):
        """Draws red-white curb markings at turn locations along the inside of the curve."""
        # Identify which coordinate indices correspond to turn segments
        idx = 0
        n_total = len(xs)

        for seg in segments:
            if seg[0] == "straight":
                num_pts = max(5, int(seg[1] / 8.0))
                idx += num_pts
            elif seg[0] == "turn":
                angle_deg = seg[2]
                direction = seg[3]
                num_pts = max(8, int(angle_deg / 3.0))

                # Draw curbs every few points on the inside
                inside_sign = 1.0 if direction == "right" else -1.0
                curb_offset = road_half_width * 0.95

                for i in range(0, num_pts, 3):
                    ci = (idx + i) % n_total
                    ci_next = (idx + i + 1) % n_total

                    cx1 = xs[ci] - inside_sign * nx[ci] * curb_offset
                    cy1 = ys[ci] - inside_sign * ny[ci] * curb_offset
                    cx2 = xs[ci_next] - inside_sign * nx[ci_next] * curb_offset
                    cy2 = ys[ci_next] - inside_sign * ny[ci_next] * curb_offset

                    color = "#ff1744" if (i // 3) % 2 == 0 else "#ffffff"
                    self.ax_track.plot([cx1, cx2], [cy1, cy2], color=color, linewidth=2.0, solid_capstyle="butt", zorder=zorder)

                idx += num_pts

    def run_sim(self):
        try:
            get_val = lambda k: float(self.entries[k].get())
            
            # Battery & vehicle configs are always from entries
            battery_config = {
                'v_pack': get_val('v_pack'),
                'capacity_ah': get_val('capacity_ah'),
                'r_int': get_val('r_int'),
                'bat_mass': get_val('bat_mass'),
                't_ambient': get_val('t_ambient'),
            }
            vehicle_config = {
                'mass': get_val('mass'),
                'mu': get_val('mu'),
                'p_max_kw': get_val('p_max_kw'),
                'cd_a': get_val('cd_a'),
                'c_rr': get_val('c_rr'),
            }

            num_laps = int(get_val('num_laps'))

            if self.track_mode != self.MODE_CUSTOM:
                # F1 preset — use segment-aware simulation
                track_data = F1_TRACKS[self.track_mode]
                segments = track_data["segments"]
                # For segment sim, we still need a track_config for num_laps
                track_config = {
                    'num_straights': 1,
                    'straight_length': 1,
                    'num_turns': 1,
                    'turn_radius': 1,
                    'turn_angle': 1,
                    'num_laps': num_laps,
                }
                sim = BatterySimulator(track_config, vehicle_config, battery_config)
                res = sim.run_simulation_from_segments(segments)
            else:
                # Custom track — use the original simulation
                track_config = {
                    'num_straights': int(get_val('num_straights')),
                    'straight_length': get_val('straight_length'),
                    'num_turns': int(get_val('num_turns')),
                    'turn_radius': get_val('turn_radius'),
                    'turn_angle': get_val('turn_angle'),
                    'num_laps': num_laps,
                }
                sim = BatterySimulator(track_config, vehicle_config, battery_config)
                res = sim.run_simulation()

        except (ValueError, tk.TclError):
            messagebox.showerror("Input Error", "Please enter valid numeric values for all parameters.")
            return

        # Update Summary Cards safely across both CustomTkinter and standard Tkinter
        self.cards["soc"].configure(text=f"{res['final_soc_pct']:.1f}% ({res['final_capacity_ah']:.2f} Ah)")
        
        temp_color = "#dc3545" if res['final_temp_c'] > 60 else ("#ffc107" if res['final_temp_c'] > 45 else "#28a745")
        if USE_CTK:
            self.cards["temp"].configure(text=f"{res['final_temp_c']:.1f} °C", text_color=temp_color)
        else:
            self.cards["temp"].configure(text=f"{res['final_temp_c']:.1f} °C", fg=temp_color)

        self.cards["energy"].configure(text=f"{res['total_energy_kwh']:.2f} kWh")
        self.cards["time"].configure(text=f"{res['total_time_s']:.1f} s ({res['lap_time_avg_s']:.1f} s/lap)")
        self.cards["peak_i"].configure(text=f"{res['peak_current_a']:.1f} A")

        # Update Main Performance Plots
        self.ax1.clear()
        self.ax2.clear()

        for ax in (self.ax1, self.ax2):
            ax.set_facecolor("#2b2b2b")
            ax.tick_params(colors="#ffffff")
            ax.xaxis.label.set_color("#ffffff")
            ax.yaxis.label.set_color("#ffffff")
            ax.title.set_color("#ffffff")
            for spine in ax.spines.values():
                spine.set_color("#555555")

        self.ax1.plot(res['time'], res['soc'], color="#00bc8c", linewidth=2)
        self.ax1.set_title("Battery State of Charge (%)")
        self.ax1.set_xlabel("Time (s)")
        self.ax1.set_ylabel("SOC (%)")
        self.ax1.grid(True, linestyle="--", alpha=0.3)

        self.ax2.plot(res['time'], res['temp'], color="#e74c3c", linewidth=2)
        self.ax2.axhline(60, color="#f39c12", linestyle=":", label="60°C Limit")
        self.ax2.set_title("Battery Pack Temperature (°C)")
        self.ax2.set_xlabel("Time (s)")
        self.ax2.set_ylabel("Temp (°C)")
        self.ax2.legend(facecolor="#2b2b2b", labelcolor="#ffffff")
        self.ax2.grid(True, linestyle="--", alpha=0.3)

        self.fig.tight_layout()
        self.canvas.draw()

        # Always update track view (now permanently visible in main right area)
        self.draw_track_view()


def main():
    if USE_CTK:
        root = ctk.CTk()
    else:
        root = tk.Tk()

    app = BatteryApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
