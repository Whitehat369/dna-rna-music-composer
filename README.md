# DNA to Music Composer

A small Python desktop app that turns a DNA sequence into a layered melody and saves it as a stereo WAV audio file. It uses only Python's standard library.

## Run it

1. Install Python 3 if needed.
2. Open a terminal in this folder.
3. Run `python dna_music_composer.py`.
4. Paste your own DNA sequence (A/C/G/T) or RNA sequence (A/C/G/U), choose a scale, octave, note length, style, and instrument, then press **Create and play** or **Save WAV…**. The sequence box starts empty.

On Windows, **Create and play** starts playback automatically. On other systems, save the WAV and open it with an audio player.

## How the mapping works

Each base maps to one of the first four notes in the selected scale: A to the first, C to the second, G to the third, and T to the fourth. RNA's U maps to the same note as T. Each base becomes a lead note played with the selected synthesized timbre (Piano, Guitar, Violin, Flute, or Synth); a lower bass line follows the sequence, and the Arcade and Lo-fi styles add a beat. The instrument sounds use simple synthesis and are not realistic recordings; realistic instrument samples require a soundfont or audio sample library. Scale, octave, and note length shape the melody. This is an artistic sonification mapping, not a biological property of DNA. For a responsive preview, sequences are limited to 512 bases.
