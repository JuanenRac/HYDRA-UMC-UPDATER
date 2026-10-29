<!-- =============================================================================
HYDRA-UMC-UPDATER - Installs and updates the HYDRA-UMC projects
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-UPDATER banner" width="100%">
</p>

# 📦 HYDRA-UMC-UPDATER

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | 🇫🇷 <b>Français</b> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 📦 Détecte, installe et met à jour à la main tout l'écosystème HYDRA-UMC

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Language">
  <img src="https://img.shields.io/badge/Core-stdlib%20only-brightgreen.svg" alt="Core">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="Desktop">
  <img src="https://img.shields.io/badge/Tests-160%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.4.9-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

> **État de la sûreté et de la cybersécurité :** cet écosystème n'est pas un système de sécurité certifié. Il n'existe pas encore de chaîne d'E-STOP matérielle, ni de limites ou de verrouillages imposés par le firmware, ni de commande de mouvement vérifiée ; les images de firmware sont contrôlées par CRC-32 et une signature Ed25519, et une compilation de version refuse les clés de développement publiées (les têtes d'outil et les cartes d'extension derrière le relais utilisent encore les chargeurs d'URTC, qui prennent un HMAC-SHA256 à clé partagée au lieu d'une signature) ; TLS et TLS mutuel sont optionnels et désactivés par défaut ; aucune carte propre n'a encore été assemblée ni testée. Lisez la [base de sécurité](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) et le [modèle de menaces](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md) avant de vous fier à une affirmation d'ici pour la sécurité d'une personne.

---

## 📋 En un coup d'œil

| | |
|---|---|
| Version | `0.4.9` |
| Maturité | Établi |
| Tests | 160 (`python -m pytest -q tests`) |
| Technologie | Python 3.10+ / PySide6 / Qt Quick (QML) / Tkinter (legacy fallback) / Git / GitHub raw content |
| Cible | Le PC de la personne qui l'utilise |
| Sur matériel réel | Sans objet : rien ici ne s'exécute sur du matériel |

**Aller à :** [Présentation](#-présentation) · [Architecture](#-architecture) · [Sécurité et protection](#-sécurité-et-protection) · [Configuration](#-configuration) · [Démarrage rapide](#-démarrage-rapide) · [Tests](#-tests) · [Dépannage](#-dépannage) · [Structure du dépôt](#-structure-du-dépôt) · [Projets liés](#-projets-liés)

## 🚦 État du projet

Chaque ligne est une partie de ce dépôt et le feu dit où elle en est aujourd'hui. Elle est écrite d'après ce que le dépôt peut montrer (tests, compilations, exécutions), pas d'après ce qui est prévu.

🟢 Fait et vérifié · 🟡 Fonctionne, avec des limites connues · 🟠 À moitié fait ou pas encore vérifié · 🔴 Pas fait ou ne fonctionne pas

| Domaine | État | Ce que cela veut dire ici |
|---|---|---|
| Logiciel | 🟢 | Complet pour son usage et stable ; la vérification d'honnêteté ci-dessus liste les limites connues |
| Tests | 🟢 | 160 tests automatiques, exécutés à chaque modification |
| Matériel réel | 🟢 | Sans objet : rien ici ne s'exécute sur du matériel |
| Documentation | 🟢 | README en huit langues, vérifié par rapport au manifeste à chaque modification |

## 🎯 Présentation

HYDRA-UMC-UPDATER est un petit outil - GUI avec fenêtre par défaut, CLI
complète avec `--cli` - destiné à tourner aussi bien sur le vrai CM5 que
sur la propre machine Windows/Linux/macOS d'un développeur (n'importe
quel workspace avec le même type de checkout) qui répond à trois
questions pour chaque autre projet réel qu'il découvre via le propre
manifeste `hydra-umc.project.json` de chaque checkout voisin - le nombre
lui-même n'est jamais codé en dur ici, car il croît avec l'écosystème :

1. **Qu'est-ce qui est réellement installé ici, et dans quelle version ?**
2. **Quelle est la dernière version publiée sur GitHub ?**
3. **Si GitHub est plus récent, laisse-moi choisir un projet ou un lot séquentiel confirmé.**

Ce dernier point est délibéré et non négociable : cet outil ne modifie jamais
un projet de sa propre initiative. Une action sur un projet sélectionné exige
toujours une confirmation explicite. La GUI peut aussi proposer **Installer
tous les manquants** ou **Mettre à jour tous les dépassés** ; ce sont des lots
séquentiels confirmés séparément, soumis aux mêmes contrôles de manifeste, de
version et de sécurité. Il n'existe aucune mise à jour nocturne automatique. La confirmation affiche les projets exacts du lot, dans l'ordre où ils seront exécutés.

