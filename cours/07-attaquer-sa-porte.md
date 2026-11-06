# 7. Attaquer sa propre porte

## L'idée

Une porte qu'on n'a jamais essayé de forcer n'est pas une porte, c'est une hypothèse. La bonne méthode : confier l'attaque à un agent séparé, qui n'a pas écrit la porte, avec une copie jetable du dépôt.

C'est ce qui a été fait sur ce dépôt le 6 novembre 2026, deux fois. Le premier contrôle isolé a trouvé quatre contournements que les tests ne voyaient pas :

| Contournement | Pourquoi ça passait | Correction |
|---|---|---|
| Écrire dans `Outbox/Sent/` au lieu de `outbox/sent/` | le disque de macOS confond les majuscules, la porte non | comparaison sans casse ; le rédacteur ne peut plus écrire que `outbox/draft.md` |
| Lancer la copie avec l'outil `Monitor` au lieu de `Bash` | le hook n'était branché que sur Bash et les outils de fichiers | branchement sur tous les outils ; toute clé `command` est contrôlée |
| Casser `tools/verdict.py`, que la porte importe | le plantage à l'import sortait en code 1, qui ne bloque pas | import déplacé dans la protection, et `\|\| exit 2` au branchement |
| Écrire un script, puis le lancer | le script ne nommait rien de gardé au moment de la vérification | le rédacteur ne peut plus écrire de script avec Write : un seul fichier lui est ouvert |

Le contrôle suivant, sur la porte corrigée, en a trouvé six autres. Trois permettaient de modifier la porte elle-même :

| Contournement | Pourquoi ça passait | Correction |
|---|---|---|
| Écrire un script dans le brouillon, puis `bash outbox/draft.md` | le seul fichier ouvert était exécutable par le shell | le shell ne peut plus nommer `outbox` du tout |
| `cd .claude;sed ...` | après le nom, la porte attendait un espace ou un `/`, pas un `;` | la fin du nom se teste par « pas une lettre », quel que soit le caractère |
| Remplacer le brouillon par un lien vers la porte, puis écrire « le brouillon » | Write compare des chemins résolus : les deux côtés menaient à la porte | un brouillon lié est refusé, à l'écriture comme à l'envoi |
| `git checkout HEAD~1 -- .` | git ramène l'ancienne porte depuis l'historique sans la nommer | le shell ne peut plus nommer `git` |
| Déposer un `usercustomize.py` dans les dossiers Python de l'utilisateur | le Python du hook le chargeait au démarrage | hook lancé avec `/usr/bin/python3 -I -S` |
| Changer le brouillon entre la vérification et la copie | `send_reply.py` lisait le fichier deux fois | lu une fois : les octets vérifiés sont les octets rangés |

Le même contrôle a trouvé un bug inverse : le vrai relecteur ne pouvait pas enregistrer un motif sur plusieurs lignes ou avec un `;`, que la porte prenait pour un enchaînement. Le motif passe maintenant en une chaîne entre guillemets, et un test vérifie qu'un motif réaliste passe.

Chaque correction a son test, et chaque test a été lancé sur l'ancienne porte pour vérifier qu'il échouait bien. Un test qui passe sur le code bogué ne prouve rien.

La leçon la plus utile est la deuxième ligne du premier tableau : une liste d'interdits (« pas Bash vers ces dossiers ») oublie toujours un chemin. Une liste d'autorisations (« un seul fichier écrivable ») en oublie beaucoup moins, mais le second tableau montre ses deux angles morts : ce fichier unique peut être lancé ou remplacé par un lien. Et le contrôle du shell, lui, reste une liste d'interdits : il en oubliera toujours.

## Dans le dépôt

- `demo/cas_pratiques.py`, cas 3 : douze tentatives, toutes bloquées. Le script sort en code 1 si une seule passe, ce qui fait échouer l'intégration continue.
- `tests/test_gate.py` : pour le premier contrôle, `test_case_does_not_open_a_way_round`, `test_any_tool_with_a_command_is_checked`, `test_broken_import_fails_closed`, `test_hook_wiring_turns_any_crash_into_a_block`, `test_writer_may_write_only_the_draft` ; pour le second, les huit tests qui suivent le commentaire « Third independent check ».

## Exercice

```bash
python3 demo/cas_pratiques.py --sans-modele      # le cas 3 seul, sans appel au modèle
porte "cp notes.md out*/sent/x.md"               # code 0 : un passage connu
porte "ls review/"                               # code 2 : un blocage inutile
```

Les deux dernières lignes montrent les deux défauts d'un contrôle qui lit le texte d'une commande : il laisse passer un nom fabriqué par le shell (`out*` devient `outbox`), et il bloque une commande inoffensive. Cherchez un troisième passage. Si vous en trouvez un, écrivez d'abord le test qui échoue, puis la correction.

## À retenir

- Faites attaquer la porte par quelqu'un qui ne l'a pas écrite.
- Préférez une liste d'autorisations à une liste d'interdits.
- Un test de sécurité se vérifie sur le code d'avant : il doit échouer.
