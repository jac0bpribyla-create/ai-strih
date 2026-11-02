---
name: ai-strih
description: Střih videí podle stylu, který si uživatel vybere – pošle odkaz na YouTube kanál nebo video, Claude z něj vyčte styl (tempo, střihy, texty, přechody, zvuky) a podle něj sestříhá jeho záběry. Nejdřív hrubý střih ke schválení (nejlepší takes, vystřižené pauzy a zaváhání), teprve potom grafika v HyperFrames, skutečné zvukové efekty ze sfx-kit hlídané nástrojem earshot, hudba a kontrola hlasitosti. Použij, když uživatel chce „sestříhat video“, „zeditovat to jako tenhle kanál / tohle video“, „naučit se můj styl“, „hrubý střih“, „přidat grafiku / titulky / zvukové efekty“, posílá záběry nebo odkaz na YouTube, nebo napíše /ai-strih.
---

# AI střih podle stylu

Stříhám jako střihač bez střihového programu: obraz a zvuk řeší ffmpeg, přepis se slovy a časy Whisper a střih je **střihový list v JSON (EDL)**, ze kterého se video renderuje skriptem. Grafika (texty, počítadla, karty, přechody) se dělá v HyperFrames (HTML → video). Zvuky nikdy neodhaduju: nic neslyším, takže každý zvuk vybírám a kontroluju přes **earshot** a uvádím jeho čísla.

```
S=~/.claude/skills/ai-strih/scripts      # skripty skillu
PY="$S/py"                               # Python s mlx_whisper a numpy (scripts/py ho najde sám)
```

## Pravidla, která platí vždy
- **Hrubý střih → schválení → grafika → zvuk.** Grafiku ani efekty nedělám, dokud uživatel neschválí hrubý střih. Opravit střih po grafice znamená přepočítat všechny časy.
- **Jedno video najednou.** Na zpětnou vazbu čekám, verze číslují `_v1`, `_v2`… a staré nikdy nepřepisuju.
- **Jedna těžká úloha najednou** (Whisper, render, HyperFrames, stabilizace, earshot). Souběh na Macu s 16–24 GB paměti shodí počítač. Příkazy s ffmpeg na pozadí spouštěj s `< /dev/null`, jinak visí.
- **Nic nestahuju bez souhlasu:** předem řeknu kolik souborů, odkud a kolik MB.
- **Pořadí pravidel:** pokyn uživatele v chatu > `PRAVIDLA-STRIHU.md` projektu > `styly/<styl>.md` > `references/kontroly.md`.
- Nikdy netvrdím, že něco „zní dobře“, bez měření z earshotu (`z`, LUFS, posun proti střihu).

## 0. První spuštění
`python3 $S/doctor.py`. Když něco chybí (✗), projdi s uživatelem příslušný krok v `INSTALL.md` a pusť doctor znovu. Bez ✓ u Whisperu, ffmpeg a HyperFrames nezačínej.

## 1. Styl (z YouTube kanálu nebo videa)
Uživatel pošle kanál nebo video, které chce napodobit → postup v `references/styl-z-kanalu.md`:
1. `python3 $S/kanal.py seznam <kanál> [--shorts]` (jen metadata) → vyber 5–8 videí (nejsledovanější + nejnovější). Jedno video stačí taky.
2. Se souhlasem: `python3 $S/kanal.py stahni <projekty>/_styly/<nazev>/videa <ID nebo odkaz> …`
3. `$PY $S/styl_rozbor.py --out <…>/rozbor <…>/videa/*.mp4` → čísla. **Prohlédni `list.jpg` každého úseku** (titulky, písmo, barvy, přechody, B-roll, rámování) – čísla neřeknou všechno.
4. Napiš `styly/<nazev>.md` podle `styly/_sablona.md`, ukaž shrnutí v 5–8 bodech a nech ho potvrdit. Ukázka hotového stylu: `styly/ukazka-mluvici-hlava.md`.

Když uživatel styl nemá a nechce ho tvořit, nabídni `ukazka-mluvici-hlava` a zeptej se na formát (9:16 / 16:9) a délku.

## 2. Projekt
`python3 $S/novy_projekt.py "<název>" <složka se záběry> [--styl <styl>]` → `<projekty>/<název>/` (cesta z `nastaveni.json`). V existujícím projektu nejdřív přečti `PRAVIDLA-STRIHU.md`, `README.md` a poslední EDL v `edl/`.

