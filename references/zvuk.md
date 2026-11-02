# Zvuk: efekty, hudba, hlasitost

Neslyším. Proto každý zvuk vybírám, umisťuju a kontroluju měřením: **earshot** (MCP server, nástroje `mcp__earshot__*`, nebo CLI `earshot …`) dává čísla, ke kterým se dá vrátit. V odevzdání vždy uveď, co bylo změřeno, a co by si měl uživatel poslechnout sám.

Knihovna: **sfx-kit** (320 zvuků, CC0) – cesta `zvuky` v `nastaveni.json`. Ke každému zvuku je v `catalogue.md` popis, kdy ho použít a kdy ne, délka a **bod synchronizace** (např. `whoosh-fast-hard` 0,25 s, sync 0,092 s = vrchol 0,092 s od začátku souboru). Uživatel může přidat vlastní knihovnu (Freesound s filtrem CC0, Mixkit, Sonniss GDC) – licenci si hlídá sám.

## Kdy jaký efekt
| Moment v obraze | Zvuk (složka sfx-kit) | Hlasitost proti hlasu |
|---|---|---|
| Popisek nebo číslo naskočí | `pops/pop-medium-in`, `pop-small-in` | tichý, ~−16 dB pod hlasem |
| Přechod zoom | `bounce-spin-zoom/move-zoom-in` (sync 0,489 s) | ~−10 dB |
| Přechod švih (whip) | `whooshes/whoosh-fast-hard` (sync 0,092 s) | ~−10 dB |
| Karta / panel vyjede | `whooshes/whoosh-medium-soft`, `swipes/…` | ~−14 dB |
| Velké odhalení po napětí | `risers-and-fallers/…` do `booms-and-bass/boom-drop-soft` | střídmě, 1× za video |
| Psaní, kliknutí v UI | `keyboard/…`, `interface/…` | tiché, pod hlasem |
| Počítadlo naskakuje | `data/…`, `time/…` (tick) | tiché |

Méně je víc: efekt jen tam, kde se v obraze něco děje. Nic v prvních 0,15 s videa. Žádný efekt přes první slabiku po střihu.

## Postup pro jednotlivé efekty
1. **Vybrat:** `mcp__earshot__rank` s `paths` = složka sfx-kit (nebo podsložka, např. `sounds/whooshes`) a `query` = popis zvuku samotného („a fast airy whoosh with a bright edge“, ne „zvuk na přechod“). Ber z prvních 3; `z` ≥ 3 silná shoda, 2,5–3 použitelná, pod 2 nebrat.
2. **Oříznout** (jen u delších nahrávek a balíků): `mcp__earshot__find` → `start`/`end` nejčistšího momentu.
3. **Ověřit:** `mcp__earshot__describe` na vybraný soubor/úsek – sedí to s tím, co si myslíš, že to je?
4. **Umístit:** začátek = čas události v obraze − bod synchronizace. Whoosh má vrchol ~0,1 s **před** střihem a nesmí dozvukem překrýt první slovo po něm (zkrať ho fade-outem).
5. **Smíchat:** ve `strih.py` přes popupy (pop se přidá sám), v HyperFrames přes `<audio data-start data-volume>` (dělá `hf_kompozice.py`), jinak ffmpeg `adelay` + `amix normalize=0`. **Obraz a zvukový mix renderuj zvlášť a spoj až na konci** – ve společném grafu ffmpeg umí tiše zmizet kus hlavní stopy.

## Hodně efektů naráz: real-sfx
Pro render z HyperFrames nebo screen recording (desítky momentů) použij skill **real-sfx** – najde momenty, vybere zvuky z knihovny a umístí je na snímek:
```
R=~/.claude/skills/real-sfx/scripts
$PY $R/setup.py check
$PY $R/from_hyperframes.py <hyperframes složka nebo index.html> --video <render.mp4> --out <projekt>/zvuk/cues.json
$PY $R/mix.py <projekt>/zvuk/cues.json --out <projekt>/zvuk/video_sfx.mp4 --voice-safe --plan   # nejdřív plán
$PY $R/mix.py <projekt>/zvuk/cues.json --out <projekt>/zvuk/video_sfx.mp4 --voice-safe
$PY $R/critique.py <projekt>/zvuk/video_sfx_resolved_cues.json <projekt>/zvuk/video_sfx_sfx_track.wav
```
`--voice-safe` ztlumí efekty pod řečí. Výsledek: nové MP4 + samostatná stopa efektů (WAV) + hodnocení. Podrobnosti v SKILL.md skillu real-sfx. Pozor: syntetické zvuky, které už jsou v renderu (z `hf_kompozice.py`), real-sfx nahradí – nevrstvi oboje.

## Hudba
- Jen hudba, ke které má uživatel práva (vlastní, licencovaná knihovna, YouTube Audio Library). Populární písničky nestahovat; u YouTube upozorni na Content ID.
- V EDL `"hudba": {"soubor", "od", "pod_reci_db": 12, "ducking": true}` – asi 12 dB pod hlasem, pod řečí se ztišuje.
- Bez řeči nese rytmus hudba: střihy na doby. Tempo a doby: `mcp__earshot__measure` s `music=true`.
- Drop hudby na hlavní moment videa (odhalení, pointa), ne náhodně.

## Kontrola zvuku (před odevzdáním)
- `mcp__earshot__measure` na hotové video: **−14 LUFS ±0,5, true peak ≤ −1,5 dBTP**, žádné oříznuté vzorky.
- `mcp__earshot__timeline` s `cues` = časy střihů a nástupů prvků: posun efektů proti obrazu (cíl do ±40 ms) a co kde zní.
- Delší video nebo „launch“ styl: `mcp__earshot__critique` – skóre proti profesionálním filmům, s konkrétními časy k opravě.
- Délka zvuku = délka obrazu (`ffprobe` obou streamů, rozdíl < 0,05 s).
- Hotový zvuk znovu přepiš Whisperem (`rozbor_videa.py`) – useknutá slova, opakování a slyšitelné pokyny z natáčení se tak najdou bez poslechu.
- HyperFrames dělá z mono hlasu dual-mono stereo (měří se o ~3 LU hlasitěji) → po renderu vždy `$PY $S/hlasitost.py`.
- `mcp__earshot__llm_critique` posílá zvuk do Gemini – **jen s výslovným souhlasem uživatele**.

## Výkon
První volání earshotu načítá modely (~20–60 s), další jsou rychlé. Nespouštěj earshot souběžně s renderem nebo Whisperem. Pro víc než pár souborů použij MCP (modely zůstanou načtené), ne opakované CLI.
