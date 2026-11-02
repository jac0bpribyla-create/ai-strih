# Nástroje a příkazy

`S=~/.claude/skills/ai-strih/scripts` · `PY="$S/py"` (Python s Whisperem a numpy – mlx-whisper na Macu s Apple Silicon, jinde faster-whisper; všechny skripty spouštěj přes něj) · cesty a jazyk v `nastaveni.json` (`$PY $S/nastaveni.py` je vypíše).
V zsh se proměnná se seznamem nerozdělí na slova – seznamy klipů vypiš ručně nebo je předej z Pythonu.

## Projekt a materiál
- `$PY $S/novy_projekt.py "<název>" <složka> [--styl <styl>]` → `<projekty>/<název>/` (projekt.json: zdroje, jazyk, LUT, otočení, fps, písmo, barvy; PRAVIDLA-STRIHU.md; README.md).
- `$PY $S/nahledy.py <projekt> out.jpg --tile 200 --cols 10 C0001@1.5 C0002 …` – snímky klipů s LUTem a otočením (`@čas`, jinak střed).
- `$PY $S/prepis_slova.py <projekt> --vse` – Whisper se slovy (`prepisy-slova/<klip>.json`: segments → words `w/s/e/p`).
- `$PY $S/pauzy.py <projekt> C0001 C0002` – úseky řeči podle hlasitosti, pauzy > 0,3 s a **zaváhání** (podle hlasitosti každé promluvy). Zaváhání nad 0,25 s vystřihnout vždy.
- `$PY $S/onsety.py <klip> <od> <do> --prepis prepis.json` – hranice slov z hlasitosti (sem nasazovat B-roll a střihy) a šumové úseky (nádech, kašel).
- Kamera: Sony S-Log3 potřebuje LUT (`projekt.json` → `"lut": {"soubor": "assets/x.cube", "kdy": "sony-slog3"}`, pozná se ze Sony XML vedle klipu). Rec.709 / iPhone jen jemný kontrast. Chybějící příznak otočení → `"otocit": {"C0007": "cclock"}`.

## Pravidla času
- **Whisper dává začátky slov o 0,1–0,5 s vedle** (většinou dřív). Nástřih 0,12 s před první slabikou, výstřih 0,15 s po poslední – podle hlasitosti (`pauzy.py`), ne podle Whisperu.
- **Whisper umí označit kašel jako slovo.** Na začátku každé věty zkontroluj `onsety.py`: šumový náraz s pomalým doznívaním = kašel → vystřihnout; tichý šum −45 až −55 dB před první hláskou = nádech → nástřih až za něj.
- Mezi větami ~0,25 s, uvnitř věty žádné zaváhání. Skok ve stejném záběru (jump cut) schovej přiblížením (1,2–1,4×), B-rollem nebo přechodem.
- `strih.py` zaokrouhluje úseky na celé snímky → skutečné časy střihů zjisti detekcí scén v hotovém základu (`kontrola.py` nebo `ffmpeg -vf "select='gt(scene,0.18)',showinfo"`) a podle nich časuj grafiku a zvuky.

## Výřez (zoom, cx, cy)
- **Oči na horní třetině** (y ≈ 1/3 výšky): `cy = výška_očí + 1/(6·zoom)`, omezeno na `[0,5/zoom; 1 − 0,5/zoom]`. Výška očí: `uv run --with "opencv-python-headless==4.10.0.84" --with "numpy<2.3" python $S/oci.py C0001@0.6-5.2@1.6` (na plochém S-Logu nebo s brýlemi změř ručně z náhledu).
- Bez přiblížení oči posunout nejdou: když jsou moc vysoko, přibliž s výřezem u horního okraje (`cy = 0,5/zoom`) nebo vezmi jiný take.
- Přiblížení nad 2× ztrácí kvalitu (4K → 1080). Celek (postava od hlavy k patě) na 9:16 přibliž 1,3–1,6×.

## Třes a stabilizace
- `uv run --with "opencv-python-headless==4.10.0.84" --with "numpy<2.3" python $S/stabil.py mereni <klip>` – třes po sekundách: < 0,15 % klidné, 0,15–0,35 % stabilizovat, > 0,35 % nebrat.
- `… stabil.py stab <klip> <od> <do> <výstup.mov> [--rezim plynule|zamek]` – ProRes 10 bit, nikdy do 8bit H.264.

## B-roll
- 50p a 60p záběry zpomal 0,5× / ~0,6× (plynulé), **25p a 30p nezpomaluj** (trhá se).
- Přesvětlené bílé pozadí: `"grade": "curves=master='0/0 0.3/0.24 0.6/0.5 0.85/0.78 1/0.95',eq=saturation=1.1"`. Průměrný jas (kontrola.py): nad ~165 přesvětlené, pod ~60 tmavé.
- B-roll nad 2 s rozděl; v rychlém střídání po 0,5–1,5 s.

## Render a zvuk
- `$PY $S/strih.py edl/x.json [--rychle]` → `export/<name>[_<hook>].mp4` + `.srt`. Hooky = `"hooks"` v EDL (každý = samostatné video se stejným tělem).
- HyperFrames: `hyperframes lint <výstup>/public` → `PRODUCER_BROWSER_GPU_MODE=hardware hyperframes snapshot <výstup>/public --at 1.0,2.5` → `hyperframes render <výstup>/public -o <výstup>/output.mp4 --fps 25`.
- Hlasitost po HyperFrames: `$PY $S/hlasitost.py output.mp4 export/<name>.mp4` (dvouprůchodový `loudnorm` na −14 LUFS / −1,5 dBTP, obraz se nepřekódovává). V zsh piš `${promenna}`, ne `$promenna:…`.
- Náhled do mobilu (pod 30 MB): `ffmpeg -i x.mp4 -c:v libx264 -crf 24 -preset medium -c:a copy -movflags +faststart x_nahled.mp4`.

## Obrázky z webu uživatele
- Stahovat jen se souhlasem (kolik souborů, odkud, velikost). Ořez na kartu 920×660 (cover) v Pythonu s PIL; skripty spouštěj mimo složku se staženými soubory.
- Názvy produktů přesně podle webu, zkrácené. Fotky generované AI nepoužívat, pokud o ně uživatel výslovně nestojí.

## Rozbor videa
- `$PY $S/rozbor_videa.py --out <složka> video.mp4 [--no-whisper] [--lang en]` → `rozbor.json` (střihy, délky záběrů, řeč, slova/s, hlasitost, hudba) + `list.jpg` (prvních 3 s hustě + střed každého záběru).
- `$PY $S/styl_rozbor.py --out <složka> video1.mp4 …` → `styl.md` s mediány (dlouhá videa po úsecích).