Tous les projets découverts n'appartiennent pas non plus à la CM5 elle-même - certains sont des outils qu'un développeur exécute depuis son propre PC (le firmware est compilé et flashé DEPUIS un poste de travail, pas construit SUR la cellule) ou des applications installées sur un téléphone/une montre. Le manifeste de chaque projet indique de quel cas il s'agit (voir section 3), et le tableau des projets de la GUI peut filtrer selon ce critère - tous les projets sont affichés par défaut, de sorte que l'outil de mise à jour lui-même et le SDK ne sont jamais masqués.

Exemple illustratif (le nombre exact de projets et chaque numéro de
version ci-dessous sont inventés pour la forme de la sortie, pas une
exécution réellement capturée - le vrai nombre est toujours ce que
`registry.py` découvre aujourd'hui, jamais un chiffre figé dans ce
document) :

```
$ hydra-umc-updater --cli status
Workspace root: /home/pi/HYDRA-UMC
PROJECT           MATURITY     ROLE      STACK       LOCAL     GITHUB    STATE
-----------------------------------------------------------------------------
HYDRA-UMC         functional   firmware  firmware-c  0.0.7     0.0.7     up to date
HYDRA-UMC-SERVER  functional   service   node        0.0.5     0.0.9     OUTDATED
HYDRA-UMC-STUDIO  functional   client    node        0.0.8     0.1.3     OUTDATED
...
59/59 installed, 2 outdated
Run `hydra-umc-updater update <project>` to update one by hand - never automatic, see this tool's own README.

$ hydra-umc-updater --cli update HYDRA-UMC-SERVER
Updating HYDRA-UMC-SERVER into /home/pi/HYDRA-UMC ...
OK  Updated /home/pi/HYDRA-UMC/HYDRA-UMC-SERVER to v0.0.9 (commit 1a2b3c4d5e6f) after a verified build; previous installation kept at /home/pi/HYDRA-UMC/HYDRA-UMC-SERVER.backup-9f3c2d1a
```

Lancer `hydra-umc-updater` sans argument (ou double-cliquer dessus) ouvre
la même information dans une fenêtre - un tableau de projets, un filtre
par cible de déploiement, et des boutons Installer/Mettre à jour pour la
ligne sélectionnée.

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_1.png" alt="Vue générale réelle du bureau HYDRA-UMC-UPDATER" width="100%">
</p>

## 🧩 Rôle dans HYDRA-UMC

**HYDRA-UMC-UPDATER** trouve, installe et met à jour les projets HYDRA-UMC sur la machine où il tourne, à la main et un projet à la fois. Une nouvelle version est d'abord clonée et compilée dans un dossier de préparation puis seulement déplacée en place, la précédente reste en sauvegarde, et chaque tentative laisse une ligne de preuve. Il a une ligne de commande et une fenêtre de bureau qui appellent le même cœur.

## 🏛️ Architecture

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-UPDATER architecture" width="100%">
</p>

### COMMENT FONCTIONNE VRAIMENT UNE VÉRIFICATION/MISE À JOUR

- **Source de la version** : la convention "compteur kilométrique"
  d'auto-incrémentation de cet écosystème (chaque bump explicite incrémente
  un numéro de version qui vit DANS un fichier source -
  `pyproject.toml`, `Cargo.toml`, `version.go`, `package.json`,
  `version.properties`, `pubspec.yaml`, ou un `#define` de firmware,
  selon la stack du projet) n'a jamais créé de tag git ni de GitHub
  Release pour cet incrément. Cet outil lit donc le MÊME fichier que le
  propre `bump_version.py`/script de build de chaque projet écrit déjà,
  directement depuis la branche par défaut du dépôt via l'hébergeur de
  contenu brut de GitHub - pas l'API des Releases, qui indiquerait que
  tous les projets n'ont aucune release.
- **Détection locale** : pour chaque projet découvert, vérifie si
  un répertoire portant ce nom exact existe sous la racine du workspace
  (la disposition standard de l'écosystème - chaque projet en tant que
  répertoire voisin, exactement ce que supposent déjà build-frontend.sh
  et la propre découverte de HYDRA-UMC-SUITE), et si oui, lit sa propre
  copie locale de ce même fichier de version.
- **Une seule implémentation d'analyse** (`version_parse.py`) est
  partagée entre la lecture locale et la récupération GitHub, donc un
  checkout local et une récupération GitHub ne sont jamais interprétés
  par deux regex pouvant diverger indépendamment.
