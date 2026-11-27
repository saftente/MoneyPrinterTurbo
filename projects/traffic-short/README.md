# Stau-Short: Woher weiß Google Maps, dass gerade Stau ist? (TikTok / YouTube Shorts, 9:16, Deutsch)

Status: **fertig gerendert** (53,3 s; 1080×1920, 30 fps, −14 LUFS, Endkontrolle bestanden).
MP4 nach dem Render: `work/stau_short.mp4` (git-ignoriert).

17 von 18 Szenen sind **eigene Animationen** (`tools/animate.py`, pycairo); nur „wo gerade Stau ist“ ist ein
Stockvideo (Pixabay 84970, in keinem früheren Projekt verwendet; `curate.py` sperrt alle IDs aus anderen
Projekten). Heller Look statt der dunklen Grade der früheren Videos.

## Ablauf

```bash
python3 projects/traffic-short/tools/gemini_voice.py --voice Algenib
ffmpeg -y -i projects/traffic-short/work/voice/Algenib.wav -af "adelay=150:all=1,apad=pad_dur=0.8" projects/traffic-short/work/voice/Algenib_padded.wav
python3 projects/traffic-short/tools/align.py projects/traffic-short/work/voice/Algenib_padded.wav
python3 projects/traffic-short/tools/verify_take.py projects/traffic-short/work/voice/Algenib_padded.wav --scenes   # Abnahme der Stimme
python3 projects/traffic-short/tools/animate.py              # 17 Animationsszenen -> work/clips/
python3 projects/traffic-short/tools/curate.py fetch && python3 projects/traffic-short/tools/curate.py cut   # Stockszene 2
python3 projects/traffic-short/tools/group_subs.py
python3 projects/traffic-short/tools/make_bgm.py projects/traffic-short/work/bgm.wav && ffmpeg -y -i projects/traffic-short/work/bgm.wav -b:a 192k projects/traffic-short/assets/bgm_groove.mp3
./projects/traffic-short/render.sh
python3 projects/traffic-short/tools/verify_take.py projects/traffic-short/work/stau_short.mp4 --scenes   # Abnahme des fertigen Videos
```

`animate.py --still <szene> <0..1>` rendert ein Einzelbild zur Kontrolle.

## Animationen (je ein Erklärschritt)

| Szene | Bild |
|---|---|
| 1 | Erster Frame: Karte mit rotem Stauabschnitt, „STAU“-Label, Handy mit Funkwellen |
| 3 | Einstellungen-Mockup, Schalter „Standort“ springt bei „Standorterfassung“ auf AN |
| 4 | Autos auf der Hauptstraße, Handys senden Datenpakete an einen Server, Label „anonym“ |
| 5–6 | Zwei Positionen mit Uhrzeit (12:00:00 / 12:00:05), 150 m → Tacho zeigt 108 km/h |
| 7–8 | Tempo vieler Autos (96, 104 …) verschmilzt zu „Ø 100 km/h“; Handys werden zu identischen Punkten |
| 9–10 | Autos rücken zusammen, „sonst 100 / jetzt 25 km/h“; Straße färbt sich exakt bei „orange“ und „rot“ |
| 11–13 | Neuronales Netz; Eingänge „jetzt“ + „historisch“; typischer Tagesverlauf mit Spitzen morgens und abends (illustrativ) |
| 14–15 | Prognose-Zeitleiste +10/+20/+50 min (bei den gesprochenen Zahlen); Route wechselt auf die Alternative, 32 → 24 min |
| 16–18 | „Berlin, 2020 – Simon Weckert“; Bollerwagen mit 99 Handys auf leerer Straße; die Straße wird rot, „0 Autos“ |

Wortgenaues Timing: `animate.py` liest `work/voice/subtitle_words.srt`. Inhalte liegen über y = 1250 px,
die Untertitel (88 px, Wortgruppen, gelbe Schlüsselbegriffe) bei 74 % der Höhe.

## Qualitätssicherung (neu)

- **Abnahme pro Szene** (`verify_take.py --scenes`): Über die ganze Datei „hört“ Whisper verschluckte Wörter
  aus dem Kontext richtig. Szene für Szene fiel auf, dass eine Aufnahme „schlägt dir“ als „schlägt ihr“
  sprach. „dir“ wurde gestrichen, die Aufnahme ersetzt. Das fertige MP4 besteht beide Prüfungen.
