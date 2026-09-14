import math
import numpy as np

class BatterySimulator:
    def __init__(self, track_config=None, vehicle_config=None, battery_config=None):
        track_config = track_config or {}
        vehicle_config = vehicle_config or {}
        battery_config = battery_config or {}

        # Track parameters
        self.num_straights = track_config.get('num_straights', 4)
        self.straight_length = track_config.get('straight_length', 100.0)  # meters
        self.num_turns = track_config.get('num_turns', 4)
        self.turn_radius = track_config.get('turn_radius', 15.0)  # meters
        self.turn_angle = track_config.get('turn_angle', 90.0)  # degrees
        self.num_laps = track_config.get('num_laps', 10)

        # Vehicle Dynamics
        self.mass = vehicle_config.get('mass', 250.0)  # kg (car + driver)
        self.mu = vehicle_config.get('mu', 1.2)  # tire friction coefficient
        self.p_max_kw = vehicle_config.get('p_max_kw', 80.0)  # kW max motor power
        self.cd_a = vehicle_config.get('cd_a', 1.0)  # m^2
        self.c_rr = vehicle_config.get('c_rr', 0.015)  # rolling resistance
        self.eta_drivetrain = vehicle_config.get('eta_drivetrain', 0.88)
        self.regen_efficiency = vehicle_config.get('regen_efficiency', 0.3)

        # Battery & Thermal
        self.v_pack = battery_config.get('v_pack', 300.0)  # Volts
        self.capacity_ah = battery_config.get('capacity_ah', 15.0)  # Ah
        self.r_int = battery_config.get('r_int', 0.05)  # Ohms
        self.bat_mass = battery_config.get('bat_mass', 35.0)  # kg
        self.c_p = battery_config.get('c_p', 900.0)  # J / (kg * K)
        self.t_ambient = battery_config.get('t_ambient', 25.0)  # deg C
        self.h_cooling = battery_config.get('h_cooling', 15.0)  # W / (m^2 * K)
        self.cooling_area = battery_config.get('cooling_area', 0.5)  # m^2

        self.g = 9.81
        self.air_density = 1.225  # kg/m^3

    def run_simulation(self, dt=0.05):
        """
        Simulates track run lap by lap with time step dt (seconds).
        Returns dictionary containing time series and summary metrics.
        """
        # Cornering velocity limit
        v_turn = math.sqrt(self.mu * self.g * self.turn_radius)
        
        # Turn arc length
        turn_arc_length = self.turn_radius * math.radians(self.turn_angle)
        
        time_points = [0.0]
        soc_points = [100.0]
        capacity_ah_points = [self.capacity_ah]
        temp_points = [self.t_ambient]
        current_points = [0.0]
        speed_points = [v_turn * 3.6]
        dist_points = [0.0]

        remaining_ah = self.capacity_ah
        current_temp = self.t_ambient
        current_time = 0.0
        peak_current = 0.0
        total_energy_kwh = 0.0
        total_dist_m = 0.0

        bms_activated = False
        bms_reason = ""
        bms_reason_type = "none"
        stopped_lap = self.num_laps
        min_cell_v_seen = 4.2
        n_cells_series = max(1.0, self.v_pack / 3.6)
        r_cell = self.r_int / n_cells_series

        p_max_watts = self.p_max_kw * 1000.0

        for lap in range(self.num_laps):
            if bms_activated:
                break
            num_segments = max(self.num_straights, self.num_turns)
            
            for seg in range(num_segments):
                if bms_activated:
                    break

                # 1. Turn Segment
                if seg < self.num_turns:
                    dist_in_turn = 0.0
                    v_current = v_turn
                    while dist_in_turn < turn_arc_length:
                        f_drag = 0.5 * self.air_density * self.cd_a * (v_current ** 2)
                        f_rr = self.mass * self.g * self.c_rr
                        f_res = f_drag + f_rr
                        
                        p_mech = f_res * v_current
                        p_elec = p_mech / self.eta_drivetrain
                        
                        i_bat = p_elec / self.v_pack if self.v_pack > 0 else 0.0
                        if i_bat > peak_current:
                            peak_current = i_bat
                        
                        ah_used = (i_bat * dt) / 3600.0
                        remaining_ah = max(0.0, remaining_ah - ah_used)
                        total_energy_kwh += (p_elec * dt) / (3600.0 * 1000.0)
                        
                        q_gen = (i_bat ** 2) * self.r_int
                        q_cool = self.h_cooling * self.cooling_area * (current_temp - self.t_ambient)
                        d_temp = ((q_gen - q_cool) * dt) / (self.bat_mass * self.c_p)
                        current_temp += d_temp
                        
                        d_dist = v_current * dt
                        dist_in_turn += d_dist
                        total_dist_m += d_dist
                        current_time += dt
                        
                        current_soc_pct = (remaining_ah / self.capacity_ah) * 100.0
                        soc_ratio = max(0.0, min(1.0, current_soc_pct / 100.0))
                        v_cell_ocv = 2.5 + 1.2 * soc_ratio + 0.1 * (soc_ratio ** 2)
                        v_cell_term = v_cell_ocv - i_bat * r_cell
                        if v_cell_term < min_cell_v_seen:
                            min_cell_v_seen = v_cell_term

                        time_points.append(current_time)
                        soc_points.append(current_soc_pct)
                        capacity_ah_points.append(remaining_ah)
                        temp_points.append(current_temp)
                        current_points.append(i_bat)
                        speed_points.append(v_current * 3.6)
                        dist_points.append(total_dist_m)

                        if current_temp >= 60.0:
                            bms_activated = True
                            bms_reason_type = "temperature"
                            bms_reason = f"Thermal Overheat: Pack temperature reached {current_temp:.1f}°C (FSAE limit: 60.0°C)"
                            stopped_lap = lap + 1
                            break
                        elif v_cell_term <= 2.5:
                            bms_activated = True
                            bms_reason_type = "voltage"
                            bms_reason = f"Cell terminal voltage dropped to {v_cell_term:.2f}V (minimum limit 2.5V)"
                            stopped_lap = lap + 1
                            break
                        elif remaining_ah <= 0.0001 or current_soc_pct <= 0.01:
                            bms_activated = True
                            bms_reason_type = "soc"
                            bms_reason = "Battery pack SOC depleted to 0.0%"
                            stopped_lap = lap + 1
                            break

                # 2. Straight Segment
                if seg < self.num_straights and not bms_activated:
                    dist_in_straight = 0.0
                    v_current = v_turn
                    a_brake = self.mu * self.g
                    
                    while dist_in_straight < self.straight_length:
                        remaining_dist = self.straight_length - dist_in_straight
                        a_brake_needed = (v_current**2 - v_turn**2) / (2 * max(0.001, remaining_dist))
                        is_braking = (a_brake_needed >= a_brake * 0.9) and (v_current > v_turn)
                        
                        f_drag = 0.5 * self.air_density * self.cd_a * (v_current ** 2)
                        f_rr = self.mass * self.g * self.c_rr
                        
                        if is_braking:
                            a_net = -a_brake
                            f_braking = self.mass * a_brake
                            p_regen_mech = f_braking * v_current
                            p_elec = -p_regen_mech * self.regen_efficiency
                            i_bat = p_elec / self.v_pack
                        else:
                            f_tractive_limit = self.mu * self.mass * self.g
                            f_power_limit = (p_max_watts * self.eta_drivetrain) / max(0.1, v_current)
                            f_tractive = min(f_tractive_limit, f_power_limit)
                            
                            f_net = f_tractive - f_drag - f_rr
                            a_net = f_net / self.mass
                            p_mech = f_tractive * v_current
                            p_elec = p_mech / self.eta_drivetrain
                            i_bat = p_elec / self.v_pack
                        
                        if i_bat > peak_current:
                            peak_current = i_bat
                        
                        v_next = max(1.0, v_current + a_net * dt)
                        
                        ah_used = (i_bat * dt) / 3600.0
                        remaining_ah = max(0.0, remaining_ah - ah_used)
                        if p_elec > 0:
                            total_energy_kwh += (p_elec * dt) / (3600.0 * 1000.0)
                        
                        q_gen = (i_bat ** 2) * self.r_int
                        q_cool = self.h_cooling * self.cooling_area * (current_temp - self.t_ambient)
                        d_temp = ((q_gen - q_cool) * dt) / (self.bat_mass * self.c_p)
                        current_temp += d_temp
                        
                        d_dist = ((v_current + v_next) / 2.0) * dt
                        dist_in_straight += d_dist
                        total_dist_m += d_dist
                        v_current = v_next
                        current_time += dt
                        
                        current_soc_pct = (remaining_ah / self.capacity_ah) * 100.0
                        soc_ratio = max(0.0, min(1.0, current_soc_pct / 100.0))
                        v_cell_ocv = 2.5 + 1.2 * soc_ratio + 0.1 * (soc_ratio ** 2)
                        v_cell_term = v_cell_ocv - i_bat * r_cell
                        if v_cell_term < min_cell_v_seen:
                            min_cell_v_seen = v_cell_term

                        time_points.append(current_time)
                        soc_points.append(current_soc_pct)
                        capacity_ah_points.append(remaining_ah)
                        temp_points.append(current_temp)
                        current_points.append(i_bat)
                        speed_points.append(v_current * 3.6)
                        dist_points.append(total_dist_m)

                        if current_temp >= 60.0:
                            bms_activated = True
                            bms_reason_type = "temperature"
                            bms_reason = f"Thermal Overheat: Pack temperature reached {current_temp:.1f}°C (FSAE limit: 60.0°C)"
                            stopped_lap = lap + 1
                            break
                        elif v_cell_term <= 2.5:
                            bms_activated = True
                            bms_reason_type = "voltage"
                            bms_reason = f"Cell terminal voltage dropped to {v_cell_term:.2f}V (minimum limit 2.5V)"
                            stopped_lap = lap + 1
                            break
                        elif remaining_ah <= 0.0001 or current_soc_pct <= 0.01:
                            bms_activated = True
                            bms_reason_type = "soc"
                            bms_reason = "Battery pack SOC depleted to 0.0%"
                            stopped_lap = lap + 1
                            break

        return {
            'time': time_points,
            'soc': soc_points,
            'capacity_ah': capacity_ah_points,
            'temp': temp_points,
            'current': current_points,
            'speed': speed_points,
            'total_time_s': current_time,
            'lap_time_avg_s': current_time / max(1, stopped_lap if bms_activated else self.num_laps),
            'final_soc_pct': soc_points[-1],
            'final_capacity_ah': remaining_ah,
            'final_temp_c': current_temp,
            'peak_current_a': peak_current,
            'total_energy_kwh': total_energy_kwh,
            'v_turn_kmh': v_turn * 3.6,
            'bms_activated': bms_activated,
            'bms_reason': bms_reason,
            'bms_reason_type': bms_reason_type,
            'stopped_lap': stopped_lap,
            'total_laps_requested': self.num_laps,
            'distance_km': total_dist_m / 1000.0,
            'min_cell_v_seen': min_cell_v_seen,
            'dist_m': dist_points,
        }

    def get_track_coordinates(self):
        """
        Generates (x, y) 2D point lists representing the bird's-eye view layout of a closed-loop Formula SAE track circuit.
        Returns x_coords, y_coords, total_length_m
        """
        x, y = 0.0, 0.0
        heading = 0.0  # radians (0 = east / +X)
        
        x_coords = [x]
        y_coords = [y]

        num_segments = max(self.num_straights, self.num_turns)
        
        # In a closed loop circuit, total turning angle equals 360 degrees (2*pi)
        # If num_turns is specified, default turn angle per turn is 360 / num_turns unless custom
        effective_turn_angle_deg = 360.0 / self.num_turns if self.num_turns > 0 else 90.0
        # Use user specified angle if provided and valid, otherwise effective turn angle for closed circuit
        if self.turn_angle != 90.0 or self.num_turns == 4:
            actual_turn_angle_deg = self.turn_angle
        else:
            actual_turn_angle_deg = effective_turn_angle_deg

        turn_angle_rad = math.radians(actual_turn_angle_deg)
        turn_arc_length = self.turn_radius * turn_angle_rad
        turn_dir = 1.0  # Turn in consistent direction to form a closed circuit loop

        total_length = 0.0

        for seg in range(num_segments):
            # 1. Straight
            if seg < self.num_straights:
                num_pts = max(10, int(self.straight_length / 5.0))
                for i in range(1, num_pts + 1):
                    t = i / num_pts
                    px = x + (t * self.straight_length) * math.cos(heading)
                    py = y + (t * self.straight_length) * math.sin(heading)
                    x_coords.append(px)
                    y_coords.append(py)
                
                x = x_coords[-1]
                y = y_coords[-1]
                total_length += self.straight_length

            # 2. Turn
            if seg < self.num_turns:
                center_angle = heading + turn_dir * (math.pi / 2.0)
                cx = x + self.turn_radius * math.cos(center_angle)
                cy = y + self.turn_radius * math.sin(center_angle)
                
                start_angle = center_angle + math.pi
                end_angle = start_angle + turn_dir * turn_angle_rad
                
                num_pts = max(15, int(actual_turn_angle_deg / 3.0))
                for i in range(1, num_pts + 1):
                    t = i / num_pts
                    curr_a = start_angle + t * (end_angle - start_angle)
                    px = cx + self.turn_radius * math.cos(curr_a)
                    py = cy + self.turn_radius * math.sin(curr_a)
                    x_coords.append(px)
                    y_coords.append(py)
                
                x = x_coords[-1]
                y = y_coords[-1]
                heading += turn_dir * turn_angle_rad
                total_length += turn_arc_length

        # Ensure loop is completely closed by connecting back to start point (0, 0)
        dist_to_start = math.hypot(x_coords[-1] - x_coords[0], y_coords[-1] - y_coords[0])
        if dist_to_start > 0.1:
            num_pts = max(5, int(dist_to_start / 5.0))
            x_end, y_end = x_coords[-1], y_coords[-1]
            for i in range(1, num_pts + 1):
                t = i / num_pts
                x_coords.append(x_end + t * (x_coords[0] - x_end))
                y_coords.append(y_end + t * (y_coords[0] - y_end))
            total_length += dist_to_start

        return x_coords, y_coords, total_length

    @staticmethod
    def get_track_coordinates_from_segments(segments):
        """
        Generates (x, y) 2D point lists from an ordered list of segments.
        Applies heading normalization and smooth spatial loop closure so that
        track endpoints align seamlessly into a closed loop without sharp jump lines.
        Returns x_coords, y_coords, total_length_m
        """
        # 1. Determine raw heading change & target loop heading
        raw_net_heading_rad = 0.0
        for seg in segments:
            if seg[0] == "turn":
                angle_rad = math.radians(seg[2])
                turn_dir = -1.0 if seg[3] == "right" else 1.0
                raw_net_heading_rad += turn_dir * angle_rad

        # Target -2*pi for net clockwise, +2*pi for net anti-clockwise
        target_heading_rad = -2.0 * math.pi if raw_net_heading_rad < 0 else 2.0 * math.pi
        turn_sum = sum(seg[2] for seg in segments if seg[0] == "turn")
        heading_diff = target_heading_rad - raw_net_heading_rad

        # 2. Build preliminary path
        x, y = 0.0, 0.0
        heading = 0.0

        x_coords = [x]
        y_coords = [y]
        distances = [0.0]
        total_length = 0.0

        for seg in segments:
            if seg[0] == "straight":
                length = seg[1]
                num_pts = max(5, int(length / 8.0))
                for i in range(1, num_pts + 1):
                    t = i / num_pts
                    px = x + (t * length) * math.cos(heading)
                    py = y + (t * length) * math.sin(heading)
                    x_coords.append(px)
                    y_coords.append(py)
                    total_length += length / num_pts
                    distances.append(total_length)
                x, y = x_coords[-1], y_coords[-1]
            elif seg[0] == "turn":
                radius = seg[1]
                raw_angle_deg = seg[2]
                direction = seg[3]

                # Proportional angle adjustment for perfect 360-degree net rotation
                scale_adj = (raw_angle_deg / max(1.0, turn_sum)) * math.degrees(abs(heading_diff))
                sign = 1.0 if (heading_diff > 0 if direction == "left" else heading_diff < 0) else -1.0
                adj_angle_deg = raw_angle_deg + sign * scale_adj

                angle_rad = math.radians(adj_angle_deg)
                turn_dir = 1.0 if direction == "left" else -1.0

                center_angle = heading + turn_dir * (math.pi / 2.0)
                cx = x + radius * math.cos(center_angle)
                cy = y + radius * math.sin(center_angle)

                start_angle = center_angle + math.pi
                end_angle = start_angle + turn_dir * angle_rad

                num_pts = max(8, int(raw_angle_deg / 3.0))
                arc_len = radius * angle_rad
                for i in range(1, num_pts + 1):
                    t = i / num_pts
                    curr_a = start_angle + t * (end_angle - start_angle)
                    px = cx + radius * math.cos(curr_a)
                    py = cy + radius * math.sin(curr_a)
                    x_coords.append(px)
                    y_coords.append(py)
                    total_length += arc_len / num_pts
                    distances.append(total_length)

                x, y = x_coords[-1], y_coords[-1]
                heading += turn_dir * angle_rad

        # 3. Smooth spatial loop closure drift correction
        dx = x_coords[-1] - x_coords[0]
        dy = y_coords[-1] - y_coords[0]
        S = max(1.0, distances[-1])

        closed_x = []
        closed_y = []
        for i in range(len(x_coords)):
            t = distances[i] / S
            w = t * t * (3.0 - 2.0 * t)  # Smooth cubic weighting function
            closed_x.append(x_coords[i] - w * dx)
            closed_y.append(y_coords[i] - w * dy)

        dxs = np.diff(closed_x)
        dys = np.diff(closed_y)
        actual_closed_len = float(np.sum(np.hypot(dxs, dys)))

        return closed_x, closed_y, actual_closed_len

    def run_simulation_from_segments(self, segments, dt=0.05):
        """
        Simulates a multi-lap run on a track defined by per-segment geometry.
        Each straight and turn can have its own length, radius, and angle.
        Returns the same result dict as run_simulation().
        """
        # Compute exact closed-loop geometric track length for perfect lap distance alignment
        _, _, track_total_geom_len = BatterySimulator.get_track_coordinates_from_segments(segments)
        nominal_seg_len = 0.0
        for seg in segments:
            if seg[0] == "straight":
                nominal_seg_len += seg[1]
            elif seg[0] == "turn":
                nominal_seg_len += seg[1] * math.radians(seg[2])

        geom_scale = (track_total_geom_len / nominal_seg_len) if nominal_seg_len > 0 else 1.0

        time_points = [0.0]
        soc_points = [100.0]
        capacity_ah_points = [self.capacity_ah]
        temp_points = [self.t_ambient]
        current_points = [0.0]
        speed_points = [0.0]
        dist_points = [0.0]

        remaining_ah = self.capacity_ah
        current_temp = self.t_ambient
        current_time = 0.0
        peak_current = 0.0
        total_energy_kwh = 0.0
        total_dist_m = 0.0

        bms_activated = False
        bms_reason = ""
        bms_reason_type = "none"
        stopped_lap = self.num_laps
        min_cell_v_seen = 4.2
        n_cells_series = max(1.0, self.v_pack / 3.6)
        r_cell = self.r_int / n_cells_series

        p_max_watts = self.p_max_kw * 1000.0

        for lap in range(self.num_laps):
            if bms_activated:
                break
            for seg in segments:
                if bms_activated:
                    break
                if seg[0] == "straight":
                    straight_length = seg[1]
                    v_exit = self._find_next_turn_speed(segments, seg)

                    dist_in_straight = 0.0
                    v_current = max(v_exit, 5.0)

                    a_brake = self.mu * self.g

                    while dist_in_straight < straight_length:
                        remaining_dist = straight_length - dist_in_straight
                        a_brake_needed = (v_current**2 - v_exit**2) / (2 * max(0.001, remaining_dist))
                        is_braking = (a_brake_needed >= a_brake * 0.9) and (v_current > v_exit)

                        f_drag = 0.5 * self.air_density * self.cd_a * (v_current ** 2)
                        f_rr = self.mass * self.g * self.c_rr

                        if is_braking:
                            a_net = -a_brake
                            f_braking = self.mass * a_brake
                            p_regen_mech = f_braking * v_current
                            p_elec = -p_regen_mech * self.regen_efficiency
                            i_bat = p_elec / self.v_pack
                        else:
                            f_tractive_limit = self.mu * self.mass * self.g
                            f_power_limit = (p_max_watts * self.eta_drivetrain) / max(0.1, v_current)
                            f_tractive = min(f_tractive_limit, f_power_limit)

                            f_net = f_tractive - f_drag - f_rr
                            a_net = f_net / self.mass
                            p_mech = f_tractive * v_current
                            p_elec = p_mech / self.eta_drivetrain
                            i_bat = p_elec / self.v_pack

                        if i_bat > peak_current:
                            peak_current = i_bat

                        v_next = max(1.0, v_current + a_net * dt)

                        ah_used = (i_bat * dt) / 3600.0
                        remaining_ah = max(0.0, remaining_ah - ah_used)
                        if p_elec > 0:
                            total_energy_kwh += (p_elec * dt) / (3600.0 * 1000.0)

                        q_gen = (i_bat ** 2) * self.r_int
                        q_cool = self.h_cooling * self.cooling_area * (current_temp - self.t_ambient)
                        d_temp = ((q_gen - q_cool) * dt) / (self.bat_mass * self.c_p)
                        current_temp += d_temp

                        d_dist = ((v_current + v_next) / 2.0) * dt
                        dist_in_straight += d_dist
                        total_dist_m += d_dist * geom_scale
                        v_current = v_next
                        current_time += dt

                        current_soc_pct = (remaining_ah / self.capacity_ah) * 100.0
                        soc_ratio = max(0.0, min(1.0, current_soc_pct / 100.0))
                        v_cell_ocv = 2.5 + 1.2 * soc_ratio + 0.1 * (soc_ratio ** 2)
                        v_cell_term = v_cell_ocv - i_bat * r_cell
                        if v_cell_term < min_cell_v_seen:
                            min_cell_v_seen = v_cell_term

                        time_points.append(current_time)
                        soc_points.append(current_soc_pct)
                        capacity_ah_points.append(remaining_ah)
                        temp_points.append(current_temp)
                        current_points.append(i_bat)
                        speed_points.append(v_current * 3.6)
                        dist_points.append(total_dist_m)

                        if current_temp >= 60.0:
                            bms_activated = True
                            bms_reason_type = "temperature"
                            bms_reason = f"Thermal Overheat: Pack temperature reached {current_temp:.1f}°C (FSAE limit: 60.0°C)"
                            stopped_lap = lap + 1
                            break
                        elif v_cell_term <= 2.5:
                            bms_activated = True
                            bms_reason_type = "voltage"
                            bms_reason = f"Cell terminal voltage dropped to {v_cell_term:.2f}V (minimum limit 2.5V)"
                            stopped_lap = lap + 1
                            break
                        elif remaining_ah <= 0.0001 or current_soc_pct <= 0.01:
                            bms_activated = True
                            bms_reason_type = "soc"
                            bms_reason = "Battery pack SOC depleted to 0.0%"
                            stopped_lap = lap + 1
                            break

                elif seg[0] == "turn" and not bms_activated:
                    turn_radius = seg[1]
                    turn_angle_deg = seg[2]

                    v_turn = math.sqrt(self.mu * self.g * turn_radius)
                    turn_arc_length = turn_radius * math.radians(turn_angle_deg)

                    dist_in_turn = 0.0
                    v_current = v_turn

                    while dist_in_turn < turn_arc_length:
                        f_drag = 0.5 * self.air_density * self.cd_a * (v_current ** 2)
                        f_rr = self.mass * self.g * self.c_rr
                        f_res = f_drag + f_rr

                        p_mech = f_res * v_current
                        p_elec = p_mech / self.eta_drivetrain

                        i_bat = p_elec / self.v_pack if self.v_pack > 0 else 0.0
                        if i_bat > peak_current:
                            peak_current = i_bat

                        ah_used = (i_bat * dt) / 3600.0
                        remaining_ah = max(0.0, remaining_ah - ah_used)
                        total_energy_kwh += (p_elec * dt) / (3600.0 * 1000.0)

                        q_gen = (i_bat ** 2) * self.r_int
                        q_cool = self.h_cooling * self.cooling_area * (current_temp - self.t_ambient)
                        d_temp = ((q_gen - q_cool) * dt) / (self.bat_mass * self.c_p)
                        current_temp += d_temp

                        d_dist = v_current * dt
                        dist_in_turn += d_dist
                        total_dist_m += d_dist * geom_scale
                        current_time += dt

                        current_soc_pct = (remaining_ah / self.capacity_ah) * 100.0
                        soc_ratio = max(0.0, min(1.0, current_soc_pct / 100.0))
                        v_cell_ocv = 2.5 + 1.2 * soc_ratio + 0.1 * (soc_ratio ** 2)
                        v_cell_term = v_cell_ocv - i_bat * r_cell
                        if v_cell_term < min_cell_v_seen:
                            min_cell_v_seen = v_cell_term

                        time_points.append(current_time)
                        soc_points.append(current_soc_pct)
                        capacity_ah_points.append(remaining_ah)
                        temp_points.append(current_temp)
                        current_points.append(i_bat)
                        speed_points.append(v_current * 3.6)
                        dist_points.append(total_dist_m)

                        if current_temp >= 60.0:
                            bms_activated = True
                            bms_reason_type = "temperature"
                            bms_reason = f"Thermal Overheat: Pack temperature reached {current_temp:.1f}°C (FSAE limit: 60.0°C)"
                            stopped_lap = lap + 1
                            break
                        elif v_cell_term <= 2.5:
                            bms_activated = True
                            bms_reason_type = "voltage"
                            bms_reason = f"Cell terminal voltage dropped to {v_cell_term:.2f}V (minimum limit 2.5V)"
                            stopped_lap = lap + 1
                            break
                        elif remaining_ah <= 0.0001 or current_soc_pct <= 0.01:
                            bms_activated = True
                            bms_reason_type = "soc"
                            bms_reason = "Battery pack SOC depleted to 0.0%"
                            stopped_lap = lap + 1
                            break

            # Anchor completed laps precisely at track lap boundaries if not interrupted by BMS cutoff
            if not bms_activated:
                total_dist_m = (lap + 1) * track_total_geom_len
                if dist_points:
                    dist_points[-1] = total_dist_m

        return {
            'time': time_points,
            'soc': soc_points,
            'capacity_ah': capacity_ah_points,
            'temp': temp_points,
            'current': current_points,
            'speed': speed_points,
            'total_time_s': current_time,
            'lap_time_avg_s': current_time / max(1, stopped_lap if bms_activated else self.num_laps),
            'final_soc_pct': soc_points[-1],
            'final_capacity_ah': remaining_ah,
            'final_temp_c': current_temp,
            'peak_current_a': peak_current,
            'total_energy_kwh': total_energy_kwh,
            'v_turn_kmh': 0.0,
            'bms_activated': bms_activated,
            'bms_reason': bms_reason,
            'bms_reason_type': bms_reason_type,
            'stopped_lap': stopped_lap,
            'total_laps_requested': self.num_laps,
            'distance_km': total_dist_m / 1000.0,
            'min_cell_v_seen': min_cell_v_seen,
            'dist_m': dist_points,
        }

    @staticmethod
    def get_car_position_at_distance(dist_m, x_coords, y_coords, cum_lens=None):
        """
        Given a total accumulated distance in meters and 2D track closed-loop coordinates,
        returns (x_car, y_car, dx, dy, heading_deg) for vehicle animation positioning.
        """
        if x_coords is None or len(x_coords) < 2:
            return 0.0, 0.0, 1.0, 0.0, 0.0

        xs = np.asarray(x_coords)
        ys = np.asarray(y_coords)

        if cum_lens is None:
            dxs = np.diff(xs)
            dys = np.diff(ys)
            seg_lens = np.hypot(dxs, dys)
            cum_lens = np.insert(np.cumsum(seg_lens), 0, 0.0)

        track_total_len = max(1.0, cum_lens[-1])
        lap_dist = dist_m % track_total_len

        # Find segment index
        idx = np.searchsorted(cum_lens, lap_dist, side='right') - 1
        idx = max(0, min(len(xs) - 2, idx))

        s0 = cum_lens[idx]
        s1 = cum_lens[idx + 1]
        ds = max(1e-6, s1 - s0)
        t = (lap_dist - s0) / ds

        x_car = xs[idx] + t * (xs[idx + 1] - xs[idx])
        y_car = ys[idx] + t * (ys[idx + 1] - ys[idx])

        dx = xs[idx + 1] - xs[idx]
        dy = ys[idx + 1] - ys[idx]
        heading_deg = math.degrees(math.atan2(dy, dx))

        return float(x_car), float(y_car), float(dx), float(dy), float(heading_deg)

    def _find_next_turn_speed(self, segments, current_seg):
        """Find the cornering speed of the next turn segment after the current one."""
        found_current = False
        for seg in segments:
            if seg is current_seg:
                found_current = True
                continue
            if found_current and seg[0] == "turn":
                turn_radius = seg[1]
                return math.sqrt(self.mu * self.g * turn_radius)
        # If no next turn found, wrap around to first turn
        for seg in segments:
            if seg[0] == "turn":
                turn_radius = seg[1]
                return math.sqrt(self.mu * self.g * turn_radius)
        return 10.0  # fallback


