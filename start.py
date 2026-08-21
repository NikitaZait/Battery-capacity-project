import sys
import tkinter as tk
from tkinter import messagebox
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

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
        self.root.geometry("1280x800")

        if not USE_CTK:
            self.root.configure(bg="#1e1e1e")

        self._build_ui()
        self.run_sim()

    def _build_ui(self):
        # Main layout container
        if USE_CTK:
            main_container = ctk.CTkFrame(self.root)
            main_container.pack(fill="both", expand=True, padx=10, pady=10)

            # Left Sidebar (Inputs)
            sidebar = ctk.CTkScrollableFrame(main_container, width=350, label_text="⚙️ Input Parameters")
            sidebar.pack(side="left", fill="y", padx=5, pady=5)

            # Right Content Area (Dashboard & Plots)
            content_area = ctk.CTkFrame(main_container)
            content_area.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        else:
            main_container = tk.Frame(self.root, bg="#1e1e1e")
            main_container.pack(fill="both", expand=True, padx=10, pady=10)

            sidebar = tk.Frame(main_container, bg="#2d2d2d", width=350)
            sidebar.pack(side="left", fill="y", padx=5, pady=5)

            content_area = tk.Frame(main_container, bg="#1e1e1e")
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
                ("t_ambient", "Ambient Temperature", "25.0", "°C"),
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
                lbl_group = ctk.CTkLabel(sidebar, text=group_title, font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
                lbl_group.pack(fill="x", pady=(10, 5), padx=5)
            else:
                lbl_group = tk.Label(sidebar, text=group_title, fg="#ffffff", bg="#2d2d2d", font=("Arial", 11, "bold"), anchor="w")
                lbl_group.pack(fill="x", pady=(10, 5), padx=5)

            for key, label, default, unit in items:
                row_frame = ctk.CTkFrame(sidebar) if USE_CTK else tk.Frame(sidebar, bg="#2d2d2d")
                row_frame.pack(fill="x", pady=2, padx=5)

                if USE_CTK:
                    lbl = ctk.CTkLabel(row_frame, text=label, font=ctk.CTkFont(size=11), width=140, anchor="w")
                    lbl.pack(side="left", padx=2)
                    entry = ctk.CTkEntry(row_frame, width=90)
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

        # Run Button
        if USE_CTK:
            btn_run = ctk.CTkButton(sidebar, text="🚀 Run Simulation", command=self.run_sim, font=ctk.CTkFont(size=14, weight="bold"))
            btn_run.pack(fill="x", pady=15, padx=5)
        else:
            btn_run = tk.Button(sidebar, text="🚀 Run Simulation", command=self.run_sim, bg="#007acc", fg="#ffffff", font=("Arial", 11, "bold"))
            btn_run.pack(fill="x", pady=15, padx=5)

        # Summary Cards Container
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
                v_lbl = ctk.CTkLabel(card, text=val, font=ctk.CTkFont(size=16, weight="bold"), text_color=color)
                v_lbl.pack(pady=(0, 5))
            else:
                card = tk.Frame(self.cards_frame, bg="#2d2d2d", bd=1, relief="solid")
                card.pack(side="left", expand=True, fill="both", padx=4, pady=4)
                t_lbl = tk.Label(card, text=title, fg="#aaaaaa", bg="#2d2d2d", font=("Arial", 9))
                t_lbl.pack(pady=(5, 0))
                v_lbl = tk.Label(card, text=val, fg=color, bg="#2d2d2d", font=("Arial", 12, "bold"))
                v_lbl.pack(pady=(0, 5))

            self.cards[key] = v_lbl

        # Plot Canvas
        if USE_CTK:
            plot_frame = ctk.CTkFrame(content_area)
            plot_frame.pack(fill="both", expand=True, pady=5)
        else:
            plot_frame = tk.Frame(content_area, bg="#1e1e1e")
            plot_frame.pack(fill="both", expand=True, pady=5)

        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(9, 4), facecolor="#1e1e1e")
        self.fig.tight_layout(pad=3.0)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

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

        # Update Summary Cards
        self.cards["soc"].configure(text=f"{res['final_soc_pct']:.1f}% ({res['final_capacity_ah']:.2f} Ah)")
        
        temp_color = "#dc3545" if res['final_temp_c'] > 60 else ("#ffc107" if res['final_temp_c'] > 45 else "#28a745")
        self.cards["temp"].configure(text=f"{res['final_temp_c']:.1f} °C", text_color=temp_color if USE_CTK else temp_color)
        
        self.cards["energy"].configure(text=f"{res['total_energy_kwh']:.2f} kWh")
        self.cards["time"].configure(text=f"{res['total_time_s']:.1f} s ({res['lap_time_avg_s']:.1f} s/lap)")
        self.cards["peak_i"].configure(text=f"{res['peak_current_a']:.1f} A")

        # Update Plots
        self.ax1.clear()
        self.ax2.clear()

        # Style plots for dark theme
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


def main():
    if USE_CTK:
        root = ctk.CTk()
    else:
        root = tk.Tk()

    app = BatteryApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
