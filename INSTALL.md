# Instalace (návod pro Claude Code)

Tenhle soubor čte Claude, když uživatel napíše „nainstaluj skill ai-strih…“. Postupuj krok po kroku, po každém kroku ověř výsledek a na konci pusť kontrolu (krok 9). Kroky mají variantu **Mac** a **Windows** – zjisti v kroku 0, která platí, a druhou přeskakuj.

**Než začneš, řekni uživateli v pár bodech, co se nainstaluje a kolik to zabere, a počkej na souhlas:**
- Základní nástroje (ffmpeg, yt-dlp, uv, Node.js – na Macu přes Homebrew, na Windows přes winget), Whisper na přepis řeči, HyperFrames na grafiku, earshot na kontrolu zvuku, real-sfx a knihovnu 320 zvukových efektů (CC0).
- Místo na disku: ~8–10 GB (model Whisperu ~1,6 GB, earshot s modely ~2,5 GB, ffmpeg, prohlížeč pro HyperFrames).
- Čas: 15–40 minut podle rychlosti internetu. Nic se neposílá ven kromě stahování; střih běží na jeho počítači.
- Všechno se instaluje do `~/AI-strih/` a `~/.claude/skills/`. Souhlasem s instalací přijímá i licence instalovaných balíčků (na Windows je winget potvrdí za něj).

Pravidla instalace: hesla, klíče a tokeny nikdy nezadávej za uživatele – když příkaz chce heslo (Homebrew, `sudo`), řekni uživateli, ať ho spustí sám v Terminálu. Na Windows potvrzuje okno „Chcete této aplikaci povolit provádět změny?“ uživatel sám. Úpravu `~/.zshrc` předem ukaž a nech schválit. Těžké kroky (stahování modelů) spouštěj po jednom.

## 0. Počítač
`uname -sm`:
- **Mac s Apple Silicon** (`Darwin arm64`): nejrychlejší varianta, přepis běží na grafickém čipu (mlx-whisper).
- **Mac s Intelem** (`Darwin x86_64`): funguje, přepis běží na procesoru (faster-whisper) a je pomalejší.
- **Windows 10/11** (`MINGW64_NT…`): funguje, přepis běží na procesoru (faster-whisper). Claude Code na Windows spouští příkazy v Git Bash, takže příkazy níže píšeš stejně jako na Macu; cesty s `/` a `~` (= `C:\Users\<jméno>`). Ověř `winget --version` – když chybí, uživatel si z Microsoft Store nainstaluje „Instalační služba aplikace“ (App Installer).
- Doporučeno 16 GB paměti a víc. S 8 GB to půjde, ale pomalu a jen jedna úloha najednou.

## 1. Nastavení
```bash
cp ~/.claude/skills/ai-strih/nastaveni.example.json ~/.claude/skills/ai-strih/nastaveni.json
```
Zeptej se uživatele: **v jakém jazyce mluví ve videích** (`"jazyk"`: `cs`, `sk`, `en`, …; prázdné = Whisper rozpozná sám) a jestli mu vyhovuje složka projektů `~/AI-strih/projekty`. Zapiš do `nastaveni.json`.

## 2. Základní nástroje
**Mac (Homebrew):**
- Homebrew: `brew --version`. Když chybí, uživatel ho musí nainstalovat sám (chce heslo): příkaz z https://brew.sh vložit do Terminálu.
- ```bash
  brew install ffmpeg-full yt-dlp uv node git
  ```
- `ffmpeg-full` se nepřidá do PATH sám (obyčejný `ffmpeg` z Homebrew nemá filtry `drawtext` a `ass`, které skill potřebuje). Se souhlasem uživatele přidej do `~/.zshrc`:
  ```bash
  export PATH="$(brew --prefix ffmpeg-full)/bin:$PATH"
  ```
  a ověř v novém shellu: `ffmpeg -hide_banner -filters | grep -E ' (drawtext|ass) '`.

**Windows (winget):** plná verze ffmpeg (Gyan.FFmpeg) už filtry `drawtext`, `ass` a `lut3d` má. Git je nainstalovaný s Claude Code.
```bash
for id in Gyan.FFmpeg yt-dlp.yt-dlp astral-sh.uv OpenJS.NodeJS.LTS; do
  winget install -e --id "$id" --accept-source-agreements --accept-package-agreements
done
```
Nové programy uvidí Claude Code až po restartu. **Řekni uživateli, ať Claude Code zavře, znovu otevře a napíše: „Pokračuj v instalaci skillu ai-strih od kroku 3.“** Po restartu nejdřív ověř `ffmpeg -hide_banner -filters | grep -E ' (drawtext|ass) '`, `uv --version` a `node --version`.

