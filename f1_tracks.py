"""
F1 Preset Track Definitions
============================
Contains hardcoded segment-based track layouts for 3 iconic Formula 1 circuits:
- Autodromo Nazionale Monza (Italy)
- Circuit de Monaco (Monaco)
- Autódromo José Carlos Pace / Interlagos (Brazil)

Segment types:
    ("straight", length_m)
    ("turn", radius_m, angle_deg, direction)   direction = "left" or "right"
"""

F1_TRACKS = {
    "monza": {
        "name": "Autodromo Nazionale Monza",
        "country": "Italy",
        "flag": "\U0001f1ee\U0001f1f9",
        "total_length_m": 5793,
        "num_turns": 11,
        "lap_record": "1:21.046 \u2014 Rubens Barrichello, 2004",
        "segments": [
            # Start/Finish straight
            ("straight", 650),
            # Variante del Rettifilo chicane
            ("turn", 20, 60, "right"),
            ("straight", 40),
            ("turn", 20, 60, "left"),
            # Run to Curva Grande
            ("straight", 380),
            # Curva Grande (sweeping right)
            ("turn", 180, 55, "right"),
            # Straight to second chicane
            ("straight", 500),
            # Variante della Roggia chicane
            ("turn", 20, 55, "left"),
            ("straight", 50),
            ("turn", 20, 55, "right"),
            # Straight to Lesmo curves
            ("straight", 250),
            # Lesmo 1
            ("turn", 60, 50, "right"),
            ("straight", 200),
            # Lesmo 2
            ("turn", 45, 45, "right"),
            # Run to Ascari chicane
            ("straight", 500),
            # Ascari chicane
            ("turn", 35, 45, "left"),
            ("straight", 70),
            ("turn", 35, 55, "right"),
            ("straight", 60),
            ("turn", 35, 40, "left"),
            # Straight to Parabolica (Curva Alboreto)
            ("straight", 480),
            # Parabolica (long right-hander)
            ("turn", 80, 100, "right"),
            # Back to Start/Finish
            ("straight", 400),
        ],
    },
    "monaco": {
        "name": "Circuit de Monaco",
        "country": "Monaco",
        "flag": "\U0001f1f2\U0001f1e8",
        "total_length_m": 3337,
        "num_turns": 19,
        "lap_record": "1:12.909 \u2014 Lewis Hamilton, 2021",
        "segments": [
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
        ],
    },
    "interlagos": {
        "name": "Aut\u00f3dromo Jos\u00e9 Carlos Pace",
        "country": "Brazil",
        "flag": "\U0001f1e7\U0001f1f7",
        "total_length_m": 4309,
        "num_turns": 15,
        "lap_record": "1:10.540 \u2014 Valtteri Bottas, 2018",
        "segments": [
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
            # Straight to Jun\u00e7\u00e3o
            ("straight", 180),
            # Jun\u00e7\u00e3o (uphill left)
            ("turn", 35, 80, "left"),
            # Subida dos Boxes (climb back to main straight)
            ("straight", 350),
            ("turn", 150, 45, "left"),
            ("straight", 250),
        ],
    },
}


def get_track_keys():
    """Returns list of track keys in display order (Monza first)."""
    return ["monza", "monaco", "interlagos"]


def get_track_display_name(key):
    """Returns a formatted display string for the dropdown, e.g. '\U0001f1f2\U0001f1e8 Monaco - Circuit de Monaco'."""
    t = F1_TRACKS[key]
    return f"{t['flag']} {t['country']} \u2014 {t['name']}"


def get_track_info_text(key):
    """Returns a multi-line info string for the track info card."""
    t = F1_TRACKS[key]
    return (
        f"{t['flag']}  {t['name']}\n"
        f"Length: {t['total_length_m']:,} m   |   Turns: {t['num_turns']}\n"
        f"Lap Record: {t['lap_record']}"
    )
