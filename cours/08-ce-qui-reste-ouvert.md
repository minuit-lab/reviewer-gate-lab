# 8. Ce qui reste ouvert

## L'idée

Un labo honnête dit ce qu'il ne prouve pas. Voici les trous connus, par ordre de gravité, et ce qu'il faudrait pour les fermer.

**1. La porte vérifie qu'un verdict existe, pas qui l'a écrit.** Le rédacteur peut lancer `record_verdict.py` lui-même et approuver son propre brouillon : c'est exactement ce que fait l'exercice du chapitre 3. Pour fermer ce trou, il faut une identité que le rédacteur ne peut pas emprunter : un verdict signé avec une clé que seul le relecteur détient, ou un processus séparé qui lance lui-même le relecteur et écrit le verdict.

**2. Le contrôle du shell est un fil-piège.** Il lit le texte de la commande. Une variable, un motif comme `out*`, un `cd` vers un nom fabriqué le contournent. Le shell peut aussi écrire hors du dépôt : le hook s'en protège en lançant un Python isolé, rien d'autre sur la machine ne l'est. La vraie réponse est hors du hook : le [bac à sable de Claude Code](https://code.claude.com/docs/en/sandboxing), ou un compte système qui n'a pas le droit d'écrire dans `review/` et `outbox/sent/`.

**3. La porte n'agit que si le hook tourne.** Un hook qui dépasse son délai ne bloque pas. Hors de Claude Code, seule la vérification de `send_reply.py` reste.

**4. L'isolement du relecteur repose sur des consignes.** Il charge `CLAUDE.md` et lit un message écrit par le rédacteur.

**5. L'éval teste le jugement, pas la boucle.** Elle colle les pièces dans un prompt ; elle ne teste ni la délégation ni la lecture des fichiers par le sous-agent.

**6. Deux contrôles, dix passages.** Le deuxième contrôle en a trouvé quatre, le troisième six, sur une porte qu'on croyait fermée. Tous sont corrigés et testés ; rien ne dit qu'il n'en reste pas.

**7. 14 cas font un test de fumée.** Un vrai support aurait besoin de cas tirés de ses propres tickets, dont les plus durs : ceux où un humain hésite.

## Pour aller plus loin

- Fermer le trou 1 avec une signature : c'est le prochain chantier naturel du dépôt.
- Ajouter des cas difficiles : un brouillon juste mais mal formulé, deux commandes dans le même ticket, une date limite le jour même.
- Lire `.github/workflows/tests.yml` : les tests et les douze tentatives du cas 3 tournent à chaque push, sur Linux et macOS, sans modèle ni clé. Ajoutez un cas, poussez, regardez le résultat.

## À retenir

- Écrire ses limites n'affaiblit pas un dépôt, ça le rend crédible.
- Chaque limite vient avec ce qui la fermerait : c'est la différence entre une excuse et un plan.
