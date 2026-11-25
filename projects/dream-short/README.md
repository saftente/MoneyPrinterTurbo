# Traum-Short: Warum träumen wir manchmal von Dingen, die später passieren? (TikTok / YouTube Shorts, 9:16, Deutsch)

Status: **fertig gerendert** (48,5 s, 1080×1920, 30 fps, −14 LUFS, Endkontrolle bestanden). Das MP4 liegt
nach dem Render unter `work/traum_short.mp4` (git-ignoriert). Pipeline wie `projects/return-trip-short`
(Pixabay, Gemini-Stimme Algenib, Whisper-Wort-Timing, gelbe Schlüsselwörter, MoneyPrinterTurbo, Mastering),
als Kopie in `tools/`, plus die Behebung des Rauschens am Videoende.

## Ablauf

```bash
python3 projects/dream-short/tools/gemini_voice.py --voice Algenib        # entfernt Rausch-Bursts, prüft die Ränder
ffmpeg -y -i projects/dream-short/work/voice/Algenib.wav -af "adelay=150:all=1,apad=pad_dur=1.0" projects/dream-short/work/voice/Algenib_padded.wav
python3 projects/dream-short/tools/align.py projects/dream-short/work/voice/Algenib_padded.wav
python3 projects/dream-short/tools/curate.py search && python3 projects/dream-short/tools/curate.py fetch && python3 projects/dream-short/tools/curate.py cut
python3 projects/dream-short/tools/make_bgm.py projects/dream-short/work/bgm.wav && ffmpeg -y -i projects/dream-short/work/bgm.wav -b:a 192k projects/dream-short/assets/bgm_mystery.mp3
./projects/dream-short/render.sh       # Render, Mastering mit Fade-out, check_tail.py; bricht bei Störgeräusch ab
```

`KEEP_RAW=1` behält die rohe Gemini-Antwort (`work/voice/Algenib.raw.wav`); `gemini_voice.py --from-raw <datei>`
verarbeitet sie ohne neue API-Anfrage (Free Tier: 10 Anfragen pro Tag und Modell).

## Das Rauschen am Ende der bisherigen Videos

**Ursache:** Gemini TTS hängt manchmal ein kurzes Stück Datenmüll an das Ende der PCM-Antwort: rund 0,2–0,3 s
breitbandiges Rauschen (spektrale Flachheit 0,82, Sprache liegt bei 0,3–0,4) mit Spitzen bis 0 dBFS, nach einer
Pause von rund 0,5 s Stille. Die alte Verarbeitung (Stille an den Rändern trimmen, `loudnorm`) behielt es, weil
es laut ist. Es landete in `Algenib.wav`, damit im Voiceover und im fertigen Video: Déjà-vu bei 61,7 s,
Rückweg bei 44,7 s, jeweils ein Sprung um rund +20 dB aus der Stille. Musik, MoneyPrinterTurbo-Mix, AAC-Codierung
und Mastering waren nicht die Ursache (einzeln gemessen). Auch bei einer Testanfrage für dieses Video steckte
der Burst in der Rohantwort.

**Behebung (dauerhaft, in der Pipeline):**
1. `gemini_voice.py` / `strip_bursts()`: erkennt am Ende (und gespiegelt am Anfang) ein höchstens 0,6 s langes,
   spektral flaches, lautes Segment nach mindestens 0,15 s Stille und schneidet es weg. Die natürliche
   Ausklingzeit (bis 0,2 s) bleibt. Getestet: echte Wörter nach einer Pause bleiben erhalten.
2. Fades: 40 ms an den Rändern des bereinigten Voiceovers, 0,25 s Ausklang nach dem letzten Wort, 120 ms Fade-out
   nach `loudnorm`; im Mastering 1,5 s Fade-out der Gesamtmischung (zusätzlich zu den 3 s Musik-Fade von
   MoneyPrinterTurbo).
3. `check_quiet_edges()`: lehnt ein Voiceover ab, dessen Ende nicht leise ist.
4. `tools/check_tail.py` (letzter Schritt von `render.sh`): decodiert die letzten 3 s der fertigen MP4 kanalweise
   in 20-ms-Fenstern und bricht ab bei Spitzen über −1 dBFS, Sprüngen über +18 dB aus der Stille oder einem
   lauten Ende. Die beiden alten Videos fallen genau an der Rauschstelle durch, das neue besteht
   (Spitze −2,2 dBFS, Ende −66 dBFS).

