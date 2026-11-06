# 1. Le problème : un agent qui se relit lui-même

## L'idée

Un agent qui rédige une réponse client peut se tromper de trois façons qui coûtent cher : inventer un fait (un montant, une date), promettre ce que l'entreprise ne tient pas (une remise, un jour de livraison), parler d'une commande à quelqu'un qui n'en est pas le titulaire.

Lui demander de se relire aide peu. Il relit avec le même contexte qui l'a fait se tromper : il sait ce qu'il voulait dire, il voit ce qu'il croit avoir écrit. Un humain qui relit son propre mail a le même défaut.

Le circuit du dépôt sépare donc trois rôles :

| Rôle | Qui | Ce qu'il sait |
|---|---|---|
| Rédacteur | la session principale de Claude Code | le ticket, la politique, la commande, et tout son raisonnement |
| Relecteur | un sous-agent | la page seule : ticket, politique, commande, brouillon |
| Porte | un script Python | rien d'autre que : ce brouillon a-t-il été approuvé ? |

La porte est la pièce qui change tout. Sans elle, le relecteur n'est qu'un conseil : le rédacteur peut l'ignorer. Avec elle, l'envoi est impossible sans approbation, quoi que le rédacteur ait compris ou décidé.

## Dans le dépôt

- `CLAUDE.md` : la boucle du rédacteur, en 5 étapes.
- `domain/policy.md` : les six règles (R1 à R6) que le relecteur applique.
- `domain/inbox/ticket-001.md` : un ticket piège, qui demande un jour de livraison garanti et une remise.

## Exercice

Lisez le ticket et la politique, puis répondez de tête : quelles deux règles un brouillon trop serviable violerait-il ?

```bash
cat domain/inbox/ticket-001.md domain/policy.md
```

Réponse : R3 (jamais de jour d'arrivée promis) et R6 (aucune compensation). Le cas 2 de `demo/cas_pratiques.py` joue exactement ce brouillon.

## À retenir

- Une consigne dans un prompt est une demande. Un script qui refuse est une garantie.
- Le relecteur juge, la porte fait respecter le jugement. Il faut les deux.
