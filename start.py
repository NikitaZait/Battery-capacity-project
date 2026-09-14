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
        self.pending_track_mode = self.MODE_CUSTOM
        self._saved_custom_values = {}  # store custom field values when switching to preset

        # Cached track data for lightweight, zero-lag animation
        self.cached_x_coords = None
        self.cached_y_coords = None
        self.cached_cum_lens = None
        self.cached_total_len = 0.0
        self.cached_track_extent = 1.0

        # Real-time car animation state
        self.is_animating = False
        self.anim_idx = 0
        self.anim_speed_val = 5.0
        self.anim_timer_id = None
        self.sim_res = None

        self.car_dot = None
        self.car_glow = None
        self.car_arrow = None
        self.car_trail = None
        self.trail_x_coords = []
        self.trail_y_coords = []

        self.graph_line_soc = None
        self.graph_head_soc = None
        self.graph_line_temp = None
        self.graph_head_temp = None

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

        # Build Performance Plots & BMS Banner inside graphs_frame (Left Panel)
        if USE_CTK:
            self.bms_banner_frame = ctk.CTkFrame(self.graphs_frame, fg_color="#3d0c0c", border_color="#ff1744", border_width=2)
            self.bms_banner_frame.pack(fill="x", padx=4, pady=(4, 2))
            self.bms_lbl_title = ctk.CTkLabel(self.bms_banner_frame, text="⚠️ BMS System Status", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ff1744")
            self.bms_lbl_title.pack(anchor="w", padx=8, pady=(4, 1))
            self.bms_lbl_msg = ctk.CTkLabel(self.bms_banner_frame, text="", font=ctk.CTkFont(size=10), text_color="#ffffff", justify="left", anchor="w")
            self.bms_lbl_msg.pack(anchor="w", padx=8, pady=(0, 6))
        else:
            self.bms_banner_frame = tk.Frame(self.graphs_frame, bg="#3d0c0c", bd=2, relief="solid")
            self.bms_banner_frame.pack(fill="x", padx=4, pady=(4, 2))
            self.bms_lbl_title = tk.Label(self.bms_banner_frame, text="⚠️ BMS System Status", fg="#ff1744", bg="#3d0c0c", font=("Arial", 10, "bold"), anchor="w")
            self.bms_lbl_title.pack(anchor="w", padx=8, pady=(4, 1))
            self.bms_lbl_msg = tk.Label(self.bms_banner_frame, text="", fg="#ffffff", bg="#3d0c0c", font=("Arial", 9), justify="left", anchor="w")
            self.bms_lbl_msg.pack(anchor="w", padx=8, pady=(0, 6))

        self.fig = Figure(figsize=(3.8, 5.5), facecolor="#1e1e1e")
        self.ax1 = self.fig.add_subplot(211)
        self.ax2 = self.fig.add_subplot(212)
        self.fig.tight_layout(pad=2.2)

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
        """Creates the info header banner, playback controls bar, and main Matplotlib Bird's Eye View canvas inside track_frame."""

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
            self.track_info_lbl.pack(fill="x", pady=(6, 2), padx=12)

            # --- Playback Controls Bar ---
            self.controls_frame = ctk.CTkFrame(self.track_frame, fg_color="#1f1f2e", height=42)
            self.controls_frame.pack(fill="x", padx=8, pady=(2, 6))

            self.btn_play = ctk.CTkButton(
                self.controls_frame,
                text="⏸️ Pause",
                width=85,
                height=30,
                command=self.toggle_play_pause,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#28a745",
                hover_color="#1e7e34",
            )
            self.btn_play.pack(side="left", padx=(8, 4), pady=5)

            self.btn_reset = ctk.CTkButton(
                self.controls_frame,
                text="🔄 Reset",
                width=75,
                height=30,
                command=self.reset_animation,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#495057",
                hover_color="#343a40",
            )
            self.btn_reset.pack(side="left", padx=4, pady=5)

            self.btn_finish = ctk.CTkButton(
                self.controls_frame,
                text="⏩ Finish",
                width=75,
                height=30,
                command=self.finish_animation,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#17a2b8",
                hover_color="#138496",
            )
            self.btn_finish.pack(side="left", padx=4, pady=5)

            lbl_speed = ctk.CTkLabel(self.controls_frame, text="⚡ Speed:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#cccccc")
            lbl_speed.pack(side="left", padx=(10, 2), pady=5)

            self.speed_var = ctk.StringVar(value="5x")
            self.speed_dropdown = ctk.CTkComboBox(
                self.controls_frame,
                values=["1x", "2x", "5x", "10x", "20x"],
                variable=self.speed_var,
                command=self.on_speed_changed,
                width=65,
                height=30,
                state="readonly",
                font=ctk.CTkFont(size=11, weight="bold"),
            )
            self.speed_dropdown.pack(side="left", padx=2, pady=5)

            self.lbl_telemetry_live = ctk.CTkLabel(
                self.controls_frame,
                text="🏎️ Lap 1/10  |  ⏱️ 0.0 s  |  📏 0.00 km  |  ⚡ 70 km/h  |  🔋 SOC: 100.0%  |  🌡️ 25.0°C",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#00e676",
                anchor="e",
            )
            self.lbl_telemetry_live.pack(side="right", padx=(10, 12), pady=5)

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
            self.track_info_lbl.pack(fill="x", pady=(6, 2), padx=12)

            self.controls_frame = tk.Frame(self.track_frame, bg="#1f1f2e")
            self.controls_frame.pack(fill="x", padx=8, pady=(2, 6))

            self.btn_play = tk.Button(
                self.controls_frame,
                text="⏸️ Pause",
                width=9,
                command=self.toggle_play_pause,
                bg="#28a745",
                fg="#ffffff",
                font=("Arial", 9, "bold"),
            )
            self.btn_play.pack(side="left", padx=(8, 4), pady=5)

            self.btn_reset = tk.Button(
                self.controls_frame,
                text="🔄 Reset",
                width=8,
                command=self.reset_animation,
                bg="#495057",
                fg="#ffffff",
                font=("Arial", 9, "bold"),
            )
            self.btn_reset.pack(side="left", padx=4, pady=5)

            self.btn_finish = tk.Button(
                self.controls_frame,
                text="⏩ Finish",
                width=8,
                command=self.finish_animation,
                bg="#17a2b8",
                fg="#ffffff",
                font=("Arial", 9, "bold"),
            )
            self.btn_finish.pack(side="left", padx=4, pady=5)

            lbl_speed = tk.Label(self.controls_frame, text="⚡ Speed:", fg="#cccccc", bg="#1f1f2e", font=("Arial", 9, "bold"))
            lbl_speed.pack(side="left", padx=(10, 2), pady=5)

            self.speed_var = tk.StringVar(value="5x")
            self.speed_dropdown = tk.OptionMenu(
                self.controls_frame,
                self.speed_var,
                "1x", "2x", "5x", "10x", "20x",
                command=self.on_speed_changed,
            )
            self.speed_dropdown.configure(bg="#2d2d2d", fg="#ffffff", font=("Arial", 9, "bold"))
            self.speed_dropdown.pack(side="left", padx=2, pady=5)

            self.lbl_telemetry_live = tk.Label(
                self.controls_frame,
                text="🏎️ Lap 1/10  |  ⏱️ 0.0 s  |  📏 0.00 km  |  ⚡ 70 km/h  |  🔋 SOC: 100.0%  |  🌡️ 25.0°C",
                fg="#00e676",
                bg="#1f1f2e",
                font=("Arial", 9, "bold"),
                anchor="e",
            )
            self.lbl_telemetry_live.pack(side="right", padx=(10, 12), pady=5)

        # --- Main Track View Matplotlib Canvas ---
        self.fig_track = Figure(figsize=(8, 6), facecolor="#181818")
        self.ax_track = self.fig_track.add_subplot(111)
        self.fig_track.tight_layout(pad=1.0)

        self.canvas_track = FigureCanvasTkAgg(self.fig_track, master=self.track_frame)
        self.canvas_track.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)

    def _on_track_mode_changed(self, selected_value):
        """Called when the track dropdown selection changes. Updates UI parameter fields but defers simulation update until 'Run Simulation' is pressed."""
        new_mode = self._dropdown_key_map.get(selected_value, self.MODE_CUSTOM)

        if new_mode == self.pending_track_mode:
            return

        if new_mode != self.MODE_CUSTOM and self.pending_track_mode == self.MODE_CUSTOM:
            # Switching FROM custom TO preset — save current custom values
            self._saved_custom_values = {}
            for key in self._track_geometry_keys:
                self._saved_custom_values[key] = self.entries[key].get()

        self.pending_track_mode = new_mode

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
            info_text = f"🔧 Custom Track  |  Length: {total_len:,.0f} m"
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

        # Cache track arrays for lightweight, zero-allocation animation
        self.cached_x_coords = xs
        self.cached_y_coords = ys
        self.cached_total_len = total_len
        dxs = np.diff(xs)
        dys = np.diff(ys)
        seg_lens = np.hypot(dxs, dys)
        self.cached_cum_lens = np.insert(np.cumsum(seg_lens), 0, 0.0)

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
        self.cached_track_extent = track_extent
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

        # 8. Create Car Artists for real-time motion
        self.car_trail, = self.ax_track.plot([], [], color="#00e676", linewidth=2.0, alpha=0.55, zorder=18)
        self.car_glow, = self.ax_track.plot([], [], "o", color="#ff1744", markersize=16, alpha=0.35, zorder=19)
        self.car_dot, = self.ax_track.plot([], [], "o", color="#ff1744", markersize=9, markeredgecolor="#ffffff", markeredgewidth=1.2, zorder=20)
        self.car_arrow, = self.ax_track.plot([], [], color="#ffffff", linewidth=2.2, zorder=21)
        self.trail_x_coords = []
        self.trail_y_coords = []

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
        self.track_mode = self.pending_track_mode
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

        # Check BMS Shutdown Status
        bms_activated = res.get('bms_activated', False)
        bms_reason = res.get('bms_reason', '')
        bms_reason_type = res.get('bms_reason_type', 'none')
        stopped_lap = res.get('stopped_lap', 1)
        total_laps = res.get('total_laps_requested', num_laps)
        distance_km = res.get('distance_km', 0.0)

        # Update BMS Safety Alert Banner in Left Panel
        if bms_activated:
            if bms_reason_type == "temperature":
                title_text = "🔥 BMS Thermal Shutdown (T ≥ 60.0°C)"
            elif bms_reason_type == "voltage":
                title_text = "⚡ BMS Low-Voltage Shutdown (V < 2.5V)"
            elif bms_reason_type == "soc":
                title_text = "🪫 BMS Capacity Depletion (0% SOC)"
            else:
                title_text = "⚠️ BMS System Activated — Race Terminated"

            banner_bg = "#3d0c0c"
            banner_border = "#ff1744"
            msg_text = (
                f"You did not make it to finish!\n"
                f"• Stopped at Lap {stopped_lap} of {total_laps} ({distance_km:.2f} km driven)\n"
                f"• Trigger: {bms_reason}"
            )
            if USE_CTK:
                self.bms_banner_frame.configure(fg_color=banner_bg, border_color=banner_border)
                self.bms_lbl_title.configure(text=title_text, text_color="#ff1744")
                self.bms_lbl_msg.configure(text=msg_text, text_color="#ff8a80")
            else:
                self.bms_banner_frame.configure(bg=banner_bg)
                self.bms_lbl_title.configure(text=title_text, fg="#ff1744", bg=banner_bg)
                self.bms_lbl_msg.configure(text=msg_text, fg="#ff8a80", bg=banner_bg)
        else:
            title_text = "✅ Race Completed Successfully"
            banner_bg = "#0c2d1c"
            banner_border = "#28a745"
            msg_text = (
                f"Completed all {total_laps} Laps ({distance_km:.2f} km driven)\n"
                f"• Battery Pack voltage, SOC, and Temperature (< 60°C) remained OK."
            )
            if USE_CTK:
                self.bms_banner_frame.configure(fg_color=banner_bg, border_color=banner_border)
                self.bms_lbl_title.configure(text=title_text, text_color="#28a745")
                self.bms_lbl_msg.configure(text=msg_text, text_color="#a3e635")
            else:
                self.bms_banner_frame.configure(bg=banner_bg)
                self.bms_lbl_title.configure(text=title_text, fg="#28a745", bg=banner_bg)
                self.bms_lbl_msg.configure(text=msg_text, fg="#a3e635", bg=banner_bg)

        # Update Summary Cards safely
        if bms_activated:
            soc_card_text = f"{res['final_soc_pct']:.1f}% (DNF L{stopped_lap})" if bms_reason_type != "soc" else "0.0% (Cutoff L{stopped_lap})"
            soc_card_color = "#ff1744" if bms_reason_type == "soc" else "#ffc107"
            time_card_text = f"{res['total_time_s']:.1f} s (DNF Lap {stopped_lap})"
        else:
            soc_card_text = f"{res['final_soc_pct']:.1f}% ({res['final_capacity_ah']:.2f} Ah)"
            soc_card_color = "#28a745"
            time_card_text = f"{res['total_time_s']:.1f} s ({res['lap_time_avg_s']:.1f} s/lap)"

        if USE_CTK:
            self.cards["soc"].configure(text=soc_card_text, text_color=soc_card_color)
        else:
            self.cards["soc"].configure(text=soc_card_text, fg=soc_card_color)

        if bms_activated and bms_reason_type == "temperature":
            temp_text = f"{res['final_temp_c']:.1f} °C (FSAE 60°C Cutoff)"
            temp_color = "#ff1744"
        else:
            temp_text = f"{res['final_temp_c']:.1f} °C"
            temp_color = "#dc3545" if res['final_temp_c'] >= 60 else ("#ffc107" if res['final_temp_c'] > 45 else "#28a745")

        if USE_CTK:
            self.cards["temp"].configure(text=temp_text, text_color=temp_color)
        else:
            self.cards["temp"].configure(text=temp_text, fg=temp_color)

        self.cards["energy"].configure(text=f"{res['total_energy_kwh']:.2f} kWh")
        self.cards["time"].configure(text=time_card_text)
        self.cards["peak_i"].configure(text=f"{res['peak_current_a']:.1f} A")

        self.sim_res = res

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

        # Static background traces
        self.ax1.plot(res['time'], res['soc'], color="#3a3a3a", linestyle=":", linewidth=1.5, alpha=0.6)
        self.ax1.set_title("Battery State of Charge (%)")
        self.ax1.set_xlabel("Time (s)")
        self.ax1.set_ylabel("SOC (%)")
        self.ax1.grid(True, linestyle="--", alpha=0.3)

        self.ax2.plot(res['time'], res['temp'], color="#3a3a3a", linestyle=":", linewidth=1.5, alpha=0.6)
        self.ax2.axhline(60, color="#f39c12", linestyle=":", label="60°C Limit")
        self.ax2.set_title("Battery Pack Temperature (°C)")
        self.ax2.set_xlabel("Time (s)")
        self.ax2.set_ylabel("Temp (°C)")
        self.ax2.legend(facecolor="#2b2b2b", labelcolor="#ffffff")
        self.ax2.grid(True, linestyle="--", alpha=0.3)

        # Active dynamic real-time plot artists
        self.graph_line_soc, = self.ax1.plot([], [], color="#00bc8c", linewidth=2.2, zorder=5)
        self.graph_head_soc, = self.ax1.plot([], [], "o", color="#00e676", markersize=7, markeredgecolor="#ffffff", zorder=6)

        self.graph_line_temp, = self.ax2.plot([], [], color="#e74c3c", linewidth=2.2, zorder=5)
        self.graph_head_temp, = self.ax2.plot([], [], "o", color="#ff1744", markersize=7, markeredgecolor="#ffffff", zorder=6)

        max_t = max(1.0, max(res['time'])) if res['time'] else 1.0
        self.ax1.set_xlim(0, max_t)
        self.ax1.set_ylim(-2, 105)
        self.ax2.set_xlim(0, max_t)
        self.ax2.set_ylim(min(20.0, min(res['temp']) - 3), max(65.0, max(res['temp']) + 5))

        # Plot BMS Cutoff indicator line on graphs if activated
        if bms_activated and res['time']:
            stop_t = res['time'][-1]
            tag_label = "🔥 THERMAL 60°C" if bms_reason_type == "temperature" else ("⚡ VOLTAGE 2.5V" if bms_reason_type == "voltage" else "🪫 SOC 0%")
            
            self.ax1.axvline(stop_t, color="#ff1744", linestyle="--", linewidth=1.8, label="BMS Cutoff")
            self.ax1.annotate(
                f"⚠️ {tag_label}\nLap {stopped_lap}",
                xy=(stop_t, res['soc'][-1]),
                xytext=(stop_t * 0.82, max(15, res['soc'][-1] + 15)),
                arrowprops=dict(facecolor="#ff1744", shrink=0.05, width=1.5, headwidth=6),
                color="#ff1744", fontweight="bold", fontsize=8,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#1e1e1e", edgecolor="#ff1744", alpha=0.9)
            )
            self.ax2.axvline(stop_t, color="#ff1744", linestyle="--", linewidth=1.8, label="BMS Cutoff")
            self.ax2.annotate(
                f"⚠️ {tag_label}\nLap {stopped_lap}",
                xy=(stop_t, res['temp'][-1]),
                xytext=(stop_t * 0.82, max(30, res['temp'][-1] - 10)),
                arrowprops=dict(facecolor="#ff1744", shrink=0.05, width=1.5, headwidth=6),
                color="#ff1744", fontweight="bold", fontsize=8,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#1e1e1e", edgecolor="#ff1744", alpha=0.9)
            )

        self.fig.tight_layout()
        self.canvas.draw()

        # Update track view canvas and start real-time car animation
        self.draw_track_view()
        self.start_animation()

    def on_speed_changed(self, choice):
        """Called when speed multiplier option is selected."""
        try:
            val = float(choice.replace("x", ""))
            self.anim_speed_val = val
        except ValueError:
            self.anim_speed_val = 5.0

    def toggle_play_pause(self):
        """Toggles animation play/pause state."""
        if self.is_animating:
            self.is_animating = False
            if self.anim_timer_id is not None:
                self.root.after_cancel(self.anim_timer_id)
                self.anim_timer_id = None
            if USE_CTK:
                self.btn_play.configure(text="▶️ Play", fg_color="#1f538d", hover_color="#14375e")
            else:
                self.btn_play.configure(text="▶️ Play", bg="#007acc")
        else:
            if self.sim_res is None or not self.sim_res.get('time'):
                return
            if self.anim_idx >= len(self.sim_res['time']) - 1:
                self.anim_idx = 0
                self.trail_x_coords.clear()
                self.trail_y_coords.clear()
                self.render_frame_at_index(0)
            self.is_animating = True
            if USE_CTK:
                self.btn_play.configure(text="⏸️ Pause", fg_color="#28a745", hover_color="#1e7e34")
            else:
                self.btn_play.configure(text="⏸️ Pause", bg="#28a745")
            self.animate_frame()

    def reset_animation(self):
        """Resets car, telemetry, and graph playback to beginning (frame 0)."""
        if self.anim_timer_id is not None:
            self.root.after_cancel(self.anim_timer_id)
            self.anim_timer_id = None
        self.is_animating = False
        self.anim_idx = 0
        self.trail_x_coords.clear()
        self.trail_y_coords.clear()
        if USE_CTK:
            self.btn_play.configure(text="▶️ Play", fg_color="#1f538d", hover_color="#14375e")
        else:
            self.btn_play.configure(text="▶️ Play", bg="#007acc")
        self.render_frame_at_index(0)

    def finish_animation(self):
        """Instantly jumps playback to the final simulation frame."""
        if self.sim_res is None or not self.sim_res.get('time'):
            return

        if self.anim_timer_id is not None:
            self.root.after_cancel(self.anim_timer_id)
            self.anim_timer_id = None

        self.is_animating = False
        times = self.sim_res['time']
        self.anim_idx = len(times) - 1

        # Clear motion trail so no connecting line cuts across the circuit
        self.trail_x_coords.clear()
        self.trail_y_coords.clear()

        if USE_CTK:
            self.btn_play.configure(text="▶️ Play", fg_color="#1f538d", hover_color="#14375e")
        else:
            self.btn_play.configure(text="▶️ Play", bg="#007acc")

        self.render_frame_at_index(self.anim_idx)

    def start_animation(self):
        """Starts real-time playback from frame 0."""
        if self.anim_timer_id is not None:
            self.root.after_cancel(self.anim_timer_id)
            self.anim_timer_id = None
        self.anim_idx = 0
        self.trail_x_coords.clear()
        self.trail_y_coords.clear()
        self.render_frame_at_index(0)
        self.is_animating = True
        if USE_CTK:
            self.btn_play.configure(text="⏸️ Pause", fg_color="#28a745", hover_color="#1e7e34")
        else:
            self.btn_play.configure(text="⏸️ Pause", bg="#28a745")
        self.anim_timer_id = self.root.after(30, self.animate_frame)

    def render_frame_at_index(self, idx):
        """Renders car position, trail, telemetry, and graph traces for step index using cached track data."""
        if self.sim_res is None:
            return

        times = self.sim_res.get('time', [])
        if not times or idx < 0 or idx >= len(times):
            return

        t_curr = times[idx]
        soc_curr = self.sim_res['soc'][idx]
        temp_curr = self.sim_res['temp'][idx]
        dist_curr = self.sim_res['dist_m'][idx]
        dist_km = dist_curr / 1000.0

        total_len = self.cached_total_len or 1.0
        total_laps = self.sim_res.get('total_laps_requested', 10)
        lap_num = min(total_laps, int(dist_curr // max(1.0, total_len)) + 1)

        # Update live progress header label right above track
        telemetry_text = f"🏎️ Lap {lap_num}/{total_laps}  |  ⏱️ {t_curr:.1f} s  |  📏 {dist_km:.2f} km  |  ⚡ 70 km/h  |  🔋 SOC: {soc_curr:.1f}%  |  🌡️ {temp_curr:.1f}°C"
        self.lbl_telemetry_live.configure(text=telemetry_text)

        # Update Car Marker position on track canvas
        if self.cached_x_coords is not None and len(self.cached_x_coords) >= 2 and self.car_dot is not None:
            x_car, y_car, dx, dy, heading = BatterySimulator.get_car_position_at_distance(
                dist_curr, self.cached_x_coords, self.cached_y_coords, cum_lens=self.cached_cum_lens
            )
            self.car_dot.set_data([x_car], [y_car])
            self.car_glow.set_data([x_car], [y_car])

            # Direction arrow vector
            arrow_len = self.cached_track_extent * 0.035
            norm = math.hypot(dx, dy) or 1.0
            ax_x = x_car + (dx / norm) * arrow_len
            ax_y = y_car + (dy / norm) * arrow_len
            self.car_arrow.set_data([x_car, ax_x], [y_car, ax_y])

            # Motion trail: clear if jump is detected to prevent lines crossing the track
            if self.trail_x_coords:
                last_x = self.trail_x_coords[-1]
                last_y = self.trail_y_coords[-1]
                jump_dist = math.hypot(x_car - last_x, y_car - last_y)
                if jump_dist > max(30.0, self.cached_track_extent * 0.08):
                    self.trail_x_coords.clear()
                    self.trail_y_coords.clear()

            self.trail_x_coords.append(x_car)
            self.trail_y_coords.append(y_car)
            if len(self.trail_x_coords) > 18:
                self.trail_x_coords.pop(0)
                self.trail_y_coords.pop(0)
            self.car_trail.set_data(self.trail_x_coords, self.trail_y_coords)

        # Update dynamic moving graph lines
        if self.graph_line_soc and self.graph_head_soc:
            self.graph_line_soc.set_data(times[:idx+1], self.sim_res['soc'][:idx+1])
            self.graph_head_soc.set_data([t_curr], [soc_curr])

        if self.graph_line_temp and self.graph_head_temp:
            self.graph_line_temp.set_data(times[:idx+1], self.sim_res['temp'][:idx+1])
            self.graph_head_temp.set_data([t_curr], [temp_curr])

        self.canvas_track.draw_idle()
        if idx % 2 == 0 or idx == len(times) - 1:
            self.canvas.draw_idle()

    def animate_frame(self):
        """Main real-time playback loop step."""
        if not self.is_animating or self.sim_res is None:
            return

        times = self.sim_res.get('time', [])
        if not times or self.anim_idx >= len(times) - 1:
            self.is_animating = False
            if USE_CTK:
                self.btn_play.configure(text="▶️ Play", fg_color="#1f538d", hover_color="#14375e")
            else:
                self.btn_play.configure(text="▶️ Play", bg="#007acc")
            return

        step = max(1, int(round(self.anim_speed_val * 0.6)))
        self.anim_idx = min(len(times) - 1, self.anim_idx + step)

        self.render_frame_at_index(self.anim_idx)

        if self.anim_idx >= len(times) - 1:
            self.is_animating = False
            if USE_CTK:
                self.btn_play.configure(text="▶️ Play", fg_color="#1f538d", hover_color="#14375e")
            else:
                self.btn_play.configure(text="▶️ Play", bg="#007acc")
            return

        self.anim_timer_id = self.root.after(30, self.animate_frame)


def main():
    if USE_CTK:
        root = ctk.CTk()
    else:
        root = tk.Tk()

    app = BatteryApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
