import sys
import math
import tkinter as tk
from tkinter import messagebox
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

try:
    import customtkinter as ctk
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    USE_CTK = True
except ImportError:
    USE_CTK = False

from battery_model import BatterySimulator


class BatteryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Formula SAE - Battery Capacity & Thermal Model")
        self.root.geometry("1280x850")

        if not USE_CTK:
            self.root.configure(bg="#1e1e1e")

        self.inputs_visible = True
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

            # Input Parameters Header Button (Clickable header button to show/hide inputs)
            self.btn_toggle = ctk.CTkButton(
                self.left_panel,
                text="⚙️ Input Parameters  ▲ (Click to Hide)",
                command=self.toggle_inputs,
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color="#1f538d",
                hover_color="#14375e",
                height=36
            )
            self.btn_toggle.pack(fill="x", padx=5, pady=(5, 5))

            # Sub-frame 1: Inputs Scrollable Frame
            self.inputs_frame = ctk.CTkScrollableFrame(self.left_panel)
            self.inputs_frame.pack(fill="both", expand=True, padx=2, pady=2)

            # Sub-frame 2: Bird's Eye View Track Frame (hidden initially)
            self.track_frame = ctk.CTkFrame(self.left_panel)

            # Right Content Area (Dashboard & Performance Plots)
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
                text="⚙️ Input Parameters  ▲ (Click to Hide)",
                command=self.toggle_inputs,
                bg="#007acc",
                fg="#ffffff",
                font=("Arial", 10, "bold"),
                height=2
            )
            self.btn_toggle.pack(fill="x", padx=5, pady=(5, 5))

            self.inputs_frame = tk.Frame(self.left_panel, bg="#2d2d2d")
            self.inputs_frame.pack(fill="both", expand=True, padx=2, pady=2)

            self.track_frame = tk.Frame(self.left_panel, bg="#2d2d2d")

            content_area = tk.Frame(self.main_container, bg="#1e1e1e")
            content_area.pack(side="right", fill="both", expand=True, padx=5, pady=5)

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

        # Build Track View Widgets inside track_frame
        self._build_track_view_widgets()

        # Right Summary Cards Container
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

        # Main Performance Plots Canvas (using Figure directly to prevent memory leaks)
        if USE_CTK:
            plot_frame = ctk.CTkFrame(content_area)
            plot_frame.pack(fill="both", expand=True, pady=5)
        else:
            plot_frame = tk.Frame(content_area, bg="#1e1e1e")
            plot_frame.pack(fill="both", expand=True, pady=5)

        self.fig = Figure(figsize=(9, 4), facecolor="#1e1e1e")
        self.ax1 = self.fig.add_subplot(121)
        self.ax2 = self.fig.add_subplot(122)
        self.fig.tight_layout(pad=3.0)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _build_track_view_widgets(self):
        """Creates the Matplotlib Bird's Eye View track preview inside track_frame"""
        if USE_CTK:
            title_lbl = ctk.CTkLabel(self.track_frame, text="🗺️ Bird's Eye View - Track Layout", font=ctk.CTkFont(size=13, weight="bold"))
            title_lbl.pack(pady=5)
            self.track_info_lbl = ctk.CTkLabel(self.track_frame, text="Total Lap Distance: -- m", font=ctk.CTkFont(size=11), text_color="#17a2b8")
            self.track_info_lbl.pack(pady=(0, 5))
        else:
            title_lbl = tk.Label(self.track_frame, text="🗺️ Bird's Eye View - Track Layout", fg="#ffffff", bg="#2d2d2d", font=("Arial", 10, "bold"))
            title_lbl.pack(pady=5)
            self.track_info_lbl = tk.Label(self.track_frame, text="Total Lap Distance: -- m", fg="#17a2b8", bg="#2d2d2d", font=("Arial", 9))
            self.track_info_lbl.pack(pady=(0, 5))

        self.fig_track = Figure(figsize=(4, 5), facecolor="#1e1e1e")
        self.ax_track = self.fig_track.add_subplot(111)
        self.fig_track.tight_layout(pad=2.0)
        
        self.canvas_track = FigureCanvasTkAgg(self.fig_track, master=self.track_frame)
        self.canvas_track.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)

    def toggle_inputs(self):
        """Toggles between showing Input Parameters and showing Bird's Eye View track map."""
        if self.inputs_visible:
            # Hide Inputs, Show Track View
            self.inputs_frame.pack_forget()
            self.track_frame.pack(fill="both", expand=True, padx=2, pady=2)
            if USE_CTK:
                self.btn_toggle.configure(text="⚙️ Input Parameters  ▼ (Click to Show)", fg_color="#28a745", hover_color="#1e7e34")
            else:
                self.btn_toggle.configure(text="⚙️ Input Parameters  ▼ (Click to Show)", bg="#28a745")
            self.inputs_visible = False
            self.draw_track_view()
        else:
            # Show Inputs, Hide Track View
            self.track_frame.pack_forget()
            self.inputs_frame.pack(fill="both", expand=True, padx=2, pady=2)
            if USE_CTK:
                self.btn_toggle.configure(text="⚙️ Input Parameters  ▲ (Click to Hide)", fg_color="#1f538d", hover_color="#14375e")
            else:
                self.btn_toggle.configure(text="⚙️ Input Parameters  ▲ (Click to Hide)", bg="#007acc")
            self.inputs_visible = True

    def draw_track_view(self):
        """Draws the bird's eye view track layout based on current inputs."""
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
        except ValueError:
            return

        sim = BatterySimulator(track_config=track_config)
        x_coords, y_coords, total_len = sim.get_track_coordinates()

        if not x_coords:
            return

        self.track_info_lbl.configure(text=f"Total Lap Distance: {total_len:.1f} m")

        self.ax_track.clear()
        self.ax_track.set_facecolor("#2b2b2b")

        # Plot track path
        self.ax_track.plot(x_coords, y_coords, color="#00e676", linewidth=3, label="Track Layout")
        
        # Start/Finish line marker at (0,0)
        self.ax_track.plot(x_coords[0], y_coords[0], marker="o", markersize=8, color="#ff1744", label="Start / Finish")
        self.ax_track.text(x_coords[0] + 2, y_coords[0] + 2, "Start 🏁", color="#ff1744", fontsize=9, weight="bold")

        self.ax_track.set_title("Track Layout (2D Bird's Eye)", color="#ffffff", fontsize=10)
        self.ax_track.set_xlabel("X Distance (m)", color="#ffffff", fontsize=8)
        self.ax_track.set_ylabel("Y Distance (m)", color="#ffffff", fontsize=8)
        self.ax_track.tick_params(colors="#ffffff", labelsize=8)
        self.ax_track.grid(True, linestyle=":", alpha=0.4)
        self.ax_track.set_aspect("equal", adjustable="box")
        self.ax_track.legend(facecolor="#2b2b2b", labelcolor="#ffffff", fontsize=7, loc="upper right")

        self.fig_track.tight_layout()
        self.canvas_track.draw()

    def run_sim(self):
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
        except ValueError:
            messagebox.showerror("Input Error", "Please enter valid numeric values for all parameters.")
            return

        sim = BatterySimulator(track_config, vehicle_config, battery_config)
        res = sim.run_simulation()

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

        # Update track view if currently visible
        if not self.inputs_visible:
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
