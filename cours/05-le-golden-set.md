# 5. Écrire un golden set

## L'idée

Un golden set est une liste de cas dont on connaît la bonne réponse. Ici, chaque cas est un ticket, un brouillon et le verdict attendu. Il sert à mesurer le relecteur, et surtout à voir s'il régresse quand on change ses consignes.

Quatre règles d'écriture :

1. **Une règle par cas.** Un brouillon qui viole deux règles à la fois ne dit pas laquelle le relecteur a vue.
2. **Autant de cas à approuver qu'à rejeter.** Sinon un relecteur qui rejette tout obtient un bon score.
3. **Chaque règle a au moins un cas à rejeter.** Une règle jamais testée n'est pas mesurée.
4. **Les étiquettes se vérifient par du code quand c'est possible.** Une étiquette fausse fausse tous les scores, sans bruit.

## Dans le dépôt

- `evals/golden.json` : 14 cas, 7 à approuver, 7 à rejeter, avec une ligne `why` chacun.
- `tests/test_golden_set.py` : recalcule les étiquettes du délai de retour à partir des dates de commande, et vérifie que les cas de confidentialité viennent bien d'une autre personne que le titulaire.

## Exercice

```bash
python3 -m unittest tests.test_golden_set -v
```

Puis lisez le cas G06 dans `evals/golden.json`. Son `why` raconte une correction du 6 novembre 2026 : le premier brouillon disait « I've refunded the full 7.99 EUR » (l'ancien texte se lit avec `git log -p evals/golden.json`), un remboursement déjà fait que la commande ne montre pas. Une passe sur trois, le relecteur l'a rejeté ([`demo/eval-3-passes-avant-G06-2026-11-06.txt`](../demo/eval-3-passes-avant-G06-2026-11-06.txt)) ; en relisant le cas, la règle en cause est R4 (les faits). Il n'avait pas tort : le cas était ambigu, pas le relecteur. Le brouillon dit maintenant « you are entitled to a full refund ».

## À retenir

- Quand le relecteur « se trompe », regardez d'abord le cas. Un cas ambigu mesure le hasard.
- Corriger un cas après une mesure se trace : date, raison, et nouvelle mesure. Sinon on finit par écrire des cas que le relecteur réussit.