Dazu im Mastering ein Limiter bei −2 dBFS, damit die AAC-decodierten Spitzen sicher unter −1 dBFS bleiben.
Fehlalarm unterwegs: Ein Downmix auf Mono (`-ac 1`) addiert zwei gleiche Kanäle mit je 0,707 (+3 dB) und zeigte
Spitzen über 0 dBFS, die es nicht gibt; `check_tail.py` misst deshalb jeden Kanal einzeln.

## Aufbau

| Zeit | Teil | Inhalt |
|---|---|---|
| 0–4,4 s | Hook | „Hast du schon mal etwas geträumt, das Tage später tatsächlich passiert ist?“ |
| 4,4–9,9 s | Beispiel | Traum von einer alten Freundin, zwei Tage später schreibt sie. Gänsehaut. |
| 9,9–17,7 s | Zufall | Fast jede Nacht Träume, die meisten vergessen; bei so vielen trifft einer zufällig |
| 17,7–23,8 s | Selektives Erinnern | Experiment: passende Träume besser erinnert als unpassende |
| 23,8–32,7 s | Zukunftssimulation | Etwa jeder vierte Traum mit kommenden Ereignissen verbunden, oft gemischt mit Erinnerungen |
| 32,7–45,4 s | Schlaflabor + Einordnung | Kein Hinweis auf Vorahnung; zuverlässig nachgewiesen ist es nicht |
| 45,4–48,5 s | Frage | „Ist dir so etwas auch schon einmal passiert?“ |

## Faktencheck

| Aussage im Video | Einordnung | Quelle |
|---|---|---|
| „Du träumst fast jede Nacht, und die meisten Träume vergisst du.“ | gut belegtes Grundlagenwissen der Schlafforschung (Allgemeinwissen, kein Studienzitat) | – |
| „Bei so vielen Träumen trifft irgendwann einer zufällig.“ | statistisches Argument, als Erklärung formuliert | – |
| „In einem Experiment merkten sich Teilnehmer passende Träume besser als unpassende.“ | Studie 1: Teilnehmende lasen ein Traumtagebuch und ein Ereignistagebuch und erinnerten Traum-Ereignis-Paare, die zusammenpassten, besser als unpassende (selective recall) | Watt, Ashley, Gillett, Halewood & Hanson (2014), *International Journal of Dream Research* 7(1), 1–8, doi:10.11588/ijodr.2014.1.11218 |
| „In einer Studie hing etwa jeder vierte Traum mit kommenden Ereignissen zusammen, oft vermischt mit Erinnerungen.“ | Teilnehmende ordneten 25,7 % ihrer Traumberichte mindestens einem erwarteten zukünftigen Ereignis zu (53,5 % einer vergangenen Erinnerung); 37,4 % der zukunftsbezogenen Träume enthielten zusätzlich konkrete vergangene Erinnerungen. Die Träume zeigen die Zukunft selten realistisch („probt die Zukunft“ = Simulation, nicht Vorhersage) | Wamsley (2022), *PLOS ONE* 17(3), e0264574, doi:10.1371/journal.pone.0264574 |
| „Im Schlaflabor sollten Menschen von einem Video träumen, das sie erst danach sahen. Ergebnis: kein Hinweis auf Vorahnung.“ | 20 Personen mit Vorerfahrung „präkognitiver“ Träume; unabhängige Bewertung der Traumberichte gegen Ziel- und Täuschungsvideos; kein Nachweis von Traum-Präkognition | Watt, Wiseman & Vuillaume (2015), *Journal of Consciousness Studies* 22(5–6), 172–190 |
| „Zuverlässig nachgewiesen ist so etwas bis heute nicht.“ | Einordnung: Es gibt vereinzelte positive Befunde (z. B. eine Heimstudie von Watt & Valášek), diese sind umstritten (Kritik u. a. an fehlenden Daten von Abbrechern); ein zuverlässiger, reproduzierter Nachweis fehlt | Watt et al. (2015); Postscript Watt & Valášek (2015) |

Die Volltexte waren aus der Umgebung nicht abrufbar; die Angaben stammen aus Abstracts, den Repositorien der
Universitäten Edinburgh und Hertfordshire, der Zusammenfassung der Koestler Parapsychology Unit und
Presseberichten. Bewusst nicht im Video: Einzelwerte zum paranormalen Glauben aus Watt et al. (2014), die ich
nicht im Original prüfen konnte.

## Veröffentlichung

**Titel:** Träume, die wahr werden? Das steckt dahinter 🌙

**Caption:** Du träumst von etwas, und Tage später passiert es wirklich. Zufall, Erinnerung oder Vorahnung? Das sagt die Forschung. Ist dir so etwas auch schon einmal passiert? 👇

**Hashtags:** #träume #psychologie #wissenschaft #schlaf #mystery
