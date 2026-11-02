# Nový styl z YouTube kanálu nebo videa

Cíl: z videí, která se uživateli líbí (jeho vlastní kanál, nebo tvůrce, kterého chce napodobit), vyčíst styl tak přesně, aby šel zopakovat bez dalšího vysvětlování. Výsledek je `styly/<název>.md` podle `styly/_sablona.md`. Kopíruje se **styl střihu** (tempo, rámování, typ grafiky, zvuky), ne cizí obsah, logo ani hudba.

## 1. Výběr ukázek
- Kanál: `$PY $S/kanal.py seznam <url kanálu> [--shorts]` – seznam videí (jen metadata) seřazený podle zhlédnutí.
- Jedno video: rovnou krok 2 s odkazem.
- Zeptej se: jsou shorts a dlouhá videa stejný styl? (Většinou ne → dva styly.) Je na kanálu víc střihačů / starší videa jinak?
- Vyber 5–8 videí: nejsledovanější + nejnovější, různé délky.

## 2. Stažení (se souhlasem)
- Řekni: kolik videí, odkud, přibližně kolik MB (720p ≈ 5–8 MB/min), kam (`<projekty>/_styly/<název>/videa/`). Po souhlasu:
  `$PY $S/kanal.py stahni <složka> <ID nebo odkaz> …` (720 px stačí; titulky .vtt se stáhnou, pokud jsou).

## 3. Měření
- `$PY $S/styl_rozbor.py --out <…>/rozbor <…>/videa/*.mp4` → `styl.md` (tabulka + mediány): délka záběru, střihy za 10 s, jump cuty, tempo řeči, pokrytí řečí, pauzy, hlasitost, hudba, první slovo a první střih.
- Odhad „hudba“ je hrubý (spustí ho i zvukové efekty) – ověř přes earshot `timeline` na úseku (co kdy zní: hudba, whoosh, pop) a přes snímky.
- Doplň ručně z `rozbory/*/list.jpg` a snímků v místech textů (`ffmpeg -ss T -i v.mp4 -frames:v 1 t.jpg`):
  - **titulky**: jsou/nejsou, písmo (podobné dostupné na počítači), velikost, barva, obrys/box, kolik slov naráz, zvýraznění slova, poloha (y)
  - **grafika**: čísla, klíčová slova, šipky, emoji, lower thirds, screenshoty, karty, logo
  - **rámování**: oči na třetině?, celek/detail, přiblížení při jump cutu (o kolik), střídání úhlů
  - **přechody**: ostré střihy / zoom / švih / prolínačky; zvuky (whoosh, pop, dopad) – earshot `timeline` ukáže, kde jsou
  - **B-roll**: kolik % času, jaký (produkt, prostředí, stock, screen recording), zpomalování
  - **barvy**: teplé/studené, kontrast, saturace (`signalstats` průměr Y a SAT)
  - **hudba**: žánr, hlasitost pod řečí, střih na dobu (`measure` s `music=true` na úseku bez řeči)
  - **začátek a konec**: hook (věta, obraz, text), intro, výzva k akci, end screen
- Delší video projdi i přes skill `watch` (přepis a snímky), když potřebuješ pochopit stavbu (kapitoly, opakované prvky).

## 4. Sepsat styl
- `styly/<název>-<formát>.md` podle šablony: konkrétní čísla s rozsahem, příklady s časem („video X 0:14 – popisek ‚150 KG‘ nad hlavou“), a co styl **nedělá**.
- Na konec „Otázky pro uživatele“ – co z videí nejde poznat (přesné písmo, zdroj hudby, barvy značky).
- Ukaž uživateli shrnutí v 5–8 bodech a nech ho potvrdit. Styl je hotový, až ho uživatel potvrdí na prvním videu; připomínky k němu zapisuj do stylu.
