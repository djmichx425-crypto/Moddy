# Moddy Cosmetics

Pelerynki i modele 3D (zwierzaki, czapki, dodatki) dla Moddy. Ten folder jest przeznaczony do wgrania na GitHub –
launcher odwołuje się do plików przez adresy `raw.githubusercontent.com` (bez własnej domeny).

## Zawartość

| Folder / plik | Co to jest |
|---|---|
| `capes/*.png` | Pelerynki 64×32 px (format Minecrafta) |
| `models/*.obj` + `*.mtl` | Modele 3D (1.0 = 1 blok, Y w górę, +Z = przód). Otworzysz w Blenderze, Blockbench (Import → OBJ), „Podgląd 3D” w Windows |
| `previews/*.png` | Miniatury pokazywane w launcherze |
| `catalog.json` | Lista wszystkich kosmetyk (nazwa, opis, ścieżki, miejsce przypięcia) |
| `make_cosmetics.py` | Generator – odtwarza wszystko powyższe (`py cosmetics/make_cosmetics.py`) |

Modele: Mini Bot, Galaretka, Smoczek, Duszek, Kotek, Pingwin (zwierzaki) • Korona, Kapelusz czarodzieja, Czapka Moddy,
Aureola (głowa) • Skrzydła Neon, Plecak odrzutowy (plecy) • Okulary (twarz).

## Jak wgrać na GitHub

**Sposób 1 – przeglądarka (najprościej):**
1. Wejdź na https://github.com/djmichx425-crypto/Moddy
2. **Add file → Upload files**.
3. Przeciągnij na stronę **cały folder `cosmetics`** (z `C:\Users\Mich\Python\moddy\cosmetics`) – GitHub zachowa podfoldery.
4. Na dole: **Commit changes** (gałąź `master`).

**Sposób 2 – terminal (w folderze projektu):**
```bash
git add cosmetics
git commit -m "Dodaj kosmetyki Moddy (pelerynki i modele 3D)"
git push origin master
```
(`git add cosmetics` dodaje tylko ten folder – reszta projektu zostaje u Ciebie.)

## Adresy plików po wgraniu

```
https://raw.githubusercontent.com/djmichx425-crypto/Moddy/master/cosmetics/capes/orange.png
https://raw.githubusercontent.com/djmichx425-crypto/Moddy/master/cosmetics/models/pet_cat.obj
```
Launcher używa dokładnie takich adresów (patrz `app/core/cosmetics.py`). Do czasu wgrania linki dają błąd 404.

## Własna pelerynka
Wgraj PNG 64×32 do `cosmetics/capes/` (lub do dowolnego repozytorium), otwórz plik na GitHubie → **Raw** → skopiuj adres
i wklej w Moddy → Kosmetyki → Pelerynki → „Własna pelerynka”.

## Dodawanie nowych kosmetyk
Modele to proste prostopadłościany zdefiniowane w `make_cosmetics.py` (funkcje `pet_*`, `hat_*`…). Dodaj funkcję, wpis do listy
`ITEMS`, uruchom skrypt, wgraj zmiany. Aby nowy element pojawił się też w launcherze, trzeba wydać nową wersję Moddy
(katalog i miniatury są w niej dołączone).
