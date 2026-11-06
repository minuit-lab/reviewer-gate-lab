# 6. Mesurer le relecteur

## L'idée

Un score unique (« 13 sur 14 ») cache l'essentiel. Le script sépare trois choses :

- **les fausses approbations** : une mauvaise réponse serait partie chez le client. C'est l'erreur grave ; le script sort en code 1 dès qu'il y en a une ;
- **les faux rejets** : une bonne réponse renvoyée en correction. Ça coûte du temps, pas un client ;
- **les erreurs d'appel** : le modèle n'a pas répondu. Ce n'est pas un jugement, on ne le compte ni comme approbation ni comme rejet.

Un modèle ne répond pas toujours pareil à la même question. Une seule passe ne dit donc pas grand-chose : `--runs 3` pose chaque cas trois fois et liste les cas instables, ceux qui n'ont pas reçu la même réponse à chaque passe. Un cas instable signale un cas ambigu ou une consigne floue.

## Dans le dépôt

- `evals/run_eval.py` : lit les consignes et le modèle du relecteur dans `.claude/agents/reviewer.md`, si bien qu'on mesure exactement ce que le sous-agent utilise. Chaque cas part dans un appel `claude -p` neuf, depuis un dossier vide, sans outil.
- `evals/results/` : un fichier JSON par mesure, avec la sortie complète du relecteur pour chaque cas.
- `demo/eval-3-passes-2026-11-06.txt` : une mesure en trois passes, à comparer avec la vôtre.

## Exercice

```bash
python3 evals/run_eval.py --only G03,G06 --runs 3     # 6 appels
python3 evals/run_eval.py --runs 3                    # 42 appels, la mesure complète
```

Ouvrez le JSON produit dans `evals/results/` et lisez le motif d'un cas : le relecteur cite-t-il la bonne règle ? Un bon verdict pour une mauvaise raison est une chance, pas une compétence.

## À retenir

- Mesurez avant et après chaque changement de consigne du relecteur. Sans mesure d'avant, une amélioration est une impression.
- Comptez à part ce qui coûte un client.
- Plusieurs passes, ou rien : la variance fait partie du résultat.
