# Titulky a texty přímo ve strih.py

Jednoduché texty umí `strih.py` bez HyperFrames (ASS titulky přes ffmpeg). Na grafiku podle stylu (karty, počítadla, přechody) použij HyperFrames (`grafika.md`).

## Tři vrstvy textu
| Vrstva | K čemu | Jak vypadá | V EDL |
|---|---|---|---|
| 1. Titulky řeči | dá se sledovat bez zvuku | podle stylu níže, dole uprostřed | `"titulky"` |
| 2. Popisky | čísla, klíčová slova, výčty, nadpis začátku | velké verzálky v boxu barvy značky, naskočí na slovo | `"popups"` (`pop: true`) |
| 3. Trvalé prvky | cena, pruh s akcí, logo | malý box v rohu nebo nahoře, celé video | `"popups"` (`pop: false, sfx: false`) |

Najednou nejvýš titulky + jeden popisek. Nikdy přes obličej. Na B-rollu nad nebo pod předmětem, ne přes něj.

## Styly titulků
| Styl | Kdy | Nastavení |
|---|---|---|
| `karaoke` | mluvící hlava, delší věty | 2–4 slova na řádek, bílé tučné s obrysem, **aktuální slovo v boxu barvy značky**, velikost 60–66 |
| `slova` | rychlé tempo, emoce | 1–2 slova, velké (85–100), čísla a `zvyraznit` barvou |
| `vety` | klidný hlas, produkt + hlas | delší úsek (do 30 znaků), menší (50–56) |

- Text titulků se bere z opraveného `text` v segmentu. Časy slov dodá Whisper, když sedí počet slov; jinak se text rozprostře přes `speech_from`–`speech_to`.
- Číslo drží s jednotkou (15 mm, 150 kg, 319 Kč) a nikdy nezůstane osamocené slovo na řádku (kromě stylu `slova`).
- Čárky a tečky na konci se nezobrazují, ? a ! zůstávají.
- **Pravopis oprav v `text`** – Whisper se plete hlavně ve jménech, značkách a odborných slovech.

## Popisky a nadpisy
- Čísla a klíčová slova: 100–130 px, verzálky, prostrkání, box barvy značky (nebo černý).
- Naskočí přesně na slovo, které zazní: z 30 % přes 112 % na 100 % za 0,23 s s tichým pop.
- Výčet: jedna položka = jeden záběr 0,6–1 s + popisek. Seznam pod sebou naskakuje po 0,4–0,6 s (každý řádek samostatný popup se stejným `t_to`).
- Nadpis začátku: nejvýš 8 slov, y 300–800.

## Bezpečná zóna
- 9:16 (1080×1920): text v **y 270–1250** a **x 65–1015**. Titulky kolem y 1150–1250, popisky nad nimi, nadpis nahoře (y 300–800).
- 4:5 a 1:1: okraj 60 px dokola. 16:9: okraj 5 %.

## Barvy
- Barva značky z loga nebo webu → `projekt.json` → `barvy.zvyrazneni` (titulky) a `barvy.box` (popisky).
- Bílý text s černým obrysem je čitelný všude. Na boxu: bílý text na tmavém nebo barevném, černý na žlutém.

## Hlas
- High-pass 80 Hz, kompresor 2,5:1, limiter, 20 ms prolnutí na každém střihu (dělá `strih.py`). Finál −14 LUFS, špička −1,5 dBTP.
- Mluvčí pomalu (pod 2,3 slova/s): nejdřív vystříhat pauzy, teprve pak případně zrychlit o 1,05–1,1× (`speed` v segmentu). Víc ne, hlas zní nepřirozeně.
