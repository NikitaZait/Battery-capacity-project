import sys, os, math
sys.path.append(os.path.dirname(__file__))
from test_closure import get_track_coordinates_from_segments

# Target 4361m length
canada_segments = [
    # Start/Finish straight to Senna S
    ("straight", 420),
    # Turns 1 & 2: Senna S (Left 60°, tight Right hairpin 150°)
    ("turn", 30, 60, "left"),
    ("straight", 35),
    ("turn", 18, 150, "right"),
    # Run to Turn 3 & 4 chicane
    ("straight", 350),
    ("turn", 25, 70, "right"),
    ("straight", 30),
    ("turn", 25, 70, "left"),
    # Run to Turn 5
    ("straight", 260),
    ("turn", 80, 30, "left"),
    # Run to Turn 6 & 7 chicane
    ("straight", 320),
    ("turn", 22, 75, "left"),
    ("straight", 35),
    ("turn", 22, 75, "right"),
    # Straight along Olympic basin to Turn 8 & 9 chicane
    ("straight", 480),
    ("turn", 25, 70, "right"),
    ("straight", 35),
    ("turn", 25, 70, "left"),
    # Run to L'Épingle hairpin
    ("straight", 420),
    # Turn 10: L'Épingle (tight hairpin right)
    ("turn", 15, 170, "right"),
    # Casino Back Straight (very long)
    ("straight", 1253),
    # Turns 13 & 14: Wall of Champions chicane
    ("turn", 20, 80, "right"),
    ("straight", 40),
    ("turn", 20, 80, "left"),
    # Final pit straight link back to start
    ("straight", 280),
]

xs, ys, S, gap = get_track_coordinates_from_segments(canada_segments)
num_straights = sum(1 for s in canada_segments if s[0] == "straight")
num_turns = sum(1 for s in canada_segments if s[0] == "turn")

print(f"Canada (Circuit Gilles Villeneuve) length: {S:.1f} m, Gap: {gap:.6f} m")
print(f"Straights count: {num_straights}, Turns count: {num_turns}")
