# Cours : faire relire un agent par un autre, et bloquer l'envoi par du code

Ce cours accompagne le dépôt. Il explique, chapitre par chapitre, pourquoi chaque pièce existe et comment la vérifier soi-même. Chaque chapitre suit le même plan : l'idée, où la voir dans le dépôt, un exercice à lancer, ce qu'il faut retenir.

Public visé : quelqu'un qui sait ouvrir un terminal et lancer Claude Code, sans être développeur. Les commandes se lancent depuis la racine du dépôt.

## Sommaire

1. [Le problème : un agent qui se relit lui-même](01-le-probleme.md)
2. [La porte : un hook qui bloque l'envoi](02-la-porte.md)
3. [Lier le verdict à un brouillon précis](03-lier-le-verdict.md)
4. [Le relecteur isolé](04-le-relecteur-isole.md)
5. [Écrire un golden set](05-le-golden-set.md)
6. [Mesurer le relecteur](06-mesurer.md)
7. [Attaquer sa propre porte](07-attaquer-sa-porte.md)
8. [Ce qui reste ouvert](08-ce-qui-reste-ouvert.md)

## Avant de commencer

```bash
python3 -m unittest discover -s tests     # 32 tests, environ 2 secondes, sans modèle
```

Si tout est vert, le dépôt est prêt. Les chapitres 4 et 6 appellent le modèle et demandent Claude Code connecté.

Pour les exercices, on simule ce que Claude Code envoie à la porte avant chaque commande. Collez cette fonction une fois dans votre terminal (zsh ou bash) :

```bash
porte() { python3 -c "import json,sys; print(json.dumps({\"tool_name\": \"Bash\", \"tool_input\": {\"command\": sys.argv[1]}}))" "$1" | python3 .claude/hooks/send_gate.py; echo "code $?"; }
```

`porte "une commande"` répond `code 0` si la porte laisse passer, `code 2` et la raison si elle bloque. Elle ne lance jamais la commande : elle dit seulement ce que la porte déciderait.

Pour tout remettre à zéro après un exercice :

```bash
rm -rf review outbox/sent outbox/draft.md
```