- **Riser nur in Sprechpausen** (`make_bgm.py`): Ein Rausch-Riser unter „rot“ machte daraus „ruht“.
  Riser beginnen jetzt erst nach dem letzten Wort vor dem Szenenwechsel.
- Rausch-Fix am Voiceover-Ende, Limiter, Fade-out und `check_tail.py` wie bisher; alle Schnitte bildgenau.

## Faktencheck

| Aussage im Video | Einordnung | Quelle |
|---|---|---|
| „Dein Handy verrät Google Maps, wo gerade Stau ist. Zumindest, wenn die Standorterfassung an ist.“ | Google: Ist die Standorterfassung (location data collection) an, sendet das Handy anonyme Daten, die helfen, Staus zu erkennen. Der vorgeschlagene Hook „selbst ohne gestartete Route“ steht so in keiner offiziellen Quelle und wurde **nicht** verwendet | Google Maps Hilfe, support.google.com/maps/answer/6194894 |
| „Dann schickt es immer wieder anonyme Positionsdaten an Google.“ | wie oben | Google Maps Hilfe; Google Blog 2009 „The bright side of sitting in traffic“ |
| „Aus zwei Positionen und der Zeit dazwischen ergibt sich, wie schnell du fährst.“ | Prinzip (Weg/Zeit). Google beschreibt, dass die Daten zeigen, wie schnell man unterwegs ist; die Zahlen im Bild (150 m, 5 s) sind ein Rechenbeispiel | Google Blog 2009 |
| „Google kombiniert die Daten vieler Handys auf derselben Straße, ohne einzelne Geräte zu erkennen.“ | Google: „Wir kombinieren anonyme Daten von deinem Handy und anderen Handys, sodass niemand dein Gerät ausfindig machen kann“; Start und Ziel werden gelöscht | Google Maps Hilfe |
| „Fahren plötzlich alle viel langsamer als sonst, wird die Straße orange, dann rot.“ | Farben laut Google: grün = keine Verzögerung, orange = mittleres Verkehrsaufkommen, rot = Verzögerung. „Als sonst“ verweist auf die historischen Muster (nächster Satz); die genaue Schwelle veröffentlicht Google nicht | Google Maps Hilfe (Verkehrsfarben); Google Blog 2020 |
| „Für die Vorhersage nutzt Google maschinelles Lernen: Es verbindet den Verkehr von jetzt mit historischen Mustern …“ | Google: Datenbank historischer Verkehrsmuster kombiniert mit Live-Verkehr, maschinelles Lernen erzeugt Vorhersagen | Google Blog 2020 „Google Maps 101: How AI helps predict traffic and determine routes“ |
| „So schätzt Google Maps den Verkehr in zehn, zwanzig oder fünfzig Minuten …“ | Google nennt genau diese Zeiträume (10, 20, 50 Minuten in die Fahrt hinein) | Google Blog 2020 |
| „… und schlägt eine schnellere Route vor.“ | ETA-Vorhersagen ranken Routen; bei erwartetem starkem Verkehr sucht Maps automatisch eine Alternative | Google Blog 2020; DeepMind Blog 2020 |
| „2020 … Simon Weckert: 99 Smartphones mit laufender Navigation in einem Bollerwagen durch Berlin. Auf der Karte: Stau auf fast leeren Straßen.“ | Februar 2020, 99 Android-Handys mit eigener SIM, Navigation in Google Maps aktiv, Straßen zeigten virtuellen Stau. Bewusst **nicht** behauptet, dass es heute noch so funktioniert | Weckert, „Google Maps Hacks“ (2020); Berichte u. a. Hyperallergic, The Next Web, Android Authority; Google-Stellungnahme dazu |

Bewusst weggelassen: Waze-Meldungen und Behördendaten als weitere Quellen (für Google Maps nicht offiziell
im Detail belegt), Prozentangaben zur Genauigkeit (DeepMind: ETAs bis zu 50 % genauer in einzelnen Städten).

## Veröffentlichung

**TikTok-Caption:** Woher weiß Google Maps eigentlich, wo Stau ist? 🚗📱 Dein Handy liefert die Daten, und so wird daraus eine rote Straße. Plus: das Experiment mit 99 Smartphones im Bollerwagen. #googlemaps #stau #technik #wissen #lernenmittiktok

**YouTube-Shorts-Titel (73 Zeichen):** Woher weiß Google Maps, dass Stau ist? 🚗 #googlemaps #technik #shorts
