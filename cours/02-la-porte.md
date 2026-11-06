# 2. La porte : un hook qui bloque l'envoi

## L'idée

Claude Code peut lancer un script avant chaque appel d'outil : c'est un [hook `PreToolUse`](https://code.claude.com/docs/en/hooks). Le script reçoit en entrée un petit JSON (quel outil, avec quels paramètres) et répond par son code de sortie :

- `0` : l'appel passe ;
- `2` : l'appel est bloqué, et le texte écrit sur la sortie d'erreur est montré au modèle, qui sait donc pourquoi.

Tout autre code ne bloque pas. C'est un piège qu'on retrouvera au chapitre 7.

## Dans le dépôt

- `.claude/settings.json` branche le hook sur tous les outils (`"matcher": ".*"`).
- `.claude/hooks/send_gate.py` est la porte. Sa fonction `decide` tient en vingt-cinq lignes : elle regarde l'outil, puis le fichier visé ou la commande.
- Le branchement lance la porte avec `/usr/bin/python3 -I -S` : un Python du système, qui ignore ce que l'utilisateur a pu installer ou déposer dans ses propres dossiers Python. Le chapitre 7 dit pourquoi.
- `tools/send_reply.py` est le seul chemin d'envoi. Il revérifie le verdict de son côté, si bien qu'il refuse aussi quand on le lance à la main, hors de Claude Code.

## Exercice

Avec la fonction `porte` du sommaire :

```bash
porte "python3 tools/send_reply.py"          # code 2 : No draft at outbox/draft.md.
echo "Hello Jonas" > outbox/draft.md
porte "python3 tools/send_reply.py"          # code 2 : No reviewer verdict.
porte "ls domain"                            # code 0 : le travail ordinaire passe
porte "cp outbox/draft.md outbox/sent/x.md"  # code 2 : copier à la main est interdit
```

Puis lancez le script d'envoi directement, sans passer par la porte :

```bash
python3 tools/send_reply.py; echo "code $?"  # refuse aussi : la vérification est en double
```

## À retenir

- Le code de sortie 2 est le seul qui bloque. Une porte qui plante avec un autre code laisse tout passer.
- La raison du blocage doit être utile au modèle : il la lit et corrige.
- Vérifier deux fois (dans le hook et dans le script d'envoi) coûte trois lignes et protège le jour où le hook ne tourne pas.
