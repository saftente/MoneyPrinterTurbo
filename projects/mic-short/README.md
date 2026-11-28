# Mikrofon-Short: Hören uns unsere Apps heimlich ab? (TikTok / YouTube Shorts, 9:16, Deutsch)

Status: **fertig gerendert** (73,0 s; 1080×1920, 30 fps, −14 LUFS, Endkontrolle bestanden).
MP4 nach dem Render: `work/mikro_short.mp4` (git-ignoriert). Alle 23 Szenen sind **eigene Animationen**
(`tools/animate.py`, pycairo), kein Stockmaterial. Der Film „STERNENFALL“ ist erfunden, die App-Oberfläche
generisch („Für dich“, keine Plattform-Logos).

## Ablauf

```bash
python3 projects/mic-short/tools/gemini_voice.py --voice Algenib
python3 projects/mic-short/tools/patch_voice.py projects/mic-short/work/voice/Algenib.wav 1 4 6   # nur fehlerhafte Sätze neu (s. u.)
ffmpeg -y -i projects/mic-short/work/voice/Algenib.wav -af atempo=1.08 ...   # siehe "Tempo"
ffmpeg -y -i projects/mic-short/work/voice/Algenib.wav -af "adelay=150:all=1,apad=pad_dur=0.8" projects/mic-short/work/voice/Algenib_padded.wav
python3 projects/mic-short/tools/align.py projects/mic-short/work/voice/Algenib_padded.wav
python3 projects/mic-short/tools/verify_take.py projects/mic-short/work/voice/Algenib_padded.wav --scenes
python3 projects/mic-short/tools/animate.py
python3 projects/mic-short/tools/group_subs.py
python3 projects/mic-short/tools/make_bgm.py projects/mic-short/work/bgm.wav && ffmpeg -y -i projects/mic-short/work/bgm.wav -b:a 192k projects/mic-short/assets/bgm_groove.mp3
./projects/mic-short/render.sh
python3 projects/mic-short/tools/verify_take.py projects/mic-short/work/mikro_short.mp4 --scenes
```

## Vertonung: was diesmal anders war

- **Gemini erfindet Text:** In zwei von sechs Aufnahmen hängte Gemini eigene Sätze an („Findest du das praktisch
  oder eher gruselig?“, „…fühlst du dich jetzt ertappt…“) oder wiederholte einen Satz aus der Sprechanweisung.
  Die Wort-für-Wort-Abnahme hat beides abgelehnt. Die Sprechanweisung zitiert keine Skriptsätze mehr und verlangt
  ausdrücklich wörtliches Lesen.
- **`tools/patch_voice.py`:** Bei rund 190 Wörtern enthielt jede Aufnahme irgendwo einen kleinen Fehler. Statt
  weiterer kompletter Aufnahmen (Kontingent 10 pro Tag) werden nur die fehlerhaften Sätze in einer Anfrage neu
  gesprochen und an den Sprechpausen eingeschnitten (15-ms-Überblendungen, gleiche Lautheit, keine Klicks;
  geprüft). Ein eingesetzter Satz war 1,7 dB lauter und wurde angeglichen.
- **Tempo:** Die Aufnahme (77,7 s, 2,5 Wörter/s) ist mit `atempo=1.08` (tonhöhenerhaltend) auf 2,7 Wörter/s
  beschleunigt; die Abnahme lief danach erneut.
- **`verify_take.py`:** kurze Szenen (< 1,5 s) werden mit ihren Nachbarn geprüft (0,6 s Audio allein ließen
  Whisper „öffnest“ als „öffne das“ hören); Schreibvarianten wie „orangenfarbenen“/„orangefarbenen“ gelten als gleich.
- **`render.sh`** bricht ab, wenn nicht jede Szene ihren bildgenauen Clip hat. Ein abgestürztes Animationsskript
  hatte zuvor dazu geführt, dass MoneyPrinterTurbo fehlende Szenen mit Loops auffüllte.

Endabnahme: Das Transkript des fertigen MP4 stimmt über die ganze Datei und Szene für Szene mit dem Skript.
Alle 22 Schnitte bildgenau, letzte 3 s ohne Störgeräusch (Ende −74 dBFS).

## Faktencheck

