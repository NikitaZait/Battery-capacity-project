import sys, os, math
sys.path.append(os.path.dirname(__file__))
from test_closure import get_track_coordinates_from_segments

interlagos_segments = [
    # Start/Finish straight (downhill to Senna S)
    ("straight", 450),
    # Senna S - Turn 1 left, Turn 2 right, Turn 3 left
    ("turn", 45, 65, "left"),
    ("straight", 30),
    ("turn", 40, 70, "right"),
    ("straight", 40),
    ("turn", 55, 50, "left"),
    # Curva do Sol (sweep onto back straight)
    ("straight", 150),
    ("turn", 75, 60, "left"),
    # Reta Oposta (back straight)
    ("straight", 550),
    # Descida do Lago (Turns 4 & 5)
    ("turn", 40, 55, "left"),
    ("straight", 60),
    ("turn", 35, 60, "left"),
    # Run up to Ferradura
    ("straight", 200),
    # Ferradura (infield entry right turn)
    ("turn", 45, 80, "right"),
    # Laranjinha
    ("straight", 80),
    ("turn", 35, 50, "right"),
    # Pinheirinho
    ("straight", 100),
    ("turn", 25, 65, "left"),
    # Bico de Pato (tight hairpin right)
    ("straight", 80),
    ("turn", 16, 140, "right"),
    # Mergulho
    ("straight", 70),
    ("turn", 60, 55, "left"),
    # Straight to Junção
    ("straight", 180),
    # Junção (uphill left)
    ("turn", 35, 80, "left"),
    # Subida dos Boxes (climb back to main straight)
    ("straight", 350),
    ("turn", 150, 45, "left"),
    ("straight", 250),
]

xs, ys, S, gap = get_track_coordinates_from_segments(interlagos_segments)
print(f"Interlagos length: {S:.1f} m, Gap: {gap:.6f} m")
