# Styl: ukázka – mluvící hlava (Reels / TikTok / Shorts, 9:16)

Zdroj: ukázkový styl dodaný se skillem, ověřený na několika krátkých videích, kde majitel firmy mluví do kamery. Vlastní styl si vytvoř z kanálu nebo videa (`references/styl-z-kanalu.md`).
Jednou větou: člověk mluví do kamery, každé tvrzení má hned obraz (B-roll, detail, produkt), minimalistické černé popisky s pop a tichým zvukem, přechody se švihy jen na předělech, konec na výzvě řečí s pilulkou webu.

## Formát a délka
- 1080×1920, 25 fps, −14 LUFS. Délka 25–35 s.
- První slovo hned (≤ 0,1 s), žádné intro ani logo. Začátek (hook) jako samostatná verze videa – 2 verze, stejné tělo.
- Konec: výzva řečí („Mrkni na mujweb.cz…“) + bílá pilulka s webem, bez závěrečné karty.

## Střih a tempo
- Ø záběr 1,5–1,8 s, řeč pokrývá 90–99 % délky, pauzy mezi větami ~0,25 s, uvnitř vět žádná zaváhání (slyšet je i 0,4 s).
- Plynulost take > gramatika; nikdy přeřeknutí, pokyny z natáčení ani nejednotné tykání/vykání.
- Skok ve stejném záběru → přiblížení 1,2–1,4× nebo B-roll.

## Rámování
- **Oči na horní třetině** (y ≈ 640 px), celek přiblížit 1,3–1,6×, výzvu na konci přiblížit.

## B-roll (~35–40 % času)
- Práce, výroba, detaily, produkty, balení – to, o čem se zrovna mluví.
- Nasazený přesně na slovo, ke kterému patří; po ukazovacím „tohle“ hned B-roll té věci; rychlé střídání 3–4 záběrů po ~1,4 s, když má být video dynamičtější.
- 50p zpomalit 0,5×, 25p ne. Přesvětlené bílé pozadí stáhnout křivkou. Bez techniky z natáčení v pozadí, bez useknuté hlavy.

## Texty a grafika (HyperFrames, `hf_kompozice.py`)
- Černý box `#141414`, bílé tučné verzálky (Avenir Next Bold nebo podobné bezpatkové), prostrkání 0,07 em, zaoblení 14 px, pop 30 → 112 → 100 % + tichý pop.
- Jen čísla a klíčová slova (150 KG, 15 MM, 7 SUROVIN, 2 ROKY), čísla nabíhají od 0. Text přes hruď, ~100+ px pod bradou.
- Karty produktů: bílé, fotka z webu + název, vyjedou zespodu, video ztmavne; víc produktů do mřížky 2×2.
- Titulky celé řeči volitelně (`strih.py`, styl `karaoke`) – zeptej se.

## Přechody a zvuk
- Zoom a švih střídavě, 4–6 na video, jen na předělech příběhu (začátek → tělo, nové místo, výzva), ne v rychlém střídání B-rollů ani pod kartami. Vrchol whooshe na střihu (sfx-kit, bod synchronizace).
- Pop při každém popisku, ~−16 dB pod hlasem. Hudba volitelná, ~12 dB pod hlasem s ducking. Hlas: high-pass 80 Hz, kompresor, −14 LUFS.

## Barvy
- S-Log → LUT, Rec.709 / telefon jen kontrast 1,04 a saturace 1,06.

## Co styl NEdělá
- Závěrečnou kartu s logem, efekty pro efekt, text přes obličej nebo produkt, B-roll s nejasným obsahem, hudbu přes řeč nahlas.

## Otázky pro uživatele
- Barva značky a web do výzvy? Titulky celé řeči ano/ne? Hudba ano/ne a odkud?

## Zpětná vazba
<!-- datum — verze — citace — co z toho plyne -->
