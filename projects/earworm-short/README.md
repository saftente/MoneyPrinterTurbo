# Ohrwurm-Short: Warum bekommen wir Ohrwürmer? (TikTok / YouTube Shorts, 9:16, Deutsch)

Status: **fertig gerendert** (26,0 s, Limit 30 s; 1080×1920, 30 fps, −14 LUFS, Endkontrolle bestanden).
MP4 nach dem Render: `work/ohrwurm_short.mp4` (git-ignoriert). Pipeline wie `projects/dream-short`
(inklusive Rausch-Fix, Limiter, Fade-out, `check_tail.py`), als Kopie in `tools/`.

## Ablauf

```bash
python3 projects/earworm-short/tools/gemini_voice.py --voice Algenib
ffmpeg -y -i projects/earworm-short/work/voice/Algenib.wav -af "adelay=150:all=1,apad=pad_dur=0.8" projects/earworm-short/work/voice/Algenib_padded.wav
python3 projects/earworm-short/tools/align.py projects/earworm-short/work/voice/Algenib_padded.wav
python3 projects/earworm-short/tools/group_subs.py          # Wortgruppen-Untertitel
python3 projects/earworm-short/tools/curate.py search && python3 projects/earworm-short/tools/curate.py fetch && python3 projects/earworm-short/tools/curate.py cut
python3 projects/earworm-short/tools/make_bgm.py projects/earworm-short/work/bgm.wav && ffmpeg -y -i projects/earworm-short/work/bgm.wav -b:a 192k projects/earworm-short/assets/bgm_groove.mp3
./projects/earworm-short/render.sh                           # bricht ab bei > 30 s oder Störgeräusch am Ende
```

Szene 10 ist ein Pixabay-Foto (Pixabay hat kein Video mit Menschen, die Kaugummi kauen; nur kauende
Tiere). Es liegt unter `work/stills/` (nicht im Repo) und wird mit `picks.json` → `still` erneut geladen;
`curate.py cut` macht daraus einen Clip mit Push-in.

## Neu gegenüber den bisherigen Projekten (Zuschauerbindung)

- **Kürzer:** 65 Wörter, 26 s, keine Einleitung, der Hook beginnt ab Frame 0.
- **Erster Frame:** Neon-Bild mit Kopfhörern, der Hook-Text steht schon im ersten Frame (`run_cli.py`
  lässt die Pop-Animation für den ersten Untertitel weg; sie startet sonst winzig klein).
- **Szenen:** 14 Szenen à 1,1–2,8 s.
- **Wortgruppen statt Einzelwörter:** `tools/group_subs.py` bildet Gruppen aus höchstens 3 Wörtern und
  18 Zeichen, trennt nicht hinter Artikeln oder Präpositionen, und Gruppen sind entweder ganz gelb oder
  ganz weiß. Jede Gruppe steht mindestens 0,35 s. Schriftgröße 100 px statt 118 px für die längeren Zeilen.
- **Musik:** `make_bgm.py`, 108 bpm, ohne Gesang, gleichmäßiger Pegel (die Einbrüche nach den Risern aus
  dem Rückweg-Projekt sind entfernt, Impacts leiser), Lautheitsumfang des fertigen Videos 2,3 LU.
- **30-s-Grenze** wird in `render.sh` geprüft.

## Behobener Pipeline-Fehler: Schnitte liefen gegen Ende zu früh

MoviePy rundet Cliplängen auf 0,01 s (37 Frames = 1,2333 s → 1,23 s), und MoneyPrinterTurbo schneidet jeden
Clip auf diese Länge zu. Dabei ging etwa jeder zweite Clip um einen Frame verloren; die letzten Schnitte
kamen bis zu 8 Frames (0,27 s) zu früh. Das betraf auch die bisherigen Videos, dort mit kleinerem Effekt
(längere Szenen). `render.sh` hängt die Szenenclips jetzt vorab bildgenau zu einer Datei aneinander (Prüfung
der Frameanzahl) und übergibt nur diese; MoneyPrinterTurbo zerlegt sie in 8-s-Stücke ohne Rundungsverlust.
Gemessen: alle 13 Schnitte auf den Frame genau.

## Faktencheck

| Aussage im Video | Einordnung | Quelle |
|---|---|---|
| „Meist hast du ihn kürzlich oder oft gehört.“ | Häufigster Auslöser in Tagebuch- und Umfragestudien: kürzliche und wiederholte Musikexposition; Ohrwurm-Songs sind meist vertraut. In Jakubowski et al. sagten Beliebtheit und Aktualität vorher, wie oft ein Song als Ohrwurm genannt wurde. | Williamson et al. (2012); Jakubowski et al. (2017) |
| „Dann läuft ein kurzes Stück in Dauerschleife.“ | Ohrwürmer sind typischerweise kurze Ausschnitte (oft Refrain), die sich wiederholen | Williamson et al. (2012); Beaman & Williams (2010) |
| „Besonders hartnäckig: schnelle Songs, deren Melodie typisch verläuft, aber ein paar ungewöhnliche Sprünge macht.“ | Vergleich von 100 Ohrwurm-Songs mit 100 gleich beliebten Kontrollsongs: schnelleres Tempo, häufigerer (typischer) globaler Melodieverlauf, ungewöhnlichere Intervalle/Steigungen an Wendepunkten. „Besonders hartnäckig“ = häufiger als Ohrwurm genannt, nicht Dauer gemessen | Jakubowski, Finkel, Stewart & Müllensiefen (2017) |
| „Der Trick dagegen: Kaugummi kauen. Im Experiment kamen dadurch seltener Ohrwürmer.“ | Kaugummikauen verringerte in Experimenten die Zahl unwillkürlicher Musikgedanken (auch die bewusst abgerufenen); laut Experiment 3 nicht nur durch allgemeine Ablenkung erklärbar. Erklärung der Autoren: Kauen stört das innere Mitsprechen/Mitsingen | Beaman, Powell & Rapley (2015) |

Bewusst weggelassen: „Ohrwürmer sind unvollendete Melodien / Zeigarnik-Effekt“ (populär, aber schwach belegt),
konkrete Prozentzahlen zur Kaugummi-Wirkung (nur aus Presseberichten, nicht im Original prüfbar).

## Veröffentlichung

**TikTok-Caption:** Warum läuft ein Song stundenlang in deinem Kopf? 🎧 Das sagt die Forschung zu Ohrwürmern, plus ein überraschender Trick dagegen. Welchen Song bekommst du gerade nicht aus deinem Kopf? 👇 #ohrwurm #musik #psychologie #gehirn #wissenschaft

**YouTube-Shorts-Titel (78 Zeichen):** Warum dein Gehirn Songs in Dauerschleife spielt 🎧 #ohrwurm #psychologie #shorts
