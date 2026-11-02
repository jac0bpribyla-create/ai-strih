# Střihový list (EDL) pro `strih.py`

Soubor `<projekt>/edl/<číslo>-<název>_v<verze>.json`. Render: `python3 $S/strih.py <projekt>/edl/<soubor>.json [--rychle]`.
Výstup `<projekt>/export/<name>[_<hook>].mp4` (H.264, AAC 192k, −14 LUFS) + `.srt` (stejné titulky, třeba pro CapCut nebo YouTube).

Všechny časy jsou v sekundách. `in`/`out`/`src` = čas v klipu, `t_from`/`t_to` = čas ve výsledném videu.

## Celý příklad
```json
{
 "name": "01-jak-jsem-zacal_v1",
 "scenar": "01 — Jak jsem začal, mluvím do kamery",
 "format": "9:16",
 "fps": 25,
 "grade": "eq=contrast=1.04:saturation=1.06",
 "hooks": {
  "A-otazka": {
   "segments": [{"clip": "C0012", "in": 2.3, "out": 6.3, "speech_from": 2.42, "speech_to": 6.18,
                 "text": "Víš, kolik mě stál první rok podnikání?"}],
   "popups": [{"text": "KOLIK STÁL\nPRVNÍ ROK?", "t_from": 0.1, "t_to": 3.95, "y": 800, "size": 72}]
  },
  "B-cislo": [{"clip": "C0009", "in": 0.4, "out": 3.9, "text": "První rok mě stál 200 tisíc a nic jsem nevydělal."}]
 },
 "segments": [
  {"clip": "C0014", "in": 8.97, "out": 12.99, "speech_from": 9.09, "speech_to": 12.87,
   "text": "Všechno jsem dělal sám, od nápadu až po balení.", "proc": "plynulejší take než C0013"},
  {"clip": "C0015", "in": 2.68, "out": 7.12, "zoom": 1.25, "cx": 0.57, "cy": 0.36,
   "text": "Dneska mám tým a posíláme stovky balíků týdně.", "proc": "přiblížení schová jump cut"},
  {"karta": {"logo": "assets/logo.png", "pozadi": "#141414", "text": "MUJWEB.CZ", "delka": 1.5}}
 ],
 "overlays": [
  {"clip": "C0031", "src": 1.0, "speed": 0.5, "t_from": 2.2, "t_to": 3.9, "proc": "…od nápadu až po balení – ruce balí krabici"},
  {"obrazek": "assets/web.png", "t_from": 7.0, "t_to": 8.5, "zoom_od": 1.0, "zoom_do": 1.08, "proc": "screenshot webu"}
 ],
 "popups": [
  {"text": "200 000 KČ", "t_from": 0.3, "t_to": 2.2, "y": 1000, "size": 130},
  {"text": "-20 %", "t_from": 0, "t_to": 9.5, "x": 880, "y": 300, "size": 64, "pop": false, "sfx": false, "barva": "#E63B2E"}
 ],
 "titulky": {"styl": "karaoke", "y": 1200, "velikost": 62},
 "hudba": {"soubor": "assets/hudba.mp3", "od": 12.0, "pod_reci_db": 12, "ducking": true}
}
```
V **hrubém střihu** nech `"popups": []` a `"titulky": {"styl": "zadne"}` – texty a grafika přijdou až po schválení.

## Pole
**Hlavička:** `name` (název souboru), `scenar` (popis pro lidi), `format` (`9:16` | `4:5` | `1:1` | `16:9`), `fps` (jinak z projekt.json, jinak 30), `grade` (ffmpeg filtr barev pro všechny záběry, LUT se řeší v projekt.json).

**segments** (A-roll, jde za sebou, nese zvuk):
- `clip` (název z projektu nebo cesta), `in`, `out`
- `speech_from`, `speech_to`: kde v klipu se mluví (z `pauzy.py`). Používá se pro titulky a jako kontrola nástřihu.
- `text`: opravený přepis, z něj jsou titulky
- `zoom` (1.0–2.0), `cx`, `cy` (střed výřezu 0–1): výřez se počítá z cílového poměru stran, takže 16:9 záběr jde i do 9:16
- `speed` (0.5 = zpomalení, 1.1 = zrychlení i hlasu), `mute` (bez zvuku)
- `proc`: proč tenhle take (pro lidi, render ho ignoruje)
- `{"karta": {logo, pozadi, text, delka, logo_sirka 0.6, y_logo 0.42, y_text 0.62, barva_textu}}`: koncová karta. Hudba pod ní hraje dál.

