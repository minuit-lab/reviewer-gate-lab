# 3. Lier le verdict à un brouillon précis

## L'idée

Un verdict « approuvé » ne suffit pas. Le rédacteur pourrait faire approuver une version sage, puis ajouter une promesse avant d'envoyer. Il faut que l'approbation porte sur un texte exact.

La solution est une empreinte : le SHA-256 du brouillon. Deux textes qui diffèrent d'une seule lettre ont des empreintes sans rapport. Le verdict enregistre l'empreinte du brouillon relu ; au moment d'envoyer, la porte recalcule l'empreinte du brouillon actuel et compare.

Deux règles de plus :

- un verdict ne sert qu'une fois : après l'envoi, il est consommé ;
- un rejet garde son motif, que la porte renvoie au rédacteur à chaque tentative.

## Dans le dépôt

- `tools/verdict.py`, fonction `check` : toute la logique, en une vingtaine de lignes.
- `tools/record_verdict.py` : écrit `review/verdict.json` avec le verdict, le motif et l'empreinte.

## Exercice

On joue le relecteur à la main, pour voir la mécanique (c'est aussi la faille principale du labo, voir le chapitre 8) :

```bash
echo "Hello Jonas" > outbox/draft.md
python3 tools/record_verdict.py APPROVE "test à la main"
porte "python3 tools/send_reply.py"          # code 0
echo "PS: free shipping!" >> outbox/draft.md
porte "python3 tools/send_reply.py"          # code 2 : The draft changed after it was reviewed.
shasum -a 256 outbox/draft.md                # l'empreinte actuelle
cat review/verdict.json                      # l'empreinte approuvée : elles diffèrent
```

## À retenir

- On approuve un texte, pas une intention. L'empreinte rend la retouche après coup visible.
- Tout l'état tient dans des fichiers lisibles : supprimer `review/verdict.json` annule l'approbation.
