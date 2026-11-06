# 4. Le relecteur isolé

## L'idée

Un [sous-agent](https://code.claude.com/docs/en/sub-agents) de Claude Code démarre avec un contexte vierge : il ne voit pas la conversation du rédacteur. C'est ce qui en fait un vrai second regard. Encore faut-il ne pas lui souffler la réponse.

Trois choix comptent :

- **Ce qu'on lui passe.** Le chemin du ticket, rien d'autre. Ni le raisonnement du rédacteur, ni un résumé, ni le verdict attendu. Un relecteur à qui l'on dit « j'ai vérifié les dates » vérifiera moins les dates.
- **Ce qu'il vérifie, et dans quel ordre.** D'abord la confidentialité (R5), puis les faits (R4), puis les promesses (R1, R2, R3, R6). La faute la plus grave en premier.
- **Sa règle de doute.** « En cas de doute, rejeter. » Un faux rejet coûte une correction ; une fausse approbation coûte un client.

L'isolement reste partiel, et il faut le savoir : le sous-agent charge quand même `CLAUDE.md`, et le message de délégation est écrit par le rédacteur. Ce sont des consignes, pas des garanties.

## Dans le dépôt

- `.claude/agents/reviewer.md` : les consignes complètes du relecteur, son modèle et ses outils.
- `CLAUDE.md`, étape 3 : ce que le rédacteur a le droit de lui transmettre.

## Exercice

Lancez les trois cas pratiques (3 appels au modèle) et lisez les motifs du relecteur :

```bash
python3 demo/cas_pratiques.py
```

Regardez le cas 2 : le relecteur cite les règles par numéro (`R3: ...`, `R6: ...`). C'est voulu : un motif qui cite une règle se vérifie, un motif vague ne se vérifie pas.

Puis la boucle réelle, dans Claude Code :

```bash
claude
> Answer domain/inbox/ticket-001.md
```

Observez si le rédacteur passe bien le seul chemin du ticket au relecteur.

## À retenir

- Isoler, c'est surtout ne rien transmettre d'autre que les pièces.
- Le relecteur ne réécrit pas : il juge et nomme la règle. Corriger reste le travail du rédacteur.
