import math

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

        remaining_ah = self.capacity_ah
        current_temp = self.t_ambient
        current_time = 0.0
        peak_current = 0.0
        total_energy_kwh = 0.0

        p_max_watts = self.p_max_kw * 1000.0

        for lap in range(self.num_laps):
            num_segments = max(self.num_straights, self.num_turns)
            
            for seg in range(num_segments):
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
                        
                        dist_in_turn += v_current * dt
                        current_time += dt
                        
                        time_points.append(current_time)
                        soc_points.append((remaining_ah / self.capacity_ah) * 100.0)
                        capacity_ah_points.append(remaining_ah)
                        temp_points.append(current_temp)
                        current_points.append(i_bat)
                        speed_points.append(v_current * 3.6)

                # 2. Straight Segment
                if seg < self.num_straights:
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
                        
                        dist_in_straight += ((v_current + v_next) / 2.0) * dt
                        v_current = v_next
                        current_time += dt
                        
                        time_points.append(current_time)
                        soc_points.append((remaining_ah / self.capacity_ah) * 100.0)
                        capacity_ah_points.append(remaining_ah)
                        temp_points.append(current_temp)
                        current_points.append(i_bat)
                        speed_points.append(v_current * 3.6)

        return {
            'time': time_points,
            'soc': soc_points,
            'capacity_ah': capacity_ah_points,
            'temp': temp_points,
            'current': current_points,
            'speed': speed_points,
            'total_time_s': current_time,
            'lap_time_avg_s': current_time / max(1, self.num_laps),
            'final_soc_pct': soc_points[-1],
            'final_capacity_ah': remaining_ah,
            'final_temp_c': current_temp,
            'peak_current_a': peak_current,
            'total_energy_kwh': total_energy_kwh,
            'v_turn_kmh': v_turn * 3.6
        }

    def get_track_coordinates(self):
        """
        Generates (x, y) 2D point lists representing the bird's-eye view layout of the track.
        Returns x_coords, y_coords, total_length_m
        """
        x, y = 0.0, 0.0
        heading = 0.0  # radians (0 = east / +X)
        
        x_coords = [x]
        y_coords = [y]

        turn_angle_rad = math.radians(self.turn_angle)
        turn_arc_length = self.turn_radius * turn_angle_rad
        num_segments = max(self.num_straights, self.num_turns)
        turn_dir = 1.0  # +1 for left turn, -1 for right turn

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
                # Turn center is perpendicular to current heading
                center_angle = heading + turn_dir * (math.pi / 2.0)
                cx = x + self.turn_radius * math.cos(center_angle)
                cy = y + self.turn_radius * math.sin(center_angle)
                
                start_angle = center_angle + math.pi
                end_angle = start_angle + turn_dir * turn_angle_rad
                
                num_pts = max(15, int(self.turn_angle / 3.0))
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
                
                # Alternate direction every 2 turns for chicane/autocross feel
                if (seg + 1) % 2 == 0:
                    turn_dir *= -1.0

        return x_coords, y_coords, total_length

