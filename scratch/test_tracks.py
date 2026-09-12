import math
import matplotlib.pyplot as plt

def generate_raw_coords(segments):
    x, y = 0.0, 0.0
    heading = 0.0
    x_coords = [x]
    y_coords = [y]
    
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
            x, y = x_coords[-1], y_coords[-1]
        elif seg[0] == "turn":
            radius = seg[1]
            angle_deg = seg[2]
            direction = seg[3]
            angle_rad = math.radians(angle_deg)
            turn_dir = -1.0 if direction == "right" else 1.0
            
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
            
    return x_coords, y_coords

print("Scratch test script ready")
