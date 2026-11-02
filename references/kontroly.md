# Kontroly před odevzdáním (platí pro každý styl)

Spusť `$PY $S/kontrola.py video.mp4 --prechody <časy přechodů>` a projdi seznam. Každý bod vznikl z připomínky ke skutečnému střihu – proto ho nepřeskakuj. Nové poučení, které platí pro všechna videa, sem připiš.

## Automaticky (kontrola.py)
- [ ] Hlasitost −14 LUFS (±0,5), špička pod −1,5 dBTP.
- [ ] **Žádný problik:** dva střihy ≤ 1 snímek od sebe mimo přechody = 1 snímek jiného záběru (působí „sekavě“). Kontroluj po každém renderu.
- [ ] Jas záběrů: nic nad ~165 (přesvětlené bílé pozadí) ani pod ~60 bez důvodu.
- [ ] Pauzy nad 0,25 s jen na předělech scén, ne uvnitř věty (když člověk přemýšlí, pauza se vystřihne).

## Třes kamery
- [ ] **Žádný klip se nesmí klepat.** Před výběrem záběrů změř kandidáty `stabil.py mereni` a ber úseky **< 0,15 %**. Úsek 0,15–0,35 % jen když je obsahově nenahraditelný, a pak vždy `stabil.py stab` (ProRes 10 bit). Nad 0,35 % nebrat.
- [ ] Po renderu změř třes i na hotovém videu (`stabil.py mereni export/…mp4`).
- [ ] Rychlý střih neschová třes, roztřesené krátké záběry působí ještě hůř. V montáži drž záběr aspoň ~2 s, celky 3–5 s.
- [ ] **LUT podle každého klipu zvlášť:** Sony občas nezapíše profil do XML. Šedivý, nízkokontrastní záběr v náhledu = vynutit `"lut": true`.

## Ručně (náhledový list `rozbor_videa.py --out tmp/k video.mp4` → `list.jpg`, snímky HyperFrames po 0,5 s)
- [ ] **Oči na horní třetině** u každého záběru na obličej.
- [ ] **Kašel a nádech** na začátku vět (`onsety.py`; Whisper kašel označí jako slovo).
- [ ] **Zaváhání uvnitř take** vystřižená (`pauzy.py`, řádek „zaváhání“), přeřeknutí nikde, pokyny z natáčení („super“, „ještě jednou“) neslyšet.
- [ ] **Technika v pozadí** (kamera na stativu, gimbal, světla) – projdi celý použitý úsek, ne jeden snímek.
- [ ] **Useknutá hlava** v B-rollu (ruce na výrobku → přiblížit na ruce), ruka vjíždějící do záběru, neostrý detail.
- [ ] **B-roll odpovídá slovu** na první pohled a začíná na tom slově.
- [ ] **Text nikdy přes obličej ani přes věc, o které se mluví** – horní hrana aspoň ~100 px pod nejnižší polohou brady po celou dobu zobrazení. Bezpečná zóna 9:16: y 220–1250, x 65–1015.
- [ ] Jedno video vysvětluje stejnou věc jen jednou (duplicitní větu vypustit kvůli délce).
- [ ] Tykání/vykání jednotně (take, který vyká, když zbytek tyká, vyřadit).
- [ ] Skok ve stejném záběru (jump cut) schovaný přiblížením, B-rollem nebo přechodem.

## Zvuk proti obrazu
- [ ] **Délka zvuku = délka obrazu** (`ffprobe` obou streamů, rozdíl < 0,05 s). Obraz a zvukový mix renderuj **zvlášť** a spoj až na konci – ve společném grafu ffmpeg (overlay se `setpts` + `adelay` v jednom příkazu) umí tiše zmizet kus hlavní stopy.
- [ ] U dlouhých videí ověř posun zvuku proti obrazu (křížová korelace obálek po minutách) a hotový zvuk znovu přepiš Whisperem.
- [ ] Whoosh/efekt nesmí dozvukem překrýt první slovo po střihu (vrchol ~0,1 s před střihem, dozvuk zkrátit).
- [ ] Efekty změřené earshotem (`timeline` proti střihům, `measure` hlasitost) – čísla uveď v odevzdání.

## Řeč
- [ ] **Slovo z Whisperu delší než ~0,8 s** = slitý opakovaný začátek věty („Ještě tady k… Ještě tady k tomuhle“) → úsek přepiš zvlášť a vezmi druhý pokus.
- [ ] **Zvuky v pozadí** (telefon, notifikace): úzkopásmový tón v pásmu 1–3 kHz → vystřihnout, pokud je mezi větami.
- [ ] Mezery **uvnitř věty** utáhni víc než mezi větami (i 0,4 s uvnitř věty působí jako „velká mezera mezi slovy“).