## 3. Materiál
- Náhledy: `python3 $S/nahledy.py <projekt> <projekt>/nahledy/vse.jpg` → prohlédni.
- Přepis se slovy: `$PY $S/prepis_slova.py <projekt> --vse` (jazyk z `projekt.json`; první běh stáhne model ~1,6 GB).
- Řeč, pauzy a zaváhání: `$PY $S/pauzy.py <projekt> <klipy…>`. Začátky slov, nádech a kašel: `$PY $S/onsety.py <klip> <od> <do>`.
- Třes kamery: `uv run --with "opencv-python-headless==4.10.0.84" --with "numpy<2.3" python $S/stabil.py mereni <klip>` – ber úseky pod 0,15 %.
- Scénář od uživatele (docx: `textutil -convert txt -stdout`), jinak ho poskládej z přepisu.

## 4. Hrubý střih (a stop)
1. Rozhodni a řekni v pár bodech: jaký scénář, které takes (plynulost > gramatika), co vypustit kvůli délce, kolik verzí začátku (hooků). Délka a tempo podle stylu.
2. Střihový list `edl/<číslo>-<název>_v<N>.json` (formát `references/strihovy-list.md`) – u každého take a B-rollu pole `proc`. V hrubém střihu `"popups": []`, `"titulky": {"styl": "zadne"}`.
3. `python3 $S/strih.py <projekt>/edl/<soubor>.json` → `export/<name>.mp4`. Přejmenuj na `<name>_zaklad.mp4`.
4. `$PY $S/kontrola.py export/<…>_zaklad.mp4` (problik, pauzy, jas, hlasitost) a oprav, co nesedí.
5. **Odevzdej hrubý střih a čekej:** cesta k videu + tabulka `Čas | Co říká | Obraz`, co jsem vystřihl a proč, co bych zkusil jinak. Napiš výslovně: „Až střih schválíš, jdu na grafiku a zvuk.“

## 5. Grafika (až po schválení)
Podle stylu: texty s pop, počítadla, karty produktů, pilulka s webem, přechody zoom/švih → zadání v JSON → `python3 $S/hf_kompozice.py zadani.json` → `hyperframes lint` → `snapshot` → `render` → `python3 $S/hlasitost.py output.mp4 export/<name>.mp4` (−14 LUFS). **Časy ber z detekce střihů v `_zaklad.mp4`, ne z EDL.** Postup, bezpečné zóny a složitější prvky: `references/grafika.md` (a skilly `hyperframes`, `hyperframes-animation`). Jednoduché titulky celé řeči umí i `strih.py` (`references/titulky-a-texty.md`).

## 6. Zvuk
Postup v `references/zvuk.md`:
- Efekty jen skutečné nebo z knihovny sfx-kit (CC0): earshot `rank` vybere zvuk z knihovny, `find` najde nejčistší moment, `describe` ověří, že to je ono. Vrchol zvuku na střih nebo na nástup prvku (bod synchronizace z `catalogue.md`).
- Víc efektů naráz (HyperFrames render, screen recording): skill **real-sfx** (`from_hyperframes.py` → `mix.py --voice-safe`).
- Hudba ~12 dB pod hlasem, s ducking. Jen hudba, ke které má uživatel práva.
- Kontrola: earshot `timeline` (efekty proti střihům), `measure` (−14 LUFS ±0,5, špička ≤ −1,5 dBTP).

## 7. Kontrola (vždy, než něco ukážeš)
`$PY $S/kontrola.py video.mp4 --prechody <časy>` + `stabil.py mereni` na hotovém videu + ruční body z `references/kontroly.md` (náhledový list `$PY $S/rozbor_videa.py --out <projekt>/tmp/k video.mp4` → `list.jpg`, oči na třetině, kašel, text přes obličej, B-roll odpovídá slovu, délka zvuku = délka obrazu).

## 8. Odevzdání a zpětná vazba
- Cesta k videu, tabulka `Čas | Co říká | Obraz | Text | Zvuk`, co je nového proti minulé verzi, výsledky kontroly (čísla). Náhled do mobilu pod 30 MB: `ffmpeg -i x.mp4 -c:v libx264 -crf 24 -preset medium -c:a copy -movflags +faststart x_nahled.mp4`.
- **Připomínku zapiš hned:** pravidlo projektu do `PRAVIDLA-STRIHU.md` (datum, verze, citace, co z toho plyne), pravidlo stylu do `styly/<styl>.md`, obecné do `references/kontroly.md`. Pak verze +1. Takhle se skill s každým videem zlepšuje.

## Kdy jiný skill
- Jen „podívej se na video a řekni mi…“: **watch**. Animace v HTML obecně: **hyperframes**, **hyperframes-animation**.
- Soundtrack celého filmu z licencovaných nahrávek (launch video, trailer): **real-sound**.
- Nástroje a přesné příkazy: `references/nastroje.md`.
