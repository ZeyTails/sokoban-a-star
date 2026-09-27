<p align="center">
  <img src="screenshot.png" alt="Aperçu du jeu Sokoban" width="520" />
</p>

<h1 align="center">Sokoban A*</h1>

<p align="center">
  <strong>Jeu Sokoban en Python avec résolution automatique par l'algorithme de recherche A*</strong>
</p>

<p align="center">
  Projet universitaire présenté le 14 janvier
</p>

<p align="center">
  <a href="#présentation">Présentation</a> ·
  <a href="#fonctionnalités">Fonctionnalités</a> ·
  <a href="#installation">Installation</a> ·
  <a href="#utilisation">Utilisation</a> ·
  <a href="#tests">Tests</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white" alt="Python 3" />
  <img src="https://img.shields.io/badge/Pygame-interface-00A86B" alt="Pygame" />
  <img src="https://img.shields.io/badge/Tkinter-interface-4B8BBE" alt="Tkinter" />
  <img src="https://img.shields.io/badge/IA-recherche%20A*-8A2BE2" alt="Recherche A*" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="Licence MIT" />
</p>

---

## Présentation

Ce projet universitaire porte sur la résolution du jeu **Sokoban** à l'aide
d'une méthode de recherche en intelligence artificielle. Il a été présenté
le **14 janvier**.

Le projet est un fork de
[`bravegnu/python-sokoban`](https://github.com/bravegnu/python-sokoban), une
implémentation pédagogique créée pour l'apprentissage des tests unitaires.
La version présentée ici conserve le jeu d'origine et ajoute un solveur basé
sur l'algorithme **A***.

L'objectif est de permettre au joueur de résoudre les niveaux manuellement,
ou de laisser l'algorithme explorer l'espace des états et jouer
automatiquement une solution trouvée.

## Fonctionnalités

### Jeu

- Jeu Sokoban jouable avec les flèches du clavier
- Passage au niveau suivant ou précédent
- Réinitialisation du niveau courant
- Interfaces graphiques Pygame et Tkinter
- Animation de la solution générée

### Solveur A*

- Recherche dans l'espace des états du jeu
- Évaluation des états avec `f(n) = g(n) + h(n)`
- Heuristique fondée sur les distances de Manhattan entre les caisses et les
  cibles
- Détection de certains blocages, notamment les caisses placées dans des
  coins non cibles
- Reconstruction de la suite de mouvements jusqu'à l'état final
- Statistiques : coût, états explorés, états générés, taille maximale de la
  frontière et temps d'exécution
- Trace de recherche et export de l'arbre au format DOT ou JSON

## Stack technique

- **Python 3**
- **Pygame** pour l'interface principale
- **Tkinter** pour l'interface alternative
- **A*** pour la résolution automatique
- **unittest** et **unittest.mock** pour les tests du jeu
- **JSON** pour le stockage des niveaux

## Installation

### Prérequis

- Python 3
- Pygame pour lancer `sokoban.py` et exécuter les tests
- Tkinter pour lancer `sokoban_tk.py`

Installer Pygame :

```bash
python3 -m pip install pygame
```

## Utilisation

### Interface Pygame

```bash
python3 sokoban.py
```

### Interface Tkinter

```bash
python3 sokoban_tk.py
```

### Résoudre directement un niveau

Les niveaux sont indexés à partir de `0` :

```bash
python3 sokoban.py --solve-level 0
```

### Touches principales

| Touche | Action |
|---|---|
| Flèches | Déplacer le joueur |
| `S` | Lancer la résolution A* |
| `N` | Passer au niveau suivant |
| `P` | Revenir au niveau précédent |
| `R` | Réinitialiser le niveau |
| `I` | Afficher les informations du solveur |
| `1`, `2`, `3` | Régler la vitesse de l'animation |
| `E` | Exporter l'arbre dans l'interface Tkinter |
| `Q` | Quitter |

## Fonctionnement de A*

Un état du jeu est représenté par :

- la position du joueur ;
- la position de chaque caisse.

Pour chaque état, le solveur calcule :

- `g(n)` : le coût du chemin déjà parcouru ;
- `h(n)` : une estimation de la distance restante ;
- `f(n) = g(n) + h(n)` : la priorité de l'état dans la file de recherche.

Le solveur conserve le meilleur coût connu pour chaque état, écarte les
états déjà explorés avec un coût supérieur et reconstruit la solution grâce
aux relations entre les états parents et enfants.

## Tests

```bash
python3 _test_sokoban.py
```

La suite teste notamment la lecture des niveaux, la représentation du monde,
les déplacements, la poussée des caisses, la détection de victoire, les
interfaces et le chargement des niveaux.

## Structure du projet

```text
.
├── sokoban.py           # Jeu principal avec Pygame
├── sokoban_tk.py        # Interface Tkinter et animation A*
├── solver_astar.py      # Implémentation du solveur A*
├── sokoban_prolog.pl    # Modélisation alternative en Prolog
├── levels.json          # Niveaux Sokoban
├── _test_sokoban.py     # Tests unitaires
├── screenshot.png       # Capture d'écran
└── tiles/               # Images des cases du jeu
```

## Sources et crédits

- **Dépôt original forké :**
  [`bravegnu/python-sokoban`](https://github.com/bravegnu/python-sokoban)
- **Images des cases :**
  [`borgar/sokoban-skins`](https://github.com/borgar/sokoban-skins)
- **Niveaux :** collection Boxxle 1,
  [sourcecode.se](http://www.sourcecode.se/sokoban/levels)

Le code provenant du dépôt original est distribué sous licence MIT. Voir le
fichier [`LICENSE`](LICENSE).

## Licence

Projet universitaire à vocation pédagogique. Le code est distribué sous
licence **MIT**.

<p align="center">
  Projet réalisé dans le cadre d'un travail universitaire sur les méthodes
  de recherche en intelligence artificielle.
</p>