## 3. Přepis řeči (Whisper)
**Mac s Apple Silicon:**
```bash
uv tool install mlx-whisper --with numpy
~/.claude/skills/ai-strih/scripts/py -c "import mlx_whisper, numpy; print('ok')"
```
**Windows a Mac s Intelem** (faster-whisper ve vlastním prostředí `~/AI-strih/nastroje/python`, scripts/py ho najde sám):
```bash
uv venv ~/AI-strih/nastroje/python --python 3.12
uv pip install --python ~/AI-strih/nastroje/python faster-whisper numpy
~/.claude/skills/ai-strih/scripts/py -c "import faster_whisper, numpy; print('ok')"
```
Model large-v3-turbo (~1,6 GB) se stáhne při prvním přepisu sám. Na procesoru trvá přepis zhruba tak dlouho jako záznam (na výkonném počítači méně, na slabém notebooku víc) – řekni to uživateli. Má-li kartu NVIDIA a chce přepis rychlejší, jde to přes CUDA podle https://github.com/SYSTRAN/faster-whisper#gpu a v `nastaveni.json` `"whisper_zarizeni": "cuda"` (pokročilé, volitelné).

## 4. Grafika (HyperFrames)
```bash
npm install -g hyperframes
hyperframes --version
hyperframes skills
```
`hyperframes skills` nainstaluje skilly HyperFrames do `~/.claude/skills/`. Když `npm install -g` na Macu hlásí chybu oprávnění, nastav npm prefix do domovské složky (`npm config set prefix ~/.npm-global` + PATH), nepoužívej `sudo`. Prohlížeč pro render se stáhne při prvním renderu.

## 5. Knihovna zvukových efektů (sfx-kit, CC0)
320 zvuků (~70 MB) s popisem, kdy je použít, a bodem synchronizace. Zdroj: https://huggingface.co/datasets/wyzowl/sfx-kit
```bash
mkdir -p ~/AI-strih/zvuky
uvx --from huggingface_hub hf download wyzowl/sfx-kit --repo-type dataset --local-dir ~/AI-strih/zvuky/sfx-kit
ls ~/AI-strih/zvuky/sfx-kit/sounds | head
```

## 6. earshot (Claude „slyší“ zvuk)
Open source (MIT), běží lokálně na procesoru: https://github.com/Leonxlnx/earshot
```bash
mkdir -p ~/AI-strih/nastroje
git clone https://github.com/Leonxlnx/earshot ~/AI-strih/nastroje/earshot
cd ~/AI-strih/nastroje/earshot
uv venv --python 3.12 .venv
uv pip install --python .venv torch --index-url https://download.pytorch.org/whl/cpu
uv pip install --python .venv -e ".[mcp]"
```
Pak stáhni modely (~1,1 GB) – Mac: `.venv/bin/python -m earshot doctor --fetch`, Windows: `.venv/Scripts/python.exe -m earshot doctor --fetch`.

earshot přidej do Claude Code jako MCP server a nainstaluj jeho skilly:
```bash
# Mac
claude mcp add earshot --scope user -e EARSHOT_THREADS=3 -- "$HOME/AI-strih/nastroje/earshot/.venv/bin/python" -m earshot mcp
# Windows (cesta musí být windowsová, proto cygpath)
claude mcp add earshot --scope user -e EARSHOT_THREADS=3 -e PYTHONUTF8=1 -- "$(cygpath -w "$HOME/AI-strih/nastroje/earshot/.venv/Scripts/python.exe")" -m earshot mcp
# obojí
cp -R ~/AI-strih/nastroje/earshot/skills/earshot ~/.claude/skills/earshot
cp -R ~/AI-strih/nastroje/earshot/skills/real-sound ~/.claude/skills/real-sound
```
Cestu ke složce earshot zapiš do `nastaveni.json` (`"earshot"`), pokud je jinde.

## 7. real-sfx (efekty z knihovny přesně na snímek)
Open source od Clipwing: https://github.com/Clipwing/skills
```bash
git clone --depth 1 https://github.com/Clipwing/skills ~/AI-strih/nastroje/clipwing-skills
cp -R ~/AI-strih/nastroje/clipwing-skills/skills/real-sfx ~/.claude/skills/real-sfx
cd ~/.claude/skills/real-sfx
ZVUKY="$HOME/AI-strih/zvuky/sfx-kit/sounds"; command -v cygpath >/dev/null && ZVUKY="$(cygpath -m "$ZVUKY")"
~/.claude/skills/ai-strih/scripts/py scripts/setup.py init --library main="$ZVUKY" --uisfx --index
~/.claude/skills/ai-strih/scripts/py scripts/setup.py check
```
Vlastní knihovnu zvuků uživatel přidá později: `~/.claude/skills/ai-strih/scripts/py scripts/setup.py add-library <název> <složka> --tier main --index`.

## 8. Volitelné
- Skill **watch** (Claude si „prohlédne“ video – snímky + přepis): `git clone https://github.com/bradautomates/claude-video ~/.claude/skills/watch`.

## 9. Kontrola a restart
```bash
~/.claude/skills/ai-strih/scripts/py ~/.claude/skills/ai-strih/scripts/doctor.py
```
Všechno povinné musí mít ✓. Pak řekni uživateli, ať **restartuje Claude Code** (načte MCP server earshot a nové skilly) a v novém chatu napíše třeba:
> Chci stříhat jako tenhle kanál: <odkaz>. Záběry mám ve složce <složka>.
