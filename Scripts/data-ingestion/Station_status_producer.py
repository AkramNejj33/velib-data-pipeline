import requests
import json
from kafka import KafkaProducer
from time import sleep
import os

# Configuration Kafka
# Utilise la variable d'environnement ou valeur par défaut pour Docker
KAFKA_BROKER = os.environ.get('KAFKA_BROKER', 'kafka:9092')
TOPIC_NAME = 'velib-station-status'

# Initialisation du producteur Kafka avec des paramètres de reconnexion
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    key_serializer=lambda k: k.encode('utf-8'),
    retries=5,
    retry_backoff_ms=1000
)

def velib_data_ingestion():
    """Récupère les données de l'API station_status."""
    API = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_status.json"
    response = requests.get(API)
    if response.status_code == 200:
        return response.json()["data"]["stations"]
    else:
        print(f"Erreur lors de l'appel à l'API : {response.status_code}")
        return []

def send_station_status_to_kafka(stations):
    """Envoie les données des stations à Kafka."""
    for station in stations:
        station_id = station['station_id']
        producer.send(
            topic=TOPIC_NAME,
            key=str(station_id),
            value=station
        )
        print(f"Données envoyées : {station}")

if __name__ == "__main__":
    # Attendre que Kafka soit prêt
    print("Attente de la disponibilité de Kafka...")
    sleep(30)
    
    print(f"Connexion à Kafka sur {KAFKA_BROKER}")
    
    while True:
        try:
            # Récupération des données
            stations = velib_data_ingestion()
            
            # Envoi des données à Kafka
            send_station_status_to_kafka(stations)
            
            print("Les données des stations ont été mises à jour.")
            
            break  # Sortir de la boucle si tout s'est bien passé
        except Exception as e:
            print(f"Erreur : {e}")
            sleep(60) # Attendre une minute avant de réessayer


