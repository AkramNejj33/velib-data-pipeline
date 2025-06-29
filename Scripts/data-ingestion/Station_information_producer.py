import requests
from kafka import KafkaProducer
import json
from time import sleep
import os

# Configuration de Kafka
# Utilise la variable d'environnement ou valeur par défaut pour Docker
KAFKA_BROKER = os.environ.get('KAFKA_BROKER', 'kafka:9092')
TOPIC_NAME = 'velib-station-information'

# Configuration du producteur Kafka avec des paramètres de reconnexion
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    key_serializer=lambda k: str(k).encode('utf-8'),
    retries=5,
    retry_backoff_ms=1000
)

def velib_data_ingestion():
    """Récupère les données de l'API station_information."""
    API = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_information.json"
    response = requests.get(API)
    if response.status_code == 200:
        return response.json().get('data', {}).get('stations', [])
    else:
        print(f"Erreur lors de la récupération des données : {response.status_code}")
        return []

def send_station_information_to_kafka(stations):
    """Envoie les informations des stations dans Kafka."""
    for station in stations:
        station_id = station["station_id"]
        producer.send(
            topic=TOPIC_NAME,
            key=station_id,
            value=station
        )
        print(f"Envoyé : {station_id} -> {station}")

if __name__ == "__main__":
    # Attendre que Kafka soit prêt
    print("Attente de la disponibilité de Kafka...")
    sleep(30)
    
    print(f"Connexion à Kafka sur {KAFKA_BROKER}")
    
    try:
        # Récupération des données
        stations = velib_data_ingestion()
        
        # Envoi des données à Kafka
        send_station_information_to_kafka(stations)
        
        print("Les données des stations ont été mises à jour.")
        
    except Exception as e:
        print(f"Erreur lors du traitement: {e}")