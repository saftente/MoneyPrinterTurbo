# Rückweg-Short: Warum fühlt sich der Rückweg kürzer an? (TikTok / YouTube Shorts, 9:16, Deutsch)

Status: **fertig gerendert** (46,3 s, 1080×1920, 30 fps, −14 LUFS). Das MP4 liegt nach dem Render
unter `work/rueckweg_short.mp4` (git-ignoriert). Gleiche Pipeline wie `projects/dejavu-short`
(Pixabay-Kuratierung, Gemini-Stimme Algenib, Whisper-Wort-Timing, MoneyPrinterTurbo-Render,
Mastering), als Kopie in `tools/`, damit das Déjà-vu-Projekt unverändert bleibt.

## Ablauf

```bash
python3 projects/return-trip-short/tools/gemini_voice.py --voice Algenib            # work/voice/Algenib.wav
ffmpeg -y -i projects/return-trip-short/work/voice/Algenib.wav -af "adelay=150:all=1,apad=pad_dur=1.3" projects/return-trip-short/work/voice/Algenib_padded.wav
python3 projects/return-trip-short/tools/align.py projects/return-trip-short/work/voice/Algenib_padded.wav   # SRT + Schnitte
python3 projects/return-trip-short/tools/curate.py search      # Kontaktbögen work/sheet_XX.jpg
python3 projects/return-trip-short/tools/curate.py fetch       # laut picks.json, schreibt credits.json
python3 projects/return-trip-short/tools/curate.py cut
python3 projects/return-trip-short/tools/make_bgm.py projects/return-trip-short/work/bgm.wav && ffmpeg -y -i projects/return-trip-short/work/bgm.wav -b:a 192k projects/return-trip-short/assets/bgm_travel.mp3
./projects/return-trip-short/render.sh                          # -> work/rueckweg_short.mp4
```

Voraussetzungen wie im Déjà-vu-Projekt (README dort): `PIXABAY_API_KEY`, Gemini-Key als Network Secret
(Header `x-goog-api-key`), Hosts `huggingface.co` und `us.aws.cdn.hf.co` für Whisper, `models/whisper-medium`.

Neu gegenüber dem Déjà-vu-Projekt:
- **Hervorgehobene Wörter:** In `script.txt` mit `*Wort*` markiert. `gemini_voice.py` entfernt die Sternchen
  für die Sprachausgabe, `align.py` behält sie in den Untertiteln, `run_cli.py` färbt sie (`SUB_HIGHLIGHT`,
  #FFD23F). MoneyPrinterTurbo kennt nur eine Untertitelfarbe; der Wrapper hängt sich in dessen
  Text-Clip-Fabrik ein, ohne MoneyPrinterTurbo-Code zu ändern.
- **Musik:** eigener Generator (`tools/make_bgm.py`), 96 bpm, Am9–Fmaj7–Cadd9–G6, weiche Kick,
  Uhr-Ticken auf den Off-Beats, gezupfte Arpeggios, Riser mit leisem Impact auf „Und jetzt kommt's“
  und auf die Schlussfrage. Zeitpunkte kommen aus der Shotlist.
- `align.py` zieht die letzte Szene 0,2 s über das Audioende (sonst füllt MoneyPrinterTurbo mit Loops auf)
  und übergibt Whisper das Skript ohne Markierungen (mit Sternchen brach die Erkennung ein).

## Dateien

| Datei | Inhalt |
|---|---|
| `script.txt` | Sprechertext, 116 Wörter, `*markierte*` Schlüsselwörter |
| `shotlist.json` | 18 Szenen à 1,2–4,4 s (Zeiten aus `align.py`) mit Pixabay-Suchbegriffen |
| `picks.json` | gewählter Clip, Offset, Bildausschnitt, Push-in je Szene |
| `credits.json` | Pixabay-ID, Urheber, Link je Szene (Pixabay-Lizenz, Nennung freiwillig) |
| `assets/bgm_travel.mp3` | eigens synthetisierte, lizenzfreie Musik |
| `render.sh` | MoneyPrinterTurbo-Aufruf + Zwei-Pass-Loudnorm auf −14 LUFS |

## Aufbau

| Zeit | Teil | Inhalt |
|---|---|---|
| 0–5,9 s | Hook | „Du fährst exakt dieselbe Strecke zurück. Warum fühlt sie sich plötzlich viel kürzer an?“ |
| 5,9–13,2 s | Alltag | Urlaubsfahrt hin: endlos. Zurück: gleiche Strecke, gleiche Zeit, zack, da. |
| 13,2–31,1 s | Erklärung | Name des Effekts, bis zu 22 % kürzer, Erklärung über Erwartungen |
| 31,1–40,7 s | Überraschung | Unterwegs kein Effekt, erst im Rückblick; entsteht wohl in der Erinnerung |
| 40,7–46,3 s | Frage | „Ist das bei dir auch so, oder zieht sich bei dir ausgerechnet der Rückweg?“ |

## Faktencheck

| Aussage im Video | Einordnung | Quelle |
|---|---|---|
| „Das nennt sich Return Trip Effect.“ | Fachbegriff | van de Ven, van Rijswijk & Roy (2011), *Psychonomic Bulletin & Review* 18(5), 827–832, doi:10.3758/s13423-011-0150-5 |
| „In Experimenten wirkte der Rückweg um bis zu 22 Prozent kürzer.“ | Befund; 17 % in der Fahrradstudie, 22 % in der Videostudie, daher „bis zu“ | van de Ven et al. (2011); Zusammenfassung APS „Why the Drive Home Really Does Feel Shorter“ |
| „Forscher erklären das mit Erwartungen: Der Hinweg dauert länger als gedacht …“ | als **Erklärung der Forscher** formuliert (verletzte Erwartungen); in der Busstudie fiel der Effekt umso stärker aus, je mehr der Hinweg länger als erwartet wirkte | van de Ven et al. (2011) |
| „In einer Studie wirkte der Rückweg unterwegs gar nicht kürzer. Erst im Rückblick.“ | Befund **einer** kleinen Studie (20 Männer, Geh-Videos): Echtzeit-Schätzungen ohne Effekt, nachträgliche Schätzungen mit Effekt | Ozawa, Fujii & Kouzaki (2015), *PLOS ONE* 10(6), e0127779 |
| „Die Abkürzung entsteht also wohl erst in deiner Erinnerung.“ | als **Vermutung** formuliert („wohl“), entspricht der Deutung der Autoren | Ozawa et al. (2015) |

Bewusst weggelassen: Vertrautheit mit der Strecke als Erklärung. Van de Ven et al. fanden den Effekt auch
auf einer anderen, gleich langen Rückroute; das hätte das Video verlängert. Ebenfalls weggelassen: dass der
Effekt verschwand, wenn man Teilnehmenden vorher eine lange Fahrt ankündigte (nur aus Presseberichten
bestätigt, Volltext war aus der Umgebung nicht erreichbar).

## Veröffentlichung

**Titel:** Warum fühlt sich der Rückweg kürzer an? 🚗

**Caption:** Gleiche Strecke, gleiche Zeit, und trotzdem ist der Rückweg gefühlt viel schneller vorbei. Das steckt hinter dem Return Trip Effect. Wie ist das bei dir? 👇

**Hashtags:** #rückweg #psychologie #zeitwahrnehmung #roadtrip #wissenschaft
