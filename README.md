# Marseille Alert — V1 PWA

Application web progressive pour Marseille : météo en temps réel et récupération d'événements publics.

## Sources
- Open-Meteo : météo, sans clé pour cet usage.
- API Tourisme France Évasion / DATAtourisme : événements publics, accès ouvert annoncé par data.gouv.fr.

## Lancer
Un hébergement HTTPS est recommandé pour l'installation comme web app sur iPhone et les notifications.

Exemple local : `python3 -m http.server 8080`

## Limites V1
Les notifications web nécessitent HTTPS et l'autorisation de l'utilisateur. Une surveillance réellement permanente avec notifications push nécessite ensuite un backend planifié et une source fiable pour les événements/alertes. Cette V1 ne prétend pas assurer cette surveillance en arrière-plan.


## V2 — veille automatique

Cette version ajoute un workflow GitHub Actions qui actualise toutes les 30 minutes les données publiques d'événements et la météo, puis les publie dans `data/`.

Sources :
- France Evasion / DATAtourisme pour les événements : API publique documentée sur data.gouv.fr.
- Open-Meteo pour la météo.

### Vigilance Météo-France

L'API officielle de Vigilance Météo-France est accessible avec un compte API. Elle pourra être branchée dès qu'une clé API Météo-France est ajoutée comme secret GitHub (`METEOFRANCE_API_KEY`). Sans cette clé, l'application ne prétend pas fournir la vigilance officielle.

### Notifications push

La V2 prépare la veille côté serveur, mais les notifications push iOS nécessitent encore un service push et des clés (VAPID/APNs selon l'architecture retenue). Elles ne sont pas simulées.
