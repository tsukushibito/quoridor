# Sound assets

Retrieved 2026-09-30. All seven adopted sounds are CC0 1.0. Credit is retained in the
application. `manifest.json` records source pages, actual download URLs, source/distributed
SHA-256 hashes, sizes and processing parameters.

| Distributed file | Source | Author |
| --- | --- | --- |
| pawn.wav | impactWood_light_000.ogg / [Impact Sounds](https://kenney.nl/assets/impact-sounds) | Kenney |
| wall.wav | impactWood_medium_000.ogg / Impact Sounds | Kenney |
| click.wav | click_001.ogg / [Interface Sounds](https://kenney.nl/assets/interface-sounds) | Kenney |
| undo.wav | back_001.ogg / Interface Sounds | Kenney |
| win.wav | [Game Success Fanfare Short](https://freesound.org/people/el_boss/sounds/677858/) | el_boss |
| lose.wav | [Game Fail Fanfare](https://freesound.org/people/el_boss/sounds/677855/) | el_boss |
| cozy-puzzle.mp3 | [Cozy Puzzle In-Game 1](https://opengameart.org/content/cozy-puzzle-in-game-1) | MintoDog |

License: [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/).
Kenney's archive notices are included in the adjacent `*-license.txt` files with normalized
whitespace. The OpenGameArt and Freesound pages explicitly license the selected sounds CC0.
The Freesound downloads use the public HQ MP3 previews of the approved recordings, rather
than the login-only original WAV files. Their exact download URLs and hashes are recorded.

The BGM is a soft puzzle-game bossa nova with flute, saxophone and mallets. The author's
entire loop is normalized to -20 LUFS / -3 dB true peak and encoded at 128 kbps / 44.1 kHz
(2,084,071 bytes). Web Audio loops the decoded buffer's full duration, about 130.19 seconds;
there is no fixed 95-second cutoff. Winning/losing notes retain their beginning, with tails
shortened to 1.8/1.6 seconds and faded over the final 400 ms. SE uses mono PCM16 WAV / 44.1 kHz.

Only the selected processed files ship, locally. No runtime hotlinks or third-party players
are used. Numerical and browser signal verification is recorded in
`docs/reports/presentation-implementation.md`; real-speaker listening is a separate human check.
