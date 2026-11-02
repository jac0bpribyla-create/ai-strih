# Instalace (návod pro Claude Code)

Tenhle soubor čte Claude, když uživatel napíše „nainstaluj skill ai-strih…“. Postupuj krok po kroku, po každém kroku ověř výsledek a na konci pusť `python3 ~/.claude/skills/ai-strih/scripts/doctor.py`.

**Než začneš, řekni uživateli v pár bodech, co se nainstaluje a kolik to zabere, a počkej na souhlas:**
- Nástroje přes Homebrew (ffmpeg-full, yt-dlp, uv, Node.js), Whisper na přepis řeči, HyperFrames na grafiku, earshot na kontrolu zvuku, real-sfx a knihovnu 320 zvukových efektů (CC0).
- Místo na disku: ~8–10 GB (model Whisperu ~1,6 GB, earshot s modely ~2,5 GB, ffmpeg-full se závislostmi, prohlížeč pro HyperFrames).
- Čas: 15–40 minut podle rychlosti internetu. Nic se neposílá ven kromě stahování; střih běží na Macu.
- Všechno se instaluje do `~/AI-strih/` a `~/.claude/skills/`.

Pravidla instalace: hesla, klíče a tokeny nikdy nezadávej za uživatele – když příkaz chce heslo (Homebrew, `sudo`), řekni uživateli, ať ho spustí sám v Terminálu. Úpravu `~/.zshrc` předem ukaž a nech schválit. Těžké kroky (stahování modelů) spouštěj po jednom.

## 0. Počítač
- Mac s Apple Silicon (M1 a novější): `uname -m` → `arm64`. Na Intel Macu a Windows nefunguje přepis (mlx-whisper) – řekni to a skonči.
- Doporučeno 16 GB paměti a víc. S 8 GB to půjde, ale pomalu a jen jedna úloha najednou.

## 1. Nastavení
```bash
cp ~/.claude/skills/ai-strih/nastaveni.example.json ~/.claude/skills/ai-strih/nastaveni.json
```
Zeptej se uživatele: **v jakém jazyce mluví ve videích** (`"jazyk"`: `cs`, `sk`, `en`, …; prázdné = Whisper rozpozná sám) a jestli mu vyhovuje složka projektů `~/AI-strih/projekty`. Zapiš do `nastaveni.json`.

## 2. Základní nástroje (Homebrew)
- Homebrew: `brew --version`. Když chybí, uživatel ho musí nainstalovat sám (chce heslo): příkaz z https://brew.sh vložit do Terminálu.
- ```bash
  brew install ffmpeg-full yt-dlp uv node git
  ```
- `ffmpeg-full` se nepřidá do PATH sám (obyčejný `ffmpeg` z Homebrew nemá filtry `drawtext` a `ass`, které skill potřebuje). Se souhlasem uživatele přidej do `~/.zshrc`:
  ```bash
  export PATH="$(brew --prefix ffmpeg-full)/bin:$PATH"
  ```
  a ověř v novém shellu: `ffmpeg -hide_banner -filters | grep -E ' (drawtext|ass) '`.

## 3. Přepis řeči (Whisper)
```bash
uv tool install mlx-whisper --with numpy
~/.claude/skills/ai-strih/scripts/py -c "import mlx_whisper, numpy; print('ok')"
```
Model (~1,6 GB) se stáhne při prvním přepisu sám.

## 4. Grafika (HyperFrames)
```bash
npm install -g hyperframes
hyperframes --version
hyperframes skills
```
`hyperframes skills` nainstaluje skilly HyperFrames do `~/.claude/skills/`. Když `npm install -g` hlásí chybu oprávnění, nastav npm prefix do domovské složky (`npm config set prefix ~/.npm-global` + PATH), nepoužívej `sudo`. Prohlížeč pro render se stáhne při prvním renderu.

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
uv pip install --python .venv/bin/python torch --index-url https://download.pytorch.org/whl/cpu
uv pip install --python .venv/bin/python -e ".[mcp]"
.venv/bin/python -m earshot doctor --fetch
```
`doctor --fetch` stáhne dva modely (~1,1 GB). Pak earshot přidej do Claude Code jako MCP server a nainstaluj jeho skill:
```bash
claude mcp add earshot --scope user -e EARSHOT_THREADS=3 -- ~/AI-strih/nastroje/earshot/.venv/bin/python -m earshot mcp
cp -R ~/AI-strih/nastroje/earshot/skills/earshot ~/.claude/skills/earshot
cp -R ~/AI-strih/nastroje/earshot/skills/real-sound ~/.claude/skills/real-sound
```
`~` v příkazu `claude mcp add` nahraď plnou cestou, když ho shell nerozbalí (`echo ~` → `/Users/<jméno>`). Cestu ke složce earshot zapiš do `nastaveni.json` (`"earshot"`), pokud je jinde.

## 7. real-sfx (efekty z knihovny přesně na snímek)
Open source od Clipwing: https://github.com/Clipwing/skills
```bash
git clone --depth 1 https://github.com/Clipwing/skills ~/AI-strih/nastroje/clipwing-skills
cp -R ~/AI-strih/nastroje/clipwing-skills/skills/real-sfx ~/.claude/skills/real-sfx
cd ~/.claude/skills/real-sfx
python3 scripts/setup.py init --library main="$HOME/AI-strih/zvuky/sfx-kit/sounds" --uisfx --index
python3 scripts/setup.py check
```
Vlastní knihovnu zvuků uživatel přidá později: `python3 scripts/setup.py add-library <název> <složka> --tier main --index`.

## 8. Volitelné
- Skill **watch** (Claude si „prohlédne“ video – snímky + přepis): `git clone https://github.com/bradautomates/claude-video ~/.claude/skills/watch`.

## 9. Kontrola a restart
```bash
python3 ~/.claude/skills/ai-strih/scripts/doctor.py
```
Všechno povinné musí mít ✓. Pak řekni uživateli, ať **restartuje Claude Code** (načte MCP server earshot a nové skilly) a v novém chatu napíše třeba:
> Chci stříhat jako tenhle kanál: <odkaz>. Záběry mám ve složce <složka>.
