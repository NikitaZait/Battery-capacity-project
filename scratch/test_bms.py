import sys, os, math
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from battery_model import BatterySimulator

# Test Thermal Overheat run (Light mass pack bat_mass=8.0, t_ambient=35.0)
sim_hot = BatterySimulator(battery_config={'capacity_ah': 30.0, 'bat_mass': 8.0, 'r_int': 0.05, 't_ambient': 35.0, 'h_cooling': 2.0}, track_config={'num_laps': 10})
res_hot = sim_hot.run_simulation()
print("Hot run time:", res_hot['total_time_s'], "Final Temp:", res_hot['final_temp_c'])
print("Hot BMS Activated:", res_hot['bms_activated'])
print("Reason:", res_hot['bms_reason'])
print("Type:", res_hot['bms_reason_type'])
print("Stopped at Lap:", res_hot['stopped_lap'], "of", res_hot['total_laps_requested'])
