pip install -r requirements.txt

1️⃣ Lancer vos conteneurs Docker localement

Si tu as déjà ton docker-compose.yml, les commandes de base sont :

Construire les images :
``
docker-compose build
``

Démarrer les services :
``
docker-compose up -d
``

-d = détaché, tourne en arrière-plan

Vérifie que PostgreSQL, Kafka et autres services sont bien up

Vérifier les conteneurs :
``
docker ps
``

Tu devrais voir postgres, kafka, zookeeper, etc.

Arrêter les conteneurs :
``
docker-compose down
``

2️⃣ Tester les logs pour debug
``
docker-compose logs -f
``

-f = suivi en temps réel

Utile pour voir si le Collector Agent reçoit bien les messages Kafka
