# Déjà-vu-Short (TikTok / YouTube Shorts, 9:16, Deutsch)

Status: **fertig gerendert** mit Gemini-Stimme „Algenib“ (63,1 s, 1080×1920, 30 fps, −14 LUFS) und
23 kuratierten Pixabay-Clips (`picks.json`, Quellen in `credits.json`). Das MP4 liegt nach dem
Render unter `work/dejavu_short.mp4` (git-ignoriert, also nicht im Repo).

Die aktuelle Vertonung stammt von `gemini-3.8-flash-lite-tts`, weil das Free-Tier-Tageslimit
(10 Anfragen pro Modell) für `gemini-3.8-flash-tts` aufgebraucht war. Mit dem Vollmodell neu vertonen:
siehe „Neue Stimme“ unten (Standardmodell in `gemini_voice.py`).

## Neue Stimme (Gemini TTS)

Edge-TTS ist keine Option mehr: Alle deutschen Edge-Männerstimmen liefern dieselbe Aufnahme,
die Frauenstimmen ebenso. Gemini braucht einen Key als Network Secret der Umgebung:
Typ Bearer, Host `generativelanguage.googleapis.com`, Header `x-goog-api-key`, Präfix leer.
Whisper (für die Wort-Untertitel) braucht die Hosts `huggingface.co` und `us.aws.cdn.hf.co`.

```bash
python3 projects/dejavu-short/tools/gemini_voice.py --voice Algenib          # work/voice/Algenib.wav
ffmpeg -y -i projects/dejavu-short/work/voice/Algenib.wav -af apad=pad_dur=1.3 projects/dejavu-short/work/voice/Algenib_padded.wav
python3 projects/dejavu-short/tools/align.py projects/dejavu-short/work/voice/Algenib_padded.wav   # SRT + Schnitte in shotlist.json
# letzte Szene in shotlist.json ~0,2 s über das Audioende ziehen, sonst füllt MoneyPrinterTurbo mit Clip-Loops auf
python3 projects/dejavu-short/tools/make_bgm.py projects/dejavu-short/work/bgm.wav && ffmpeg -y -i projects/dejavu-short/work/bgm.wav -b:a 192k projects/dejavu-short/assets/bgm_mystery.mp3
python3 projects/dejavu-short/tools/curate.py cut
VOICE_FILE=projects/dejavu-short/work/voice/Algenib_padded.wav ./projects/dejavu-short/render.sh
```

Stilsteuerung: Gemini liest eine normale Anweisung im Prompt mit vor, und Systemanweisungen lehnen
die TTS-Modelle ab. Deshalb nutzt `gemini_voice.py` das Format mit Regieanweisungen über einem
`#### TRANSCRIPT`-Abschnitt; nur der Transkriptteil wird gesprochen. Eine Längenprüfung bricht ab,
falls doch Anweisungen gesprochen wurden. `align.py` liegt am alten Edge-Voiceover gemessen im Mittel
0,05 s neben den echten Wortgrenzen. Die Musik (`make_bgm.py`) liest Länge und Riser-Zeitpunkte
aus der Shotlist (Riser enden auf Szene 18 und 23).

## Neue Cloud-Umgebung einrichten (claude.ai/code)

1. Neue Umgebung anlegen, Netzwerk **Limited** (Paketmanager erlaubt), erlaubte Hosts:
   `speech.platform.bing.com`, `pixabay.com`, `cdn.pixabay.com`
2. Umgebungsvariable: `PIXABAY_API_KEY=<dein Key>` (Key unter pixabay.com/api/docs/, eingeloggt).
   Der Key gehört nur in die Umgebung, nie in das Repo oder den Chat; `config.toml` ist git-ignoriert.
3. Neue Session mit dieser Umgebung, Repo `saftente/moneyprinterturbo`, Branch
   `claude/great-wozniak-7mf5zn` starten und schreiben: „Mach mit projects/dejavu-short weiter (README).“

Prüfen, ob der Key ankommt: `test -n "$PIXABAY_API_KEY" && echo ok`.

## Weitermachen in einer neuen Session

```bash
python3 projects/dejavu-short/tools/curate.py search    # Kandidaten + Kontaktbögen work/sheet_XX.jpg
python3 projects/dejavu-short/tools/curate.py fetch     # Downloads laut picks.json + credits.json
python3 projects/dejavu-short/tools/curate.py cut       # work/clips/scene_XX.mp4 (1080x1920, Grade, bildgenau)
./projects/dejavu-short/render.sh                       # Render + Mastering -> work/dejavu_short.mp4
```

Einzelne Szenen neu suchen oder schneiden: `curate.py search 9 16`, `curate.py cut 21`
(`search` mit IDs ersetzt nur diese Einträge in `work/candidates.json`, die Indizes in
`picks.json` beziehen sich auf die jeweils aktuelle Kandidatenliste).

Felder in `picks.json` pro Szene: `index` (Kandidat), `offset` (Startsekunde im Quellclip),
`focus_x` (0–1, horizontaler Bildausschnitt beim 9:16-Crop), optional `zoom` (langsamer
Push-in, 0.1 = 10 % enger) und `speed` (Zeitraffer-Faktor).

Hinweise zur Suche: Pixabay verknüpft Suchwörter mit ODER, darum behält `search` nur Treffer,
deren Tags alle Wörter der Suchanfrage enthalten, verwirft alles unter 720p-Niveau und sortiert
nach Schärfe beim 9:16-Crop (Hochformat/4K zuerst). Medizin/VR/Neuro-Material ist bei Pixabay
dünn („mri“: 0 Treffer, „neuron“: 3).

