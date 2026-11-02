# Grafika v HyperFrames (až po schváleném hrubém střihu)

Kompozice = `public/index.html`: `#video-wrap` se schváleným základem (`input-video.mp4`, `data-has-audio="true"`), nad ním vrstvy „card-host“ s `data-start`/`data-duration`, `<audio>` zvuky a jedna GSAP timeline (`window.__timelines["<id>"]`). Běžné prvky generuje `scripts/hf_kompozice.py` ze zadání v JSON (popis polí v hlavičce skriptu). Na všechno ostatní použij skilly **hyperframes**, **hyperframes-animation** a **hyperframes-registry** (~400 hotových bloků: grafy, glitch, film grain, mapy, terminál…).

## Hotové prvky v hf_kompozice.py
| Prvek | Pole v zadání | Kdy |
|---|---|---|
| Popisek v boxu s „pop“ (30 % → 112 % → 100 %, 0,28 s, `back.out(2.2)`) + tichý pop | `texty` | čísla a klíčová slova, naskočí přesně na slovo |
| Počítadlo (0 → 150 KG, 0 → 10 LET) | `texty` + `"pocitadlo"` | číslo v řeči; jednotku nech vyjet až po doběhnutí čísla |
| Karty produktů (mřížka 2×2, vyletí s natočením po 0,13 s, video ztmavne) | `karty` | když mluví o víc věcech najednou |
| Pilulka s webem (bílá, zaoblená) | `pilulka` | na konci, na výzvě k akci |
| Přechod zoom (1,25× + rozmazání 10 px) / švih (180 px, 1,35×, 16 px) se zvukem | `prechody` | jen na předělech příběhu; hýbe se jen video |

Písmo: `styl.font` = písmo z Macu (výchozí Avenir Next), nebo vlastní soubory v `styl.fonty` (`{"700": "fonts/X-Bold.woff2"}`). Komerční písma (Futura, Gilroy…) do sdílených projektů nedávej bez licence.

Zvuky prvků jsou ze sfx-kit (CC0) a nasazují se podle bodu synchronizace (vrchol whooshe přesně na střih). Když chceš jiné zvuky nebo jich je hodně, nech `prechody` bez zvuku a efekty udělej podle `references/zvuk.md`.

## Postup
1. Schválený `_zaklad.mp4` → **časy střihů z detekce scén** (`kontrola.py` vypíše „střihy“). Podle nich přechody, texty ~0,15 s po přechodu.
2. Zadání `hyperframes/<id>_v<N>/zadani.json` → `python3 $S/hf_kompozice.py zadani.json`.
3. `hyperframes lint <výstup>/public` → `PRODUCER_BROWSER_GPU_MODE=hardware hyperframes snapshot <výstup>/public --at <čas každého textu po 0,5 s>` → **prohlédni snímky: text nesmí být přes obličej ani přes věc, o které se mluví**.
4. `hyperframes render <výstup>/public -o <výstup>/output.mp4 --fps 25` (jeden render najednou) → `python3 $S/hlasitost.py <výstup>/output.mp4 <projekt>/export/<name>.mp4` (−14 LUFS) → `kontrola.py`.
5. Víc verzí začátku (hooky) generuj z jednoho zadání s `"posun"` – nikdy ručně kopírovat a posouvat (ztratí se zvuky a časy).

## Bezpečné zóny
- 9:16 (Reels, TikTok, Shorts): text v **y 220–1250, x 65–1015**. Nahoře je profil, dole popisek a tlačítka.
- 16:9 (YouTube): okraj aspoň 5 % dokola, dolní třetina pro lower thirds, pravý dolní roh nechat volný (end screen, tlačítka).
- Horní hrana textu aspoň ~100 px pod nejnižší polohou brady po celou dobu zobrazení.

## Složitější prvky (skilly hyperframes)
- Kóta nebo šipka připnutá na předmět, který se hýbe: sledování v OpenCV → klíčové snímky (`hyperframes-keyframes`).
- 3D produkt (three.js): import přes jsdelivr importmap, `data-duration` na kořeni, `PRODUCER_BROWSER_GPU_MODE=hardware`.
- Mluvčí v kartě nad pozadím, grafika na každé slovo (styl „explainer“): vlastní kompozice podle `hyperframes-core`; hustota ~1 prvek za 2–5 s, nic prázdného přes 2,5 s.