- **Installer/mettre à jour** : `git clone` (installation) compile
  ensuite comme une étape séparée. Mettre à jour un checkout DÉJÀ
  EXISTANT est atomique-par-vérification à la place : le candidat est
  cloné, fusionné en fast-forward (jamais un reset forcé, donc de
  vraies modifications locales échouent bruyamment plutôt que d'être
  écrasées), puis construit/vérifié dans un clone de staging
  entièrement indépendant D'ABORD - l'installation réelle n'est touchée
  (via deux renommages de répertoire consécutifs, l'installation
  précédente étant conservée dans `<nom>.backup-xxxxxxxx`, jamais supprimée) que
  si cette compilation de staging réussit vraiment. Un échec de
  compilation, un checkout divergent/sale, un plantage ou un disque
  plein à n'importe quel moment avant cette promotion finale laissent
  l'installation précédente complètement intacte et toujours
  opérationnelle - voir la docstring propre de `clone_or_pull` dans
  `install.py`. Le remote git propre du clone de staging est restauré
  vers le dépôt GitHub réel juste après sa création (un simple clone
  local le laisserait sinon pointer vers l'ancien chemin d'installation,
  mettant fin silencieusement à toutes les futures mises à jour une fois
  promu), et les données locales réelles propres au checkout installé
  (tout ce que git considère comme non suivi ou ignoré - `data/settings.json`
  et similaires, à l'exclusion des artefacts de build régénérables) sont
  transférées dans le clone de staging avant sa compilation, afin que
  l'état opérationnel réel d'un projet survive à une mise à jour au lieu
  de rester bloqué dans le checkout `.backup` conservé. Dans tous les cas, cela exécute le `build-test.sh`/
  `build-test.bat` propre à ce projet (la vérification non-versionnante
  - voir section 3) s'il en a un. Cet outil ne réimplémente jamais les
  étapes de build propres à un projet.

- **Barrière de signature optionnelle** : le script `build-test` d'un candidat est du code que le candidat apporte lui-même et qui s'exécute ici avant que rien n'ait prouvé que le commit est bien celui du mainteneur. Avec `HYDRA_UMC_UPDATER_REQUIRE_SIGNED=1`, l'outil lance d'abord `git verify-commit` sur le candidat accepté dans le clone de staging et, si le commit n'a pas de signature à laquelle cette machine fait confiance (une clé gpg dans le trousseau, ou un signataire ssh dans `gpg.ssh.allowedSignersFile`), s'arrête là : rien n'est compilé ni exécuté et l'installation en service reste intacte. Désactivée par défaut, car elle exige sur la machine un trousseau qui fait confiance à la clé du mainteneur.

- **Un `.venv` neuf après chaque promotion** : si l'installation remplacée avait un `.venv`, le checkout promu en reçoit un nouveau (`python -m venv`, puis `pip install -r requirements.txt` quand le projet a ce fichier) au lieu de rien ; l'ancien reste dans le `.backup`. Se désactive avec `HYDRA_UMC_UPDATER_RECREATE_VENV=0` ou le réglage enregistré `recreate_venv`. S'il ne peut pas être créé, la mise à jour est signalée comme échouée et nomme la sauvegarde qui garde l'ancien.
- **Davantage de filets de sécurité** : une seule installation ou mise à jour à la fois par espace de travail (fichier de verrou) ; une limite de temps sur chaque commande git et chaque build-test, sans jamais demander d'identifiants ; une erreur inattendue devient un résultat en échec dans la fenêtre et dans le fichier de preuves, jamais une fenêtre bloquée sur « en cours » ; la barrière de signature couvre aussi une première installation et peut être activée dans les réglages enregistrés (`require_signed_commits` ; un fichier de réglages illisible compte comme activé), avec un avertissement rouge dans la fenêtre tant qu'elle est désactivée ; un commit local qui empêche l'avance rapide est nommé dans le refus ; une installation neuve dont la compilation échoue est supprimée à nouveau ; les dossiers de staging périmés sont nettoyés au début d'une exécution, et `--cli prune-backups [--keep N] [--dry-run]` supprime les anciens dossiers `<nom>.backup-xxxxxxxx` uniquement sur demande.

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_2.png" alt="Checkpoints réels pendant une installation ou mise à jour HYDRA-UMC-UPDATER" width="100%">
</p>

### ARCHITECTURE ET DÉCISIONS DE CONCEPTION

- **GUI Qt Quick par défaut, `--cli` pour le headless.** `main.py` vérifie
  `--cli` avant d'importer le runtime PySide6 optionnel. La CLI fonctionne
  sur une CM5 sans écran ni dépendance desktop ; sans argument QML démarre
  lorsqu'il est disponible et Tkinter reste seulement un fallback temporaire.
- **L'interface graphique fenêtrée est réelle, multilingue en 8 langues (`i18n.py`) - `--cli` ne l'est délibérément pas.** Chaque widget réel se réétiquette en direct depuis un `Combobox` de langue (en/es/fr/it/de/zh/ja/pt, les 8 mêmes que publient le tableau de bord public et chaque README), détecté à partir d'une préférence enregistrée ou de la locale propre du système d'exploitation. Les noms de projets/familles et le propre texte réel `notes`/`tech` de chaque projet restent non traduits - `registry.py` en est leur unique source de vérité, et 8 copies parallèles de documentation d'ingénierie réelle empêcheraient cela. La sortie de `--cli` reste volontairement en anglais uniquement : elle est destinée à être scriptée/redirigée, où un texte stable et grep-able compte plus que la localisation.
- **`deploy` est une classification, pas une restriction.** Traiter
  chaque projet découvert comme "une chose qui appartient au CM5" était une
  erreur - les dépôts de firmware sont compilés et flashés DEPUIS un PC
  (le CM5 n'a besoin que du binaire résultant via CAN-OTA, jamais du code
  source de ce dépôt), et plusieurs outils (URTC-FLASHER,
  HYDRA-UMC-SUITE, HYDRA-UMC-TOOL-CLI, ...) sont destinés à tourner sur
  le propre poste de travail d'un opérateur, pas dans la cellule
  elle-même. Le champ `deploy` de `registry.py` ("cm5" / "user-pc" /
  "mobile" / "wearable" / "dev-server") enregistre cela, et le filtre de la GUI l'utilise
  comme point de départ raisonnable - jamais comme une restriction dure,
  puisque cet outil est aussi destiné à tourner sur le propre PC d'un
  développeur, où chaque projet découvert est tout aussi légitime à inspecter.
- **Aucune logique de build par stack dans cet outil.** L'écosystème couvre 7 chaînes d'outils (Python, Rust, Go, Node/TS, Android/Kotlin, Flutter, firmware ARM). Réimplémenter `npm install && npm run build` / `cargo build --release` / `./gradlew assembleDebug` / etc. ICI créerait un second endroit qui prétend savoir compiler chaque projet, assuré de dériver des vérifications réelles (et déjà correctes) du projet lui-même. `install.py` n'exécute à la place que le `build-test.sh` non versionnant du projet (`build-test.bat` sous Windows), qui vérifie sans incrémenter aucune version ; un projet qui n'en a pas est refusé avec « No non-versioning build-test.sh/.bat found ».
- **Contenu brut de GitHub, pas l'API des Releases.** Voir la section 2 -
  la convention de versionnage de cet écosystème ne crée jamais de
  tag/release, donc l'API des Releases serait activement fausse ici, pas
  seulement moins pratique.
- **Un échec réseau transitoire reçoit un vrai réessai ; une réponse
  définitive jamais.** Chaque requête GitHub réelle (`_urlopen_with_retries`
  de `github_client.py`) réessaie jusqu'à 3 fois avec un backoff, mais
  uniquement quand la connexion n'a jamais obtenu de réponse du tout
  (DNS/timeout/reset). Un statut HTTP réel que GitHub a effectivement
  renvoyé - 404, 403, 500 - n'est jamais réessayé : GitHub a déjà
  répondu, et insister ne ferait que consommer davantage de quota pour le
  même résultat.
- **Un catalogue distant malformé échoue bruyamment ; un seul projet
  malformé non.** Si le listing des dépôts GitHub lui-même est
  injoignable ou illisible, `discover_remote_projects()` lève une
  exception - `gui.py` et `main.py` la capturent déjà tous les deux et
  retombent sur la liste de projets découverts localement plutôt que
  d'afficher un scan cassé ou vide. Le manifeste malformé d'un seul dépôt,
  en revanche, est isolé dans la liste `errors` de ce scan et n'interrompt
  jamais la découverte du reste - un vrai test avec serveur de fixtures
  (`tests/test_github_client.py`) prouve les deux chemins.
- **La CLI reste explicite ; les lots GUI restent confirmés.** Les commandes
  CLI `install`/`update` prennent un nom de projet. La GUI peut exécuter
  **Installer tous les manquants** ou **Mettre à jour tous les dépassés**,
  uniquement après confirmation séparée et de façon séquentielle par les mêmes
  contrôles de sécurité. Aucune mise à jour automatique non surveillée n'existe.
- **Bibliothèque standard uniquement.** `urllib` pour les récupérations
  GitHub (`github_client.py`), `subprocess` pour les appels git/scripts
  de build (`install.py`), rien d'autre - qu'un outil responsable de
  maintenir saines les dépendances de TOUS les autres projets reste
  lui-même sans dépendances est délibéré.
- **Simplification connue** : HYDRA-UMC et URTC sont de vrais dépôts de
  firmware multi-composants (6 et 4 binaires versionnés indépendamment
  chacun - voir leur propre `VERSION_CHECKLIST.txt`/`build_firmware.sh`)
  sans numéro de version unique. `registry.py` suit UN composant
  représentatif par dépôt - suffisant pour répondre "ce dépôt est-il à
  peu près à jour ?", pas un remplacement du propre
  `firmware_manifest.json` de `build_firmware.sh` pour un vrai flashage.

## 🔒 Sécurité et protection

| Menace | Défense | Où |
|---|---|---|
| Une nouvelle version qui ne compile pas laisse un projet à moitié mis à jour | Le candidat est d'abord cloné, fusionné et compilé dans un dossier de préparation à part ; le dossier installé n'est pas touché tant que cela n'a pas réussi, puis deux renommages le mettent en place et gardent l'ancien en `<name>.backup` | `install.py` |
| Une mise à jour qui est en réalité un retour en arrière, ou qui écarte du travail local | Le manifeste récupéré est validé et une version inférieure est rejetée ; seule une fusion en avance rapide est utilisée, et une modification locale suivie arrête la mise à jour avec un message net | `install.py`, `project_manifest.py` |
| Exécuter le code d'un commit qui n'est pas celui du mainteneur | Avec `HYDRA_UMC_UPDATER_REQUIRE_SIGNED=1` (ou le réglage enregistré) le commit cloné doit passer `git verify-commit` avant que rien de ce qu'il apporte ne soit exécuté ; un outil absent, un commit non signé ou une clé inconnue comptent comme non signé | `install.py` |

**Ce qu'il ne fait jamais :** se mettre à jour tout seul. Chaque installation et chaque mise à jour est une commande que quelqu'un lance, et le `GITHUB_TOKEN` qu'il peut lire est facultatif et n'exige qu'un accès en lecture.

## ⚙️ Configuration

| Variable | Par défaut | Ce qu'elle définit |
|---|---|---|
| `GITHUB_TOKEN` | aucun | jeton facultatif en lecture seule ; sans lui GitHub autorise 60 requêtes par heure |
| `HYDRA_UMC_UPDATER_REQUIRE_SIGNED` | `0` | `1`, `true`, `yes` ou `on` exige une signature valide sur le commit cloné |
| `HYDRA_UMC_UPDATER_RECREATE_VENV` | activé | `0` garde l'ancien environnement virtuel au lieu d'en créer un neuf après une promotion |
| `--workspace` | le dossier parent de celui-ci | dossier qui contient un sous-dossier par projet |

## 🚀 Démarrage rapide

Nécessite Python 3.10 ou plus récent.

```bash
./build.sh  # Linux, macOS (build.bat on Windows)
./run.sh --cli status --offline
./run.sh --cli status --workspace ~/hydra
./run.sh --cli install HYDRA-UMC-DATALAKE
./run.sh --cli update HYDRA-UMC-DATALAKE
./run.sh --cli prune-backups --keep 2 --dry-run
```

## 🧪 Tests

160 tests automatiques s'exécutent avec `python -m pytest -q tests`. Ils n'ont besoin ni de matériel ni de rien en dehors de cette machine.

La CI exécute `HYDRA_UMC_CI=1 python tools/ci_validate.py`, qui vérifie le manifeste, les documents, les huit README et les images.

## 🏗️ Compilation et publication

```bash
chmod +x build.sh   # une seule fois
./build.sh          # crée .venv, pip install -e ., compile-check de tout
./run.sh                              # GUI avec fenêtre (par défaut)
./run.sh --cli status                 # ce qui est installé, version locale vs. GitHub
./run.sh --cli status --offline       # pareil, sans vérifier GitHub
./run.sh --cli install <NOM-PROJET>   # clone + compile un projet pas encore installé
./run.sh --cli update  <NOM-PROJET>   # met à jour + recompile un projet déjà installé
./run.sh --cli prune-backups --keep 2  # supprime les anciens dossiers <nom>.backup-xxxxxxxx (garde les 2 plus récents de chacun)
```

Sous Windows : `build.bat`, puis `run.bat` (GUI) / `run.bat --cli status`
/ `run.bat --cli install <nom>` / `run.bat --cli update <nom>`.

La GUI préférée requiert le runtime Qt optionnel (`pip install -e ".[gui]"`;
`build.bat`/`build.sh` l'installent déjà). `--cli` n'a pas de dépendance GUI et
convient à une CM5 headless. Sans Qt, l'ancienne fenêtre Tkinter reste un
fallback de compatibilité uniquement.

**Dépannage**

- `status` affiche `?` pour la version locale ou GitHub d'un projet : son fichier de version existe, mais l'entrée `native_version` du `hydra-umc.project.json` de ce projet ne correspond plus à l'endroit où se trouve réellement sa version - corrigez le manifeste de ce projet.
- `status` affiche `-` pour GitHub sans erreur affichée : lancez `status`
  (sans `--offline`) - `-` n'apparaît que quand la vérification GitHub a
  été complètement sautée.
- `install`/`update` échoue avec « No non-versioning build-test.sh/.bat found » : ce projet n'a pas encore de `build-test.sh`/`build-test.bat` - ajoutez-lui celui, standard, de l'écosystème (il doit vérifier sans incrémenter aucune version).
- `git merge --ff-only failed` : le checkout local a un historique divergent ou des commits locaux (le message les nomme) - déplacez-les ou abandonnez-les (`git status`/`git log` dans le répertoire de ce projet) avant de relancer `update`. Les modifications non validées de fichiers suivis sont refusées d'emblée. Cet outil ne force jamais la réinitialisation d'un checkout.

## 🩺 Dépannage

| Vous voyez | Parce que | Faites |
|---|---|---|
| `unauthenticated requests are capped at 60/hour` | La limite de GitHub pour les requêtes sans jeton est atteinte | Attendez, utilisez `status --offline` ou définissez un `GITHUB_TOKEN` en lecture seule |
| the update stops and names changed files | Un fichier suivi du projet a été modifié sur cette machine | Validez, mettez de côté ou abandonnez vous-même cette modification, puis relancez `update` |

## 📂 Structure du dépôt

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-UPDATER" width="100%">
</p>

<details>
<summary>Version texte de l'arborescence</summary>

```text
HYDRA-UMC-UPDATER/
├── src/hydra_umc_updater/     code source
│   ├── __init__.py            Description et version du paquet
│   ├── registry.py            ProjectEntry - aucun catalogue statique ; construit au moment de la découverte depuis le manifeste propre de chaque dépôt
│   ├── project_manifest.py    Lit/valide un hydra-umc.project.json propre au dépôt
│   ├── ecosystem_catalog.py   Parseur du catalogue public de découverte de l'écosystème JuanenRac
│   ├── version_parse.py       UNE implémentation d'extraction regex, local+GitHub
│   ├── detect.py              Scanne une racine de workspace pour ce qui est installé
│   ├── github_client.py       Récupération concurrente du contenu brut + réessai/backoff réel pour les erreurs réseau transitoires
│   ├── install.py             git clone/pull + délègue au script de build propre
│   ├── i18n.py                Vraies traductions complètes de la GUI (8 langues)
│   ├── qt_gui.py              Pont Qt Quick vers les services réels de découverte/mise à jour
│   ├── qml/Main.qml           Shell desktop theme avec checkpoints et About
│   ├── gui.py                 Fallback Tkinter si PySide6 est indisponible
│   ├── main.py                Répartition : GUI par défaut, --cli pour status/install/update
│   ├── evidence.py            Une ligne de preuve pour chaque tentative d'installation ou de mise à jour : projet, avant, après, commit et résultat
│   ├── assets/                Les icônes de l'application (HYDRA_UMC_ICON.ico et .svg)
│   ├── i18n_pt.py             Traduction portugaise de l'interface
│   └── settings.py            Réglages utilisateur conservés (la racine de l'espace de travail et les autres choix que l'interface retient d'un lancement à l'autre)
├── tests/                     Tests réels : github_client, i18n, install, project_manifest, registry
├── docs/                      documents du projet
├── images/                    Médias, icônes de l'app et captures de l'interface
├── tools/                     outils du projet et vérifications de la CI
├── .github/                   workflow de CI et modèles de tickets
├── .env.example               Modèle de variables d'environnement
├── build.sh / build.bat       venv + installation éditable + compile-check
├── run.sh / run.bat           GUI par défaut / entrée CLI
├── run-gui.vbs                Lanceur graphique Windows sans console
├── bump_version.py            Incrément de version type compteur kilométrique (exécuté seulement par la commande `bump` explicite)
├── bump_manifest_version.py   Synchronise la version de hydra-umc.project.json avec la version native (--sync)
├── CHANGELOG.md               ce qui a changé à chaque version
├── build-test.sh              vérification de build sans modification
├── hydra-umc.project.json     manifeste : version, maturité, famille
├── pyproject.toml             métadonnées du paquet
└── test.sh                    lance les tests
```

</details>

## 🗺️ Feuille de route et limites connues

**Limites connues aujourd'hui**

- Un exécutable GUI autonome packagé (PyInstaller, suivant la propre
  convention `build_exe.bat`/`.sh` de HYDRA-UMC-SUITE) pour une
  installation en double-clic sans aucune étape `pip`/venv - aujourd'hui
  la GUI a encore besoin de `./build.sh` d'abord, comme la CLI.
- Vérification préalable optionnelle des dépendances par projet
  (signaler les chaînes d'outils manquantes - pas de Rust/Go/SDK
  Android/Flutter installé - avant qu'un `install` échoue en cours de
  route).
- Suivi par composant pour le firmware multi-binaire propre de
  HYDRA-UMC/URTC (voir la "simplification connue" de la section 3), dès
  qu'un besoin réel se fera sentir au-delà du seul composant
  représentatif suivi aujourd'hui.

## 🌍 Langues

Ce README et les documents du dépôt existent en huit langues : anglais, espagnol, allemand, français, italien, japonais, chinois et portugais (Portugal). Ils sont écrits ensemble et la CI vérifie que les huit fichiers ont les mêmes sections et les mêmes liens.

## 🔗 Projets liés

Ce projet fait partie de l'écosystème robotique HYDRA-UMC du même auteur (JuanenRac / Electro Hobby 3D). Bon à savoir, car une demande pourrait en réalité concerner l'un de ceux-ci plutôt que ce dépôt.

**Directement Liés**
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la conception de la carte mère du bras robotique : hôte CM5 + coprocesseur STM32H745 double cœur, destinée à coordonner jusqu'à 8 bras-outils via CAN-OTA/SPI-OTA (firmware à un stade précoce ; aucune carte assemblée pour l'instant).
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centre de commande d'essaim de bureau (PySide6) pour plusieurs serveurs à la fois, empaqueté en exécutable autonome — un autre outil Python autonome destiné à fonctionner aux côtés du contrôleur de cellule, le frère le plus proche en termes de rôle (un utilitaire ciblé côté CM5, ne faisant pas partie du chemin de contrôle du robot lui-même).
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — dépend de ce projet comme véritable bibliothèque pour sa propre découverte de l'écosystème sur GitHub lors de la construction d'une nouvelle image CM5, plutôt que d'une seconde implémentation pouvant dériver de façon indépendante.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordinateur d'incidents de maintenance : un rôle edge à faible privilège collecte un instantané d'inventaire/santé assaini, un rôle control-plane le rend en lecture seule et demande à un fournisseur d'IA de suggérer un diagnostic - n'applique jamais de correctif ni ne déploie rien.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — hôte de développement reproductible (Raspberry Pi 5 / CM5) qui héberge le code source de l'écosystème et exécute des tâches de compilation/test délimitées via une file d'attente durable ; un rôle de développement dédié, explicitement distinct d'un CM5 opérationnel.

**Fait Également Partie de l'Écosystème**

*Matériel & Plateforme de Base*
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — couche produit reproductible sur Raspberry Pi OS pour le CM5 : agent en lecture seule, config/profils validés, provisionnement WiFi de premier contact.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — le contrat JSON-Schema partagé et la barrière logicielle de contrôle des jobs contre laquelle chaque bridge valide ses commandes (pas une fonction de sécurité certifiée).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registre déclaratif et validateur de manifestes d'adaptateur pour les connecteurs de machines externes ; étend la propre idée de contrat du SDK aux machines externes sans remplacer les projets de passerelle industrielle.

*Backend Central & Clients*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — le vrai backend headless (REST/WebSocket) auquel parle réellement chaque client de contrôle.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — tableau de bord de contrôle web avec visualisation 3D multi-robot en temps réel.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — application de contrôle Android native avec connexion biométrique et un compagnon Wear OS jumelé.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — application de contrôle iOS/iPadOS (Flutter) avec synchronisation WebSocket en temps réel.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tactile native pour l'écran tactile DSI 7" embarqué, intégrée directement sur le CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — créateur/éditeur graphique de bureau pour URDF qui envoie les modèles terminés vers le propre catalogue de STUDIO.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — éditeur de bureau de modèles STL, transformant/remplaçant/retirant/ajoutant de vraies pièces dans le même catalogue de modèles qu'édite aussi HYDRA-UMC-EDITOR-URDF.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — frontière de coordination pour les flottes AGV/AMR via un éditeur MQTT VDA 5050 (testé uniquement contre une flotte émulée).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinateur haut niveau pour cellules CNC avec accès au statut/octets de contrôle GRBL (testé uniquement contre un émulateur).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — frontière de coordination pour droïdes à pattes/humanoïdes, avec un émetteur de commandes Boston Dynamics Spot (testé uniquement contre un émulateur).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinateur de cellules laser lisant 3 signaux GPIO de clé/enceinte/verrouillage (testé uniquement contre une puce simulée ; il ne peut ni armer ni tirer un laser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinateur haut niveau sûr pour le flux de cartes du pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — frontière de coordination sûre pour imprimantes 3D Moonraker/Klipper, avec de vraies commandes de tâche contrôlées.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinateur avec un transport ROS 2 rclpy à importation paresseuse (pas encore exécuté contre une installation ROS 2).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — frontière de coordination pour UAV équipés de caméra, avec un émetteur de commandes MAVLink (testé uniquement contre un émulateur).

*Nœud IA de Vision (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub d'intégration pour le pipeline de vision Hailo-8, avec une vraie vérification de disponibilité matérielle par étape.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registre réel de modèles compilés avec vérification de chargement sécurisé par architecture Hailo/checksum.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — générateur réel de pipeline GStreamer + config MediaMTX, avec une vraie frontière d'intégration HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — loi de correction Position-Based Visual Servoing avec autorisation conditionnée à l'état de zone ; pas encore d'estimation de pose par caméra.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — logique v0 de violation de zone, de fraîcheur de calibration et de demande d'E-STOP qui lit les positions d'objets dans un fichier ; aucun détecteur ne l'alimente et aucun E-STOP physique n'y est encore relié.

*Nœud IA Cognitif (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — hub d'intégration pour le pipeline cognitif Hailo-10 (orchestration LLM/VLA/voix).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — vrai encodage/décodage de jetons d'action et génération de trajectoire pour un modèle Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — vrai front-end vocal (VAD + analyseur d'intention) avec un relais Watch borné et soumis à confirmation.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — vraie décomposition de tâches basée sur des règles et récupération sémantique d'erreurs sur les codes d'erreur MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — vraie recherche documentaire TF-IDF (bibliothèque standard uniquement) sur les propres documents Markdown de cet écosystème.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — technicien de maintenance IA local et à portes de politique pour l'écosystème lui-même - observe, diagnostique et propose des corrections ; les deux niveaux de risque les plus élevés ne sont délibérément pas encore implémentés.

*Orchestration & Essaim*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub d'intégration avec un vrai contrat de rapport de santé gRPC/Protobuf et une machine à états de mission.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — vraie file de tâches basée sur la priorité avec déduplication, via une vraie API HTTP.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vrai chien de garde de santé de flotte basé sur gRPC, avec retry/backoff et détection d'incohérence d'identité.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — vrai planificateur de trajectoire 3D basé sur RRT, avec vraie validation des collisions obstacle/espace de travail.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — vraie synchronisation d'état CRDT LWW-Element-Map, testée par propriétés pour la convergence multi-cellule.

*Jumeau Numérique & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — hub d'intégration pour le moteur de jumeau numérique, avec un vrai contrat de synchronisation par compatibilité de version.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — routeur hardware-in-the-loop avec un verrouillage logiciel de collision entre simulation et matériel réel (testé sans matériel réel).
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — vraie cinématique directe et validation des limites articulaires sur un vrai sous-ensemble URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — vrai générateur procédural de scènes 2D avec export d'annotations YOLO/COCO.

*Données & Analytique*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — vrai magasin de séries temporelles basé sur sqlite3, avec une vraie API HTTP d'ingestion/requête.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — vrai détecteur d'anomalies FFT + ligne de base statistique, avec surveillance de dérive.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — vrai calcul OEE/disponibilité sur l'historique de DATALAKE, avec export CSV reproductible.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — vrai pipeline d'ingestion CAN/WebSocket vers DATALAKE, avec déduplication par séquence.

*Passerelle Industrielle*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — hub d'intégration relayant vers les protocoles industriels, avec une vraie couche de liste blanche de commandes/contre-pression.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — vrai espace d'adressage OPC-UA, vérifié avec une vraie session client du protocole binaire.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — vrai broker MQTT avec authentification par client optionnelle et ACL de sujets.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — vrais points de terminaison XML MTConnect `/probe` et `/current`, avec sortie en mode dégradé.

*Outils Complémentaires & Opérations de l'Écosystème*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — panneaux Smart Summaries et Anomaly Highlighting sur DATALAKE/ANOMALY-DETECTOR, avec un repli statistique honnête.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI de flotte avec un vrai contrat de codes de sortie stable, un vrai client en direct de la propre API de HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — application compagnon WearOS avec des motifs d'alerte haptique et un relais vocal vers le téléphone jumelé (pas encore exécutée sur une montre physique).

## 📚 Documentation

Où lire la suite :

* **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — chaque sous-commande `--cli`, sortie réelle capturée depuis une installation réelle, et le contrat des codes de sortie.
* **[docs/QML_DESKTOP_GUI.md](docs/QML_DESKTOP_GUI.md)** — comment le client de bureau Qt Quick/QML est structuré, et comment il reste une vraie surface de contrôle sur le même backend que `--cli` utilise, pas une seconde implémentation.
* [Base de sécurité de l'écosystème](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [Modèle de menaces de l'écosystème](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [Journal des modifications de ce dépôt](CHANGELOG.md)
* [Licence de ce dépôt](LICENSE.md)

## 🤝 Contribuer et communauté

* Avant une pull request, exécutez `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py` (ou `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`) : il doit afficher `CI_VALIDATION=PASS`. N'exécutez pas `build.sh` ni `build.bat` pour cette vérification ; compiler n'est pas vérifier.
* Les huit README sont écrits à partir d'une source unique dans HYDRA-UMC-DOCS ; ne les modifiez pas à la main. Changez la source et réécrivez-les avec `tools/make_readmes.py`.
* N'affirmez pas dans un README ce qui n'a pas tourné : écrivez « simulé » ou « non essayé sur matériel » quand c'est la vérité.
* Voir [CONTRIBUTING.md](CONTRIBUTING.md), le [code de conduite](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md) et [SUPPORT.md](SUPPORT.md).

## 👤 AUTEUR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCE

GPL-3.0-or-later - [LICENSE](LICENSE).
