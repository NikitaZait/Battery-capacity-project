import math

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
    # Hairpin (Grand Hotel / Loews) - LEFT TURN!
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

def calculate_geometry(segments):
    x, y = 0.0, 0.0
    heading = 0.0
    x_coords = [x]
    y_coords = [y]
    total_len = 0.0

    for seg in segments:
        if seg[0] == "straight":
            length = seg[1]
            total_len += length
            num_pts = max(5, int(length / 8.0))
            for i in range(1, num_pts + 1):
                t = i / num_pts
                px = x + (t * length) * math.cos(heading)
                py = y + (t * length) * math.sin(heading)
                x_coords.append(px)
                y_coords.append(py)
            x, y = x_coords[-1], y_coords[-1]
        elif seg[0] == "turn":
            radius = seg[1]
            angle_deg = seg[2]
            direction = seg[3]
            angle_rad = math.radians(angle_deg)
            turn_dir = -1.0 if direction == "right" else 1.0
            total_len += radius * angle_rad

            center_angle = heading + turn_dir * (math.pi / 2.0)
            cx = x + radius * math.cos(center_angle)
            cy = y + radius * math.sin(center_angle)

            start_angle = center_angle + math.pi
            end_angle = start_angle + turn_dir * angle_rad

            num_pts = max(8, int(angle_deg / 3.0))
            for i in range(1, num_pts + 1):
                t = i / num_pts
                curr_a = start_angle + t * (end_angle - start_angle)
                px = cx + radius * math.cos(curr_a)
                py = cy + radius * math.sin(curr_a)
                x_coords.append(px)
                y_coords.append(py)

            x, y = x_coords[-1], y_coords[-1]
            heading += turn_dir * angle_rad

    dx = x_coords[-1] - x_coords[0]
    dy = y_coords[-1] - y_coords[0]
    dist_gap = math.hypot(dx, dy)
    net_deg = math.degrees(heading)
    print(f"Monaco total length: {total_len:.1f} m, End Gap: {dist_gap:.1f} m, Net heading: {net_deg:.1f} deg")
    return x_coords, y_coords

calculate_geometry(monaco_segments)
