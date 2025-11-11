# SMARTCITY -AGENTIC AI


## TEAM PROJECT
CHADIA ELKHARMOUDI : Lead
RACHID AIT ALI : Lead 
OUSSAMA MADIOUBI : Lead 

## virtaul envirement
``py -m venv .venv ``
``.\.venv\Scripts\Activate.ps1``
``deactivate``

## intall requirements
``pip install -r requirements.txt``

## Lancer vos conteneurs Docker localement
 
Si tu as déjà ton docker-compose.yml, les commandes de base sont :

Construire les images :
``docker-compose build``

Démarrer les services :
``docker-compose up -d``

-d = détaché, tourne en arrière-plan

Vérifie que PostgreSQL, Kafka et autres services sont bien up

Vérifier les conteneurs :
``docker ps``

Tu devrais voir postgres, kafka, zookeeper, etc.

Arrêter les conteneurs :
``docker-compose down``

### Tester les logs pour debug
``docker-compose logs -f``

-f = suivi en temps réel

Utile pour voir si le Collector Agent reçoit bien les messages Kafka


### 5️⃣ Si tu veux une interface web (facultatif)

Tu peux ajouter Kafka UI dans ton docker-compose.yml :

kafka-ui:
    image: provectuslabs/kafka-ui
    ports:
      - "8080:8080"
    environment:
      - KAFKA_CLUSTERS_0_NAME=local
      - KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS=kafka:9092

Dans ton interface :

Crée un topic principal, nommé :

``city-sensors``

Choisis un nombre de partitions (1 ou 3 pour commencer).

Laisse la réplication à 1 si tu n’as qu’un seul broker.

### run similator
``python simulator.py``

### acceder à postgresql
docker exec -it smartcity-agentic-ai-postgres-1 psql -U smartcity -d smartcitydb
