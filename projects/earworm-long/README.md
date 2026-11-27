# Ohrwurm-Short, lange Fassung (TikTok / YouTube Shorts, 9:16, Deutsch)

Status: **fertig gerendert** (44,2 s, Limit 50 s; 1080×1920, 30 fps, −14 LUFS, Endkontrolle bestanden).
MP4 nach dem Render: `work/ohrwurm_lang.mp4` (git-ignoriert). Längere Fassung von `projects/earworm-short`
(26 s, unverändert) mit mehr Erklärung: Fachbegriff, Häufigkeit, Auslöser, Zustand mit wenig Aufmerksamkeit,
Wirkmechanismus des Kaugummi-Tricks. 13 Szenen sind aus der Kurzfassung übernommen, 9 neu kuratiert.

## Ablauf

Wie in `projects/earworm-short` (alle Pfade mit `earworm-long`). Für die übernommenen Szenen kopiert die
Projekterstellung Kandidat und Rohclip aus der Kurzfassung; `curate.py search` nur für die neuen Szenen.

## Neu gegenüber der Kurzfassung

- **Musik ohne Maskierung:** Bei rund 10 dB Abstand verdeckten die gezupften Töne Wörter wie „Ort“.
  Getestet: Sidechain-Ducking machte alles verständlich, ließ die Musik aber pumpen (bis 12 dB/100 ms);
  sanftes Ducking reichte nicht. Lösung: Musik konstant leiser (bgm-volume 0.13, rund 17 dB unter der Stimme)
  und eine leichte Absenkung um 2 kHz. Keine Pegelbewegung in der Musik.
- **„ein Wort, ein Ort“** wurde durch „ein Wort, eine Situation“ ersetzt: Der Reim wurde selbst ohne Musik
  verwechselt, und „Situation“ entspricht der Studie genauer.
- **Abnahme der Vertonung:** Eine Aufnahme wird nur genommen, wenn ihr reines Voiceover Wort für Wort zum Skript
  passt (Whisper). Eine Aufnahme mit „kam“ statt „kamen“ und verschlucktem „dir“ wurde verworfen.
- **`align.py`:** transkribiert mit und ohne Skript als Kontext und nimmt die bessere Variante. Bei diesem
  längeren Skript passten mit Kontext nur 35–37 von 124 Wörtern, ohne Kontext 120–122.
- Abschluss-Transkript des fertigen MP4: stimmt Wort für Wort mit dem Skript überein. Alle 22 Schnitte
  bildgenau. Längenlimit hier 50 s.

## Faktencheck

| Aussage im Video | Einordnung | Quelle |
|---|---|---|
| „Forscher nennen das unwillkürliche Musikvorstellung.“ | Fachbegriff *involuntary musical imagery* (INMI) | Williamson et al. (2012); Jakubowski et al. (2017) |
| „In Umfragen erleben rund neun von zehn Menschen das mindestens einmal pro Woche.“ | 89,2 % wöchentlich in einer großen finnischen Online-Umfrage; Williamson et al. (2014) fassen es als „über 90 %“ zusammen | Liikkanen (2012), *Psychology of Music* 40(2); Williamson et al. (2014), *PLOS ONE* 9(1), e84259 |
| „Meist ist es ein Song, den du kürzlich oder oft gehört hast.“ | häufigster Auslöser: kürzliche/wiederholte Exposition | Williamson et al. (2012); Jakubowski et al. (2017) |
| „Manchmal reicht auch ein Auslöser: ein Wort, eine Situation, eine Erinnerung.“ | Auslöser-Kategorie „Assoziationen“ (Wörter, Situationen) und Erinnerungen | Williamson et al. (2012) |
| „Und es passiert oft, wenn dein Kopf wenig zu tun hat, zum Beispiel, wenn dir langweilig ist.“ | Zustände geringer Aufmerksamkeit, z. B. Langeweile | Williamson et al. (2012) |
| „Die Idee: Kauen stört das innere Mitsingen.“ | als **Erklärung der Autoren** formuliert („Die Idee“): Kauen stört die subvokale Artikulation | Beaman, Powell & Rapley (2015) |
| „Dann läuft ein kurzes Stück in Dauerschleife.“ | Ohrwürmer sind typischerweise kurze Ausschnitte (oft Refrain), die sich wiederholen | Williamson et al. (2012); Beaman & Williams (2010) |
| „Besonders oft trifft es schnelle Songs, deren Melodie typisch verläuft, aber ein paar ungewöhnliche Sprünge macht.“ | Vergleich von 100 Ohrwurm-Songs mit 100 gleich beliebten Kontrollsongs: schnelleres Tempo, häufigerer (typischer) globaler Melodieverlauf, ungewöhnlichere Intervalle/Steigungen an Wendepunkten. „Besonders oft“ = häufiger als Ohrwurm genannt | Jakubowski, Finkel, Stewart & Müllensiefen (2017) |
| „Der Trick dagegen: Kaugummi kauen. Im Experiment kamen dadurch seltener Ohrwürmer.“ | Kaugummikauen verringerte in Experimenten die Zahl unwillkürlicher Musikgedanken (auch die bewusst abgerufenen); laut Experiment 3 nicht nur durch allgemeine Ablenkung erklärbar. Erklärung der Autoren: Kauen stört das innere Mitsprechen/Mitsingen | Beaman, Powell & Rapley (2015) |

Bewusst weggelassen: „Ohrwürmer sind unvollendete Melodien / Zeigarnik-Effekt“ (populär, aber schwach belegt),
konkrete Prozentzahlen zur Kaugummi-Wirkung (nur aus Presseberichten, nicht im Original prüfbar).

## Veröffentlichung

**TikTok-Caption:** Warum läuft ein Song stundenlang in deinem Kopf? 🎧 Was Ohrwürmer auslöst, welche Songs besonders oft hängen bleiben und ein überraschender Trick dagegen. Welchen Song bekommst du gerade nicht aus deinem Kopf? 👇 #ohrwurm #musik #psychologie #gehirn #wissenschaft

**YouTube-Shorts-Titel (79 Zeichen):** Warum dein Gehirn Songs in Dauerschleife spielt 🎧 #ohrwurm #psychologie #shorts