| Aussage im Video | Einordnung | Quelle |
|---|---|---|
| „Technisch könnten Apps das Mikrofon nutzen, aber nur mit deiner Erlaubnis.“ | Mikrofonzugriff ist eine Laufzeitberechtigung unter Android und iOS | Android-/iOS-Berechtigungsmodell; Kröger & Raschke (2019) |
| „Neuere Handys zeigen dann einen grünen oder orangefarbenen Punkt.“ | Android ab Version 12 (grün), iOS ab Version 14 (orange) | Android 12 / iOS 14 Datenschutzanzeigen |
| „Eine Studie testete 2018 über 17.000 Android-Apps. Ergebnis: keine App schickte heimlich Audio.“ | 17.260 Apps; keine App versandte Audio oder aktivierte das Mikrofon unaufgefordert. Grenzen laut Autoren: automatisierte Tests ohne Login; lokal transkribierte Sprache wäre womöglich unentdeckt geblieben | Pan, Ding, Hu, Choffnes, Wilson (2018), „Panoptispy“, *PoPETs* 2018(4), 33–50; Northeastern News (2018) |
| „Dafür schickten manche unbemerkt Bildschirmaufnahmen an Dritte.“ | Analyse-Bibliotheken zeichneten Bildschirm/Screenshots auf und schickten sie an Dritte, ohne Hinweis (z. B. GoPuff → Appsee) | Panoptispy (2018) |
| „Ein Beweis für heute ist das nicht. Für heimliches Abhören durch große Plattformen fehlt aber jeder Beleg.“ | Studie von 2018 kann heutige Apps nicht ausschließen; Kröger & Raschke: keine empirischen Belege, aber nicht ausschließbar. 2024 warb die Werbefirma Cox Media Group mit „Active Listening“; Belege fehlen, Google entfernte die Firma aus seinem Partnerprogramm, Meta bestreitet Mikrofonnutzung für Werbung (im Video bewusst nicht als Nachweis dargestellt) | Kröger & Raschke (2019); 404 Media (2024) |
| „TikTok weiß nicht, in welchem Film du warst.“ | TikTok nennt als Empfehlungssignale Interaktionen, angesehene Videos, Videoinformationen; kein Kinobesuch | TikTok Newsroom (2020); TikTok Transparency Center |
| „Aber neue Filme sind Trends: Tausende sehen sie, viele posten Edits.“ | Erklärung (Aktualität/Trend), kein Messwert | – |
| „Und die App misst, wie lange du hinschaust. Bleibst du … hängen, wertet sie das als Interesse …“ | TikTok: angesehene Videos und ob ein Video zu Ende geschaut wird als starke Interessensignale; Instagram: Wahrscheinlichkeit, ein Reel zu Ende zu schauen, gehört zu den wichtigsten Vorhersagen | TikTok Newsroom (2020); Instagram „Ranking Explained“ (Mosseri, 2023) |
| „Dazu kommen Likes, Suchen und was Menschen mit ähnlichem Verhalten mögen.“ | Interaktionen laut TikTok/Instagram; Vergleich mit ähnlichen Nutzern ist das Grundprinzip von Empfehlungssystemen (kollaboratives Filtern) | TikTok Newsroom; Instagram (2023) |
| „Bei Werbung können je nach Einstellungen auch Daten von Partnern zählen, etwa ein online gekauftes Ticket.“ | TikTok-Datenschutzerklärung: Werbe- und Messpartner teilen Informationen über Aktivitäten außerhalb der Plattform, inkl. Käufen; abhängig von Einwilligungen | TikTok Privacy Policy |
| „Und dann die Frequenzillusion …“ | Begriff von Arnold Zwicky (2005), auch Baader-Meinhof-Phänomen | Zwicky (2005), Language Log |

Die Prozentanzeige in der Animation „Interessen-Prognose“ ist eine Illustration, kein Messwert.

## Veröffentlichung

**TikTok-Caption:** Kino, TikTok öffnen und plötzlich nur noch Edits von genau diesem Film. Hört dein Handy mit? 🎬📱 Das sagt die Forschung, und so kommen die Empfehlungen wirklich zustande. #handy #datenschutz #algorithmus #tiktokwissen #psychologie

**YouTube-Shorts-Titel (73 Zeichen):** Hört dein Handy heimlich mit? Die Wahrheit 🎬 #datenschutz #algorithmus #shorts
