# Aperçu du Projet

Ce projet est une API REST Django pour un système de gestion de file d'attente virtuelle appelé "SmartQueue", adapté pour le Sénégal. Il fournit un backend complet pour la gestion des files d'attente virtuelles, des rendez-vous et des services connexes pour divers types d'organisations telles que les banques, les hôpitaux et les administrations publiques.

## Technologies Principales

*   **Backend :** Django, Django REST Framework
*   **Authentification :** JWT (JSON Web Tokens)
*   **Fonctionnalités en temps réel :** Django Channels (WebSockets)
*   **Base de données :** SQLite (développement), PostgreSQL (production)
*   **Cache :** En mémoire (développement), Redis (production)
*   **Tâches asynchrones :** Celery
*   **Documentation de l'API :** drf-spectacular (Swagger UI)

## Architecture

Le projet suit une architecture modulaire avec plusieurs applications Django, chacune responsable d'un domaine spécifique :

*   `accounts` : Gestion des utilisateurs et authentification.
*   `business` : Organisations et services.
*   `queue_management` : Files d'attente et tickets.
*   `appointments` : Rendez-vous et planification.
*   `locations` : Fonctionnalités de géolocalisation spécifiques au Sénégal.
*   `notifications` : SMS et autres notifications.
*   `payments` : Paiements mobiles (Wave, Orange Money).
*   `analytics` : Analyse de données et rapports.
*   `core` : Fonctionnalités de base, utilitaires et gestion des WebSockets.

# Compilation et Exécution

## Prérequis

*   Python 3.x
*   Environnement virtuel

## Installation

1.  **Clonez le dépôt :**
    ```bash
    git clone <url-du-depot>
    cd smartqueue
    ```

2.  **Créez et activez un environnement virtuel :**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3.  **Installez les dépendances :**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Appliquez les migrations de la base de données :**
    ```bash
    python manage.py migrate
    ```

## Lancer le Serveur de Développement

Pour lancer le serveur de développement Django, utilisez la commande suivante :

```bash
python manage.py runserver
```

L'API sera disponible à l'adresse `http://127.0.0.1:8000/`.

## Lancer les Tests

Pour lancer la suite de tests, utilisez la commande suivante :

```bash
pytest
```

# Conventions de Développement

*   **Style de Codage :** Le projet suit le guide de style PEP 8 pour le code Python.
*   **Conception de l'API :** L'API est conçue en utilisant le style architectural REST.
*   **Authentification :** Les points de terminaison de l'API sont sécurisés à l'aide de l'authentification JWT.
*   **Documentation de l'API :** L'API est documentée à l'aide de drf-spectacular, qui génère une interface utilisateur Swagger. La documentation est disponible à l'adresse `/api/docs/`.
*   **Internationalisation :** Le projet est configuré pour l'internationalisation (i18n) et la localisation (l10n), avec prise en charge du français, du wolof et de l'anglais.
*   **Variables d'Environnement :** Le projet utilise `django-environ` pour gérer les variables d'environnement. Un fichier `.env` est utilisé pour stocker les paramètres spécifiques à l'environnement.