Voraussetzungen: `pip install -r requirements.txt`, `cp config.example.toml config.toml`.
`tools/sitecustomize.py` (per `PYTHONPATH` in `render.sh`) lässt edge-tts der CA des
Cloud-Proxys vertrauen; lokal ist das wirkungslos und schadet nicht.

## Dateien

| Datei | Inhalt |
|---|---|
| `script.txt` | Sprechertext (140 Wörter, ~62 s mit Gemini Algenib) |
| `shotlist.json` | 23 Szenen mit Zeitstempeln (aus `align.py`) und Pixabay-Suchbegriffen |
| `assets/voiceover.*` | Altes Edge-Referenz-Voiceover + Satz-SRT (Prüfstein für `align.py`) |
| `assets/bgm_mystery.mp3` | Eigens synthetisierte, lizenzfreie Ambient-Musik (d-Moll-Pad, Herzschlag-Puls, Glocken-Motiv, Riser vor der Pointe), siehe `tools/make_bgm.py` |
| `render.sh` | MoneyPrinterTurbo-CLI-Aufruf: lokale Clips sequenziell, harte Schnitte, Wort-für-Wort-Untertitel mit Pop-Animation, BeVietnamPro Bold 118 px, Musik −13 dB unter der Stimme, Clips bis 8 s (Szenen sind 1,6–5,1 s); `VOICE_FILE` nimmt ein fertiges Voiceover samt `align.py`-Untertiteln; danach Zwei-Pass-Loudnorm auf −14 LUFS / −1,5 dBTP (Video unverändert kopiert) |
| `picks.json` | Gewählter Clip, Offset, Bildausschnitt, Push-in je Szene |
| `credits.json` | Pixabay-ID, Urheber und Link je Szene (Pixabay-Lizenz, Nennung freiwillig) |

## Aufbau

| Zeit | Teil | Text |
|---|---|---|
| 0–4,3 s | Hook | Dein Gehirn lügt dich manchmal an – und du spürst es. |
| 4,3–16,9 s | Phänomen | Raum, Satz, „genau das hast du schon mal erlebt“, dann weg |
| 16,9–46,4 s | Erklärung | ~2/3 kennen es · Hypothese 1: Ähnlichkeit ohne abrufbare Erinnerung (VR-Experimente) · Hypothese 2: Kontroll-/Konfliktsignal |
| 46,4–59,7 s | Überraschung | Vorhersagegefühl im Déjà-vu, Trefferquote auf Zufallsniveau |
| 59,7–63,1 s | Ende | Wann hattest du dein letztes Déjà-vu? |

## Bildauswahl (Retention)

- **Hook:** Makro-Iris mit Push-in, das Auge schließt sich genau am Satzende; Szene 2 taucht durch
  eine Pupille ins Neuron (kurzer Glitch-Übergang statt Standbild).
- **Loop:** Das Video endet auf einem Gesicht, das die Augen öffnet und in die Kamera schaut, während
  die Frage gestellt wird. Das spiegelt das sich schließende Auge am Anfang.
- **Raum-Hypothese:** zwei unterschiedlich eingerichtete, ähnlich aufgebaute Wohnzimmer hintereinander (Szenen 10/11).
- **Pointe:** Roulette-Kugel fällt genau bei „reines Zufallsniveau“ ins Fach.
- Statische Einstellungen haben einen langsamen Push-in, sodass in keiner Szene das Bild steht.
  Schnitt alle 1,5–3,4 s.

## Faktencheck

| Aussage im Video | Einordnung | Quelle |
|---|---|---|
| „Rund zwei von drei Menschen kennen dieses Déjà-vu.“ | Umfragen, ca. 2/3 Lebenszeitprävalenz | Brown (2003), *Psychological Bulletin* 129(3); Brown (2004), *The Déjà Vu Experience* |
| Ähnlichkeit mit Erlebtem (z. B. Raumaufbau) ohne abrufbare Erinnerung | als **Hypothese** formuliert („Eine führende Hypothese“) | Cleary et al. (2012), *Consciousness and Cognition* 21(2), 969–975 (VR-Studie) |
| „In Experimenten mit virtuellen Räumen ließ sich genau das auslösen.“ | Mehr Déjà-vu-Berichte bei Szenen mit gleicher räumlicher Anordnung, wenn die Ursprungsszene nicht erinnert wurde | Cleary et al. (2012) |
| Kontrollsignal: Gehirn merkt falsche Vertrautheit und prüft nach | als **Vermutung** formuliert („Andere Forscher vermuten“) | Urquhart, Sivakumaran, Macfarlane & O'Connor (2021), *Memory* 29(7) (fMRI, frontale/cingulare Areale) |
| Vorhersagegefühl, Trefferquote auf Zufallsniveau | experimenteller Befund | Cleary & Claxton (2018), *Psychological Science* 29(4), 635–644 |

Bewusst weggelassen: die Behauptung „Déjà-vus sind ein Zeichen für ein gesundes Gehirn“
(Medienzuspitzung, so nicht belegt). Hintergrund, nicht im Video: Elektrische Stimulation
des entorhinalen Kortex kann Déjà-vus auslösen (Bartolomei et al., 2004, *Neurology* 63);
Déjà-vus werden mit dem Alter seltener (Teale & O'Connor, 2015, *Frontiers for Young Minds*).

## Veröffentlichung

**Titel:** Dein Gehirn lügt dich an – das steckt hinter Déjà-vus

**Caption:** Schon mal das Gefühl gehabt, einen Moment exakt so schon erlebt zu haben? 🌀
Das sagt die Forschung bisher und was dein Gehirn dabei vielleicht macht. Wann hattest du dein letztes Déjà-vu? 👇

**Hashtags:** #dejavu #gehirn #psychologie #wissenschaft #lernenmittiktok
