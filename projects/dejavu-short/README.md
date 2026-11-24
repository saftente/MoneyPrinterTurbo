# Déjà-vu-Short (TikTok / YouTube Shorts, 9:16, Deutsch)

Status: Skript, Voiceover-Timing, Musik, Shotlist und Render-Pipeline sind fertig und getestet
(Testrender mit Platzhalter-Clips: 58,27 s, 1080×1920, Szenen bildgenau auf den Sätzen).
Offen: echte Clips von Pixabay kuratieren (braucht `PIXABAY_API_KEY`).

## Weitermachen in einer neuen Session

```bash
cd projects/dejavu-short
python3 tools/curate.py search    # Kandidaten + Kontaktbögen work/sheet_XX.jpg
# Kontaktbögen ansehen, picks.json schreiben: {"1": {"index": 0, "offset": 0.5, "focus_x": 0.5}, ...}
python3 tools/curate.py fetch     # Downloads + credits.json
python3 tools/curate.py cut       # work/clips/scene_XX.mp4 (1080x1920, Grade, bildgenau)
./render.sh                       # MoneyPrinterTurbo-Render -> storage/tasks/<id>/final-1.mp4
```

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
| `render.sh` | MoneyPrinterTurbo-CLI-Aufruf: lokale Clips sequenziell, harte Schnitte, Wort-für-Wort-Untertitel mit Pop-Animation, BeVietnamPro Bold 118 px, Musik −13 dB unter der Stimme |

## Aufbau

| Zeit | Teil | Text |
|---|---|---|
| 0–3,2 s | Hook | Dein Gehirn lügt dich manchmal an – und du spürst es. |
| 3,2–14,7 s | Phänomen | Raum, Satz, „genau das hast du schon mal erlebt“, dann weg |
| 14,7–42,8 s | Erklärung | ~2/3 kennen es · Hypothese 1: Ähnlichkeit ohne abrufbare Erinnerung (VR-Experimente) · Hypothese 2: Kontroll-/Konfliktsignal |
| 42,8–55,6 s | Überraschung | Vorhersagegefühl im Déjà-vu, Trefferquote auf Zufallsniveau |
| 55,6–58,2 s | Ende | Wann hattest du dein letztes Déjà-vu? |

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
