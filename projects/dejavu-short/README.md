# Déjà-vu-Short (TikTok / YouTube Shorts, 9:16, Deutsch)

Status: **fertig gerendert** (58,3 s, 1080×1920, 30 fps, −14 LUFS) mit 23 kuratierten Pixabay-Clips
(`picks.json`, Quellen in `credits.json`). Das MP4 liegt nach dem Render unter
`work/dejavu_short.mp4` (git-ignoriert, also nicht im Repo).

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
| `script.txt` | Sprechertext (140 Wörter, ~58 s bei Stimme Florian, Rate 1.14) |
| `shotlist.json` | 23 Szenen à 1,5–3,4 s mit Zeitstempeln und Pixabay-Suchbegriffen |
| `assets/voiceover.*` | Referenz-Voiceover + Satz-SRT (MoneyPrinterTurbo erzeugt es beim Render identisch neu) |
| `assets/bgm_mystery.mp3` | Eigens synthetisierte, lizenzfreie Ambient-Musik (d-Moll-Pad, Herzschlag-Puls, Glocken-Motiv, Riser vor der Pointe), siehe `tools/make_bgm.py` |
| `render.sh` | MoneyPrinterTurbo-CLI-Aufruf: lokale Clips sequenziell, harte Schnitte, Wort-für-Wort-Untertitel mit Pop-Animation, BeVietnamPro Bold 118 px, Musik −13 dB unter der Stimme; danach Zwei-Pass-Loudnorm auf −14 LUFS / −1,5 dBTP (Video unverändert kopiert) |
| `picks.json` | Gewählter Clip, Offset, Bildausschnitt, Push-in je Szene |
| `credits.json` | Pixabay-ID, Urheber und Link je Szene (Pixabay-Lizenz, Nennung freiwillig) |

## Aufbau

| Zeit | Teil | Text |
|---|---|---|
| 0–3,2 s | Hook | Dein Gehirn lügt dich manchmal an – und du spürst es. |
| 3,2–14,7 s | Phänomen | Raum, Satz, „genau das hast du schon mal erlebt“, dann weg |
| 14,7–42,8 s | Erklärung | ~2/3 kennen es · Hypothese 1: Ähnlichkeit ohne abrufbare Erinnerung (VR-Experimente) · Hypothese 2: Kontroll-/Konfliktsignal |
| 42,8–55,6 s | Überraschung | Vorhersagegefühl im Déjà-vu, Trefferquote auf Zufallsniveau |
| 55,6–58,2 s | Ende | Wann hattest du dein letztes Déjà-vu? |

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
