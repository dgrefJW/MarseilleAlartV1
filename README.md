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
