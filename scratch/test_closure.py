import math

def get_track_coordinates_from_segments(segments, target_direction="auto"):
    """
    Generates (x, y) 2D point lists from an ordered list of segments.
    Applies heading normalization and smooth spatial loop closure so that
    track endpoints align seamlessly into a closed loop without sharp jump lines.
    """
    # 1. Determine raw heading change & target loop heading
    raw_net_heading_rad = 0.0
    for seg in segments:
        if seg[0] == "turn":
            angle_rad = math.radians(seg[2])
            turn_dir = -1.0 if seg[3] == "right" else 1.0
            raw_net_heading_rad += turn_dir * angle_rad

    if target_direction == "auto":
        # Target -2*pi for net clockwise, +2*pi for net anti-clockwise
        target_heading_rad = -2.0 * math.pi if raw_net_heading_rad < 0 else 2.0 * math.pi
    elif target_direction == "clockwise":
        target_heading_rad = -2.0 * math.pi
    else:
        target_heading_rad = 2.0 * math.pi

    # Compute heading scale factor for turn segments
    turn_sum = sum(seg[2] for seg in segments if seg[0] == "turn")
    heading_diff = target_heading_rad - raw_net_heading_rad

    # 2. Build preliminary raw path
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
            
            # Apply proportional angle adjustment for perfect 360-deg net rotation
            adj_angle_deg = raw_angle_deg + (raw_angle_deg / max(1.0, turn_sum)) * math.degrees(abs(heading_diff)) * (1.0 if (heading_diff > 0 if direction == "left" else heading_diff < 0) else -1.0)
            angle_rad = math.radians(adj_angle_deg)
            turn_dir = -1.0 if direction == "right" else 1.0
            
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
        # Smooth cubic weight function for 0 start slope and 0 end slope
        w = t * t * (3.0 - 2.0 * t)
        closed_x.append(x_coords[i] - w * dx)
        closed_y.append(y_coords[i] - w * dy)

    return closed_x, closed_y, S, math.hypot(closed_x[-1]-closed_x[0], closed_y[-1]-closed_y[0])

monaco_segments = [
    # Start/Finish straight (short) then Sainte Devote
    ("straight", 180),
    ("turn", 35, 75, "right"),
    # Climb to Casino / Massenet
    ("straight", 320),
    ("turn", 45, 65, "left"),
    # Casino Square area
    ("straight", 80),
    ("turn", 30, 60, "right"),
    # Mirabeau
    ("straight", 120),
    ("turn", 20, 80, "right"),
    # Hairpin (Grand Hotel / Loews) - LEFT TURN
    ("straight", 40),
    ("turn", 12, 160, "left"),
    # Mirabeau Bas to Portier
    ("straight", 70),
    ("turn", 22, 85, "right"),
    # Tunnel straight
    ("straight", 360),
    # Nouvelle Chicane
    ("turn", 18, 50, "left"),
    ("straight", 40),
    ("turn", 18, 50, "right"),
    # Tabac corner
    ("straight", 140),
    ("turn", 28, 65, "left"),
    # Swimming pool chicane
    ("straight", 70),
    ("turn", 18, 55, "right"),
    ("straight", 40),
    ("turn", 18, 55, "left"),
    ("straight", 50),
    ("turn", 18, 55, "left"),
    ("straight", 30),
    ("turn", 18, 55, "right"),
    # Rascasse
    ("straight", 100),
    ("turn", 14, 135, "right"),
    # Anthony Noghes
    ("straight", 50),
    ("turn", 22, 75, "right"),
    # Close back to start
    ("straight", 100),
]

xs, ys, S, gap = get_track_coordinates_from_segments(monaco_segments)
print(f"Closed track total length: {S:.1f} m, Final Gap: {gap:.6f} m")