**overlays** (obraz přes A-roll, zvuk A-rollu běží dál):
- klip: `clip`, `src` (odkud v klipu), `t_from`, `t_to`, `speed`, `zoom`, `cx`, `cy`, `proc`
- `uhel` (u segmentu i B-rollu, stupně, + = po směru hodinových ručiček): srovná křivý záběr; přiblížení se samo zvětší, aby nebyly vidět černé rohy. Křivý produkt: nejdřív zkusit jiný okamžik nebo záběr, teprve pak otáčet.
- `lut` (u segmentu i B-rollu): přebije `lut.kdy` z projekt.json – `false` bez LUTu, `true` LUT projektu, `"tools/x.cube"` jiný. Záběr natočený v barvách (Rec.709) místo S-Logu: `false` – S-Log LUT na něj nepatří, ani v menší síle.
- `grade` (u segmentu i B-rollu): ffmpeg filtr jen pro ten záběr, po společném `grade`. Přesvětlený záběr na bílém pozadí: `curves=master='0/0 0.3/0.24 0.6/0.5 0.85/0.78 1/0.95',eq=saturation=1.1` (průměrný jas Y nad ~165 = přesvětlené; změřit `signalstats`).
- obrázek: `obrazek` (screenshot webu, recenze, foto), `t_from`, `t_to`, `zoom_od`, `zoom_do` (pomalé přiblížení), `vypln` (`cover` | `contain`), `pozadi`

**popups** (texty): `text` (`\n` = nový řádek), `t_from`, `t_to`, `y`, `x` (výchozí střed), `size`, `style` (`Box` velký box | `Sub` malý podtitul | `Tit`), `pop` (animace naskočení, výchozí true), `sfx` (pop zvuk), `barva` (box), `barva_textu`, `font` (jiné písmo než projekt), `tucne` (true/false), `obrys` (tloušťka, 0 = bez), `stin` (`{"posun": 3, "alfa": 0.5, "rozmazani": 6}` – měkký stín jako rozmazaná vrstva pod textem), `proklad` (mezery mezi písmeny). Minimalistický text: `"style": "Tit", "obrys": 0, "tucne": false, "stin": {…}`.

**titulky:** `styl` (`karaoke` | `slova` | `vety` | `zadne`), `y`, `velikost`, `verzalky`, `max_znaku`, `zvyraznit` (slova v barvě, čísla se zvýrazní sama u `slova`/`vety`), `barva`.

**hudba:** `soubor`, `od` (odkud v hudbě), `pod_reci_db` (o kolik pod hlasem, výchozí 12), `ducking` (ztišit pod řečí, výchozí true). Bez řeči jde hudba rovnou na −14 LUFS.

**hooks:** `{"<klíč>": [segmenty]}` nebo `{"<klíč>": {"segments": [...], "popups": [...], "overlays": [...]}}`. Každý klíč = samostatné video `<name>_<klíč>.mp4`.
**Pozor:** když EDL má `hooks`, časy `overlays` a `popups` těla se počítají **od začátku těla**. Render je posune o délku hooku. Popupy a overlaye uvnitř hooku se počítají od začátku videa.

## Jak na časy
- Nástřih 0,12 s před první slabikou, výstřih 0,15 s po poslední (podle `pauzy.py`, ne podle Whisperu, ten dává začátky o 0,3–0,5 s dřív).
- `t_from` B-rollu = začátek slova, ke kterému patří, na výsledné ose. Výsledná osa = součet délek předchozích segmentů (`(out−in)/speed`).
- Po renderu vždy zkontroluj `kontrola.py` + `rozbor_videa.py` → `list.jpg` (viz SKILL.md, kontrola).
