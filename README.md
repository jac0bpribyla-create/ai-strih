# ai-strih

Skill pro Claude Code, který stříhá videa podle stylu, který si vybereš. Pošleš mu YouTube kanál nebo video, které se ti líbí, a složku se záběry. Claude z ukázek vyčte styl (tempo, střihy, texty, přechody, zvuky) a podle něj sestříhá tvoje video.

**Jak to probíhá**
1. **Styl:** Claude stáhne pár ukázek (zeptá se předem), změří je a sepíše styl. Potvrdíš ho.
2. **Hrubý střih:** vybere nejlepší takes, vystřihne pauzy, zaváhání a kašel, nasadí B-roll na slova. Pošle ti video a tabulku, co kde je. **Dál nejde, dokud ho neschválíš.**
3. **Grafika:** texty, počítadla, karty a přechody v HyperFrames – podle stylu, nikdy přes obličej.
4. **Zvuk:** skutečné zvukové efekty z knihovny (CC0), každý vybraný a změřený nástrojem earshot, vrchol přesně na střihu. Hudba pod hlasem, hlasitost −14 LUFS.
5. **Kontrola:** problik, třes kamery, jas, pauzy, text přes obličej, zvuk proti obrazu. Co nesedí, opraví sám.
6. **Zpětná vazba:** každou tvou připomínku si zapíše do pravidel projektu nebo stylu, takže příští video je lepší.

## Instalace
Vlož do Claude Code:

> Nainstaluj skill ai-strih: naklonuj https://github.com/jac0bpribyla-create/ai-strih do ~/.claude/skills/ai-strih a postupuj podle jeho INSTALL.md.

Claude ti řekne, co nainstaluje, zeptá se na jazyk tvých videí a na konci všechno zkontroluje. Pak restartuj Claude Code.

## Co potřebuješ
- **Claude Code** s placeným plánem Claude (na zkoušku stačí Pro, na pravidelné stříhání se hodí Max).
- **Mac nebo Windows 10/11**, ideálně 16 GB paměti. Nejrychlejší je Mac s Apple Silicon (M1 a novější). Na Windows a Intel Macu běží přepis řeči na procesoru, takže trvá déle (počítej zhruba s délkou záznamu, na slabším notebooku i víc). Střih, grafika i zvuk fungují všude stejně.
- **~10 GB místa** na disku a 15–40 minut na instalaci.
- **Na Macu Homebrew** (https://brew.sh) – když ho nemáš, nainstaluješ ho jedním příkazem v Terminálu. Na Windows stačí winget, který už v systému je.

Všechno ostatní (ffmpeg, Whisper, HyperFrames, earshot, real-sfx, knihovnu zvuků) nainstaluje Claude podle INSTALL.md. Všechno je zdarma a běží na tvém počítači.

## Použití
V novém chatu napiš třeba:

> Chci stříhat jako tenhle kanál: https://www.youtube.com/@… Záběry mám ve složce ~/Desktop/natoceni.

nebo

> Sestříhej záběry v ~/Desktop/natoceni jako tohle video: https://youtu.be/…

Hotová videa najdeš v `~/AI-strih/projekty/<název>/export/`.

## Časté otázky
**Kopíruje to cizí videa?** Ne. Kopíruje se styl střihu (tempo, typ grafiky, zvuky), ne obsah, logo ani hudba.

**Odkud jsou zvuky?** Z knihovny [sfx-kit](https://huggingface.co/datasets/wyzowl/sfx-kit) (CC0, volně i komerčně). Můžeš přidat vlastní knihovnu.

**A hudba?** Jen ta, ke které máš práva (vlastní, licencovaná, YouTube Audio Library). Claude populární písničky nestahuje.

**Posílá se něco do cloudu?** Ne, střih, přepis i kontrola zvuku běží na tvém počítači. Výjimka je jen volitelné hodnocení zvuku přes Gemini, a to jen když ho výslovně povolíš.

**Počítač mi při střihu zamrzá.** Skill pouští těžké úlohy (přepis, render) po jedné. Nepouštěj víc střihových chatů najednou.

## Struktura
- `SKILL.md` – postup, který Claude dodržuje
- `INSTALL.md` – instalace (čte Claude)
- `scripts/` – střih (`strih.py`), přepis, pauzy, náhledy, rozbor stylu, grafika, kontroly, `doctor.py`
- `references/` – formát střihového listu, kontroly, zvuk, grafika, titulky, styl z kanálu
- `styly/` – šablona a ukázkový styl; sem se ukládají tvoje styly
- `assets/sfx/` – tři základní zvuky ze sfx-kit (CC0)

Licence: MIT (viz `LICENSE`). Použité nástroje třetích stran: `TRETI-STRANY.md`.
