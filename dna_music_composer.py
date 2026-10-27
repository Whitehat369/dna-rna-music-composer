"""A tiny, dependency-free DNA-to-music composer with a Tkinter interface."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


SAMPLE_RATE = 22050
BASES = "ACGT"
SCALES = {
    "C major pentatonic": (0, 2, 4, 7, 9),
    "A minor pentatonic": (0, 3, 5, 7, 10),
    "C major": (0, 2, 4, 5, 7, 9, 11),
}
STYLES = {
    "Dreamy": {"wave": "soft", "beat": False, "bpm": 96, "volume": 0.72},
    "Arcade": {"wave": "bright", "beat": True, "bpm": 132, "volume": 0.68},
    "Lo-fi groove": {"wave": "warm", "beat": True, "bpm": 84, "volume": 0.72},
}
INSTRUMENTS = ("Piano", "Guitar", "Violin", "Flute", "Synth")
# Each base gets a distinct scale degree. These are musical choices, not biology.
BASE_SCALE_DEGREES = {"A": 0, "C": 1, "G": 2, "T": 3}


def clean_sequence(raw: str) -> str:
    sequence = "".join(raw.upper().split()).replace("U", "T")
    invalid = sorted(set(sequence) - set(BASES))
    if invalid:
        raise ValueError("Use only A, C, G, T, or U (spaces and line breaks are okay).")
    if not sequence:
        raise ValueError("Enter a DNA sequence first.")
    return sequence


def write_wav(path: Path, sequence: str, scale_name: str, octave: int,
              seconds_per_note: float, style_name: str, instrument_name: str) -> None:
    """Render a melody using a simple synthesized instrument voice."""
    style = STYLES[style_name]
    scale = SCALES[scale_name]
    frames_per_note = int(SAMPLE_RATE * seconds_per_note)
    # Longer sequences still work, while keeping audio generation responsive.
    sequence = sequence[:512]
    notes = []
    for i, base in enumerate(sequence):
        degree = BASE_SCALE_DEGREES[base]
        # Every fifth note moves to a different scale degree for a more song-like phrase.
        if i % 5 == 4:
            degree = (degree + (1 if base in "AG" else 3)) % len(scale)
        midi_note = 12 * (octave + 1) + scale[degree % len(scale)]
        notes.append(440.0 * 2 ** ((midi_note - 69) / 12))
    beat_len = max(1, int(SAMPLE_RATE * 60 / style["bpm"]))
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        for note_index, frequency in enumerate(notes):
            frames = bytearray()
            # Bass changes every four notes and follows the first note of that bar.
            bar_start = (note_index // 4) * 4
            bar_base = sequence[bar_start]
            bass_degree = BASE_SCALE_DEGREES[bar_base] % len(scale)
            bass_midi = 12 * (octave - 1) + scale[bass_degree]
            bass_frequency = 440.0 * 2 ** ((bass_midi - 69) / 12)
            for j in range(frames_per_note):
                t = j / SAMPLE_RATE
                # Different harmonic shapes, envelopes, and vibrato make each timbre distinct.
                vibrato_depth = {"Violin": 0.007, "Flute": 0.0025}.get(instrument_name, 0.0)
                vibrato = 1.0 + vibrato_depth * math.sin(2 * math.pi * 5.2 * t)
                phase = 2 * math.pi * frequency * vibrato * t
                if instrument_name == "Guitar":
                    lead = (math.sin(phase) + 0.62 * math.sin(2 * phase)
                            + 0.40 * math.sin(3 * phase) + 0.24 * math.sin(4 * phase)
                            + 0.14 * math.sin(5 * phase)) / 2.4
                    envelope = min(1.0, t * 75) * math.exp(-4.1 * t / seconds_per_note)
                elif instrument_name == "Violin":
                    lead = (math.sin(phase) + 0.72 * math.sin(2 * phase)
                            + 0.52 * math.sin(3 * phase) + 0.38 * math.sin(4 * phase)
                            + 0.27 * math.sin(5 * phase) + 0.18 * math.sin(6 * phase)) / 3.07
                    envelope = min(1.0, t * 5) * (0.76 + 0.24 * math.exp(-0.35 * t / seconds_per_note))
                elif instrument_name == "Flute":
                    lead = (math.sin(phase) + 0.11 * math.sin(2 * phase)
                            + 0.045 * math.sin(3 * phase) + 0.02 * math.sin(4 * phase)) / 1.175
                    envelope = min(1.0, t * 8) * (0.82 + 0.18 * math.exp(-0.5 * t / seconds_per_note))
                elif instrument_name == "Piano":
                    lead = (math.sin(phase) * math.exp(-1.7 * t / seconds_per_note)
                            + 0.52 * math.sin(2 * phase) * math.exp(-3.4 * t / seconds_per_note)
                            + 0.27 * math.sin(3 * phase) * math.exp(-5.2 * t / seconds_per_note)
                            + 0.13 * math.sin(4 * phase) * math.exp(-7.0 * t / seconds_per_note)) / 1.92
                    envelope = min(1.0, t * 48) * math.exp(-1.8 * t / seconds_per_note)
                else:
                    lead = (math.sin(phase) + 0.85 * math.sin(3 * phase)
                            + 0.62 * math.sin(5 * phase) + 0.38 * math.sin(7 * phase)) / 2.85
                    envelope = min(1.0, t * 18) * math.exp(-1.25 * t / seconds_per_note)
                bass_env = min(1.0, t * 24) * math.exp(-2.4 * t / seconds_per_note)
                bass = math.sin(2 * math.pi * bass_frequency * t) * bass_env * 0.22
                beat = 0.0
                absolute_frame = note_index * frames_per_note + j
                if style["beat"] and absolute_frame % beat_len < int(SAMPLE_RATE * 0.045):
                    beat_age = (absolute_frame % beat_len) / SAMPLE_RATE
                    beat = math.sin(2 * math.pi * (90 - 45 * beat_age / 0.045) * beat_age)
                    beat *= math.exp(-beat_age * 42) * 0.18
                mixed = max(-0.95, min(0.95, style["volume"] * lead * envelope + bass + beat))
                # Gentle alternating pan gives the lead movement across the stereo field.
                pan = -0.12 if note_index % 2 == 0 else 0.12
                left = int(32767 * mixed * (1.0 - max(0.0, pan)))
                right = int(32767 * mixed * (1.0 + min(0.0, pan)))
                frames.extend(struct.pack("<hh", left, right))
            output.writeframes(frames)


class ComposerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("DNA to Music Composer")
        self.geometry("700x630")
        self.minsize(600, 560)
        self.configure(bg="#f5f7fb")
        self.scale = tk.StringVar(value="C major pentatonic")
        self.style = tk.StringVar(value="Dreamy")
        self.instrument = tk.StringVar(value="Piano")
        self.octave = tk.IntVar(value=4)
        self.note_length = tk.DoubleVar(value=0.28)
        self.status = tk.StringVar(value="Ready to compose")
        self._build()

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=24)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="DNA to Music", font=("Segoe UI", 23, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Paste DNA or RNA and hear its bases as a melody.",
                  font=("Segoe UI", 11)).pack(anchor="w", pady=(2, 16))

        ttk.Label(outer, text="DNA sequence", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.sequence_box = tk.Text(outer, height=7, wrap="word", font=("Consolas", 12),
                                    relief="solid", borderwidth=1)
        self.sequence_box.pack(fill="x", pady=(6, 5))
        ttk.Label(outer, text="Enter your own sequence: A, C, G, T (DNA) or U (RNA). Spaces and line breaks are ignored.",
                  foreground="#596579").pack(anchor="w")

        settings = ttk.LabelFrame(outer, text="Sound settings", padding=12)
        settings.pack(fill="x", pady=16)
        ttk.Label(settings, text="Scale").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=5)
        ttk.Combobox(settings, textvariable=self.scale, values=tuple(SCALES),
                     state="readonly", width=24).grid(row=0, column=1, sticky="w", pady=5)
        ttk.Label(settings, text="Octave").grid(row=0, column=2, sticky="w", padx=(22, 8), pady=5)
        ttk.Spinbox(settings, from_=3, to=6, textvariable=self.octave,
                    width=5).grid(row=0, column=3, sticky="w", pady=5)
        ttk.Label(settings, text="Seconds per note").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=5)
        ttk.Scale(settings, from_=0.12, to=0.7, variable=self.note_length,
                  orient="horizontal", length=190).grid(row=1, column=1, sticky="w", pady=5)
        self.length_label = ttk.Label(settings, text="0.28 s")
        self.length_label.grid(row=1, column=2, columnspan=2, sticky="w", padx=(22, 0))
        ttk.Label(settings, text="Style").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=5)
        ttk.Combobox(settings, textvariable=self.style, values=tuple(STYLES),
                     state="readonly", width=24).grid(row=2, column=1, sticky="w", pady=5)
        ttk.Label(settings, text="Instrument").grid(row=2, column=2, sticky="w", padx=(22, 8), pady=5)
        ttk.Combobox(settings, textvariable=self.instrument, values=INSTRUMENTS,
                     state="readonly", width=12).grid(row=2, column=3, sticky="w", pady=5)
        ttk.Label(settings, text="Dreamy: soft · Arcade: bright beat · Lo-fi: mellow groove",
                  foreground="#596579").grid(row=3, column=0, columnspan=4, sticky="w", pady=(7, 0))
        ttk.Label(settings, text="Choose the synthesized lead sound; bass and style beat stay in the backing.",
                  foreground="#596579").grid(row=4, column=0, columnspan=4, sticky="w", pady=(5, 0))
        self.note_length.trace_add("write", self._update_length)

        self.mapping_label = ttk.Label(outer, text=self._mapping_text(),
                                       foreground="#34435a", wraplength=630)
        self.mapping_label.pack(anchor="w", pady=(0, 14))
        buttons = ttk.Frame(outer)
        buttons.pack(anchor="w")
        ttk.Button(buttons, text="Create and play", command=self._compose).pack(side="left")
        ttk.Button(buttons, text="Save WAV…", command=self._save).pack(side="left", padx=8)
        ttk.Label(outer, textvariable=self.status, foreground="#596579").pack(anchor="w", pady=(14, 0))
        ttk.Separator(outer).pack(fill="x", pady=15)
        ttk.Label(outer,
                  text="Instrument sounds are synthesized approximations. The base-to-note mapping is artistic; RNA U maps to DNA T's note.",
                  foreground="#596579", wraplength=630).pack(anchor="w")

    def _mapping_text(self) -> str:
        return "Melody: A/C/G/T choose scale notes · bass follows the sequence · every fifth note adds a melodic variation"

    def _update_length(self, *_args) -> None:
        self.length_label.configure(text=f"{self.note_length.get():.2f} s")

    def _compose(self, save_path: Path | None = None) -> None:
        try:
            sequence = clean_sequence(self.sequence_box.get("1.0", "end"))
            if len(sequence) > 512:
                sequence = sequence[:512]
        except (ValueError, tk.TclError) as error:
            messagebox.showerror("Check your settings", str(error), parent=self)
            return
        if save_path is None:
            save_path = Path.cwd() / "dna_melody.wav"
        try:
            write_wav(save_path, sequence, self.scale.get(), self.octave.get(),
                      self.note_length.get(), self.style.get(), self.instrument.get())
        except OSError as error:
            messagebox.showerror("Could not save audio", str(error), parent=self)
            return
        self.status.set(f"Created {len(sequence)} notes · {len(sequence) * self.note_length.get():.1f} seconds · {save_path}")
        try:
            import winsound
            winsound.PlaySound(str(save_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
        except (ImportError, RuntimeError):
            self.status.set(f"Saved {save_path}. Open the WAV file to listen.")

    def _save(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self, title="Save your DNA melody", defaultextension=".wav",
            initialfile="dna_melody.wav", filetypes=[("WAV audio", "*.wav")])
        if path:
            self._compose(Path(path))


if __name__ == "__main__":
    ComposerApp().mainloop()
