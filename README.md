# 🚲 Velib Data Pipeline & ML Platform

![CI/CD](https://img.shields.io/badge/CI%2FCD-Jenkins-blue)
![Dockerized](https://img.shields.io/badge/Docker-Compose-blue)
![Airflow](https://img.shields.io/badge/Orchestration-Airflow-green)
![Spark](https://img.shields.io/badge/BigData-Spark-orange)
![MongoDB](https://img.shields.io/badge/Database-MongoDB-brightgreen)
![Prometheus](https://img.shields.io/badge/Monitoring-Prometheus-yellow)
![Grafana](https://img.shields.io/badge/Dashboard-Grafana-red)

---

## 📖 Description

Ce projet propose une plateforme complète de traitement de données et de Machine Learning autour des données Velib' Métropole. Il intègre l’ingestion temps réel, la transformation, le stockage, l’entraînement de modèles prédictifs et la supervision, le tout orchestré avec Docker, Airflow, Spark, MongoDB, Prometheus, Grafana et Jenkins.

---

## 🏗️ Architecture

```
+-------------------+      +-------------------+      +-------------------+
|  Data Ingestion   | ---> |   Data Processing | ---> |   ML Prediction   |
| (Producers Kafka) |      |   (Spark + Mongo) |      |   (Spark ML)      |
+-------------------+      +-------------------+      +-------------------+
        |                        |                           |
        v                        v                           v
   Kafka, Airflow           MongoDB, Spark             MongoDB, Jenkins
```

- **Ingestion** : Récupération des données Velib via API, injection dans Kafka.
- **Transformation** : Traitement temps réel avec Spark Streaming, stockage dans MongoDB.
- **ML** : Entraînement et prédiction avec Spark MLlib.
- **Orchestration** : Airflow pour les pipelines, Jenkins pour le CI/CD.
- **Monitoring** : Prometheus & Grafana pour la supervision.

---

## 🚀 Lancement rapide

1. **Cloner le projet**
   ```sh
   git clone https://github.com/<USERNAME>/<REPO>.git
   cd <REPO>
   ```

2. **Construire et lancer l’infrastructure**
   ```sh
   docker-compose up --build
   ```

3. **Accéder aux services**
   - **Airflow** : [http://localhost:8082](http://localhost:8082)
   - **Jenkins** : [http://localhost:8083](http://localhost:8083)
   - **Kafka UI** : [http://localhost:8080](http://localhost:8080)
   - **Mongo Express** : [http://localhost:8081](http://localhost:8081)
   - **Prometheus** : [http://localhost:9090](http://localhost:9090)
   - **Grafana** : [http://localhost:3000](http://localhost:3000) (admin/admin)

---

## 📂 Structure du projet

```
.
├── dags/                # DAGs Airflow pour l'orchestration
├── Scripts/
│   ├── data-ingestion/  # Scripts producteurs Kafka
│   ├── data-transformation/ # Traitement Spark Streaming
│   └── ML_model/        # Modèle de prédiction Spark ML
├── tests/               # Tests unitaires (pytest)
├── docker-compose.yml   # Stack multi-services
├── Jenkinsfile          # Pipeline CI/CD Jenkins
├── prometheus.yml       # Config Prometheus
├── requirements.txt     # Dépendances Python
└── ...
```

---

## ⚙️ Principaux composants

- **Airflow** : Orchestration des tâches ETL et ML.
- **Kafka** : Bus de messages pour ingestion temps réel.
- **Spark** : Traitement et ML distribué.
- **MongoDB** : Stockage NoSQL des données traitées.
- **Jenkins** : CI/CD automatisé (tests, build, déploiement).
- **Prometheus & Grafana** : Monitoring et dashboards.

---

## 🧪 Tests

Lance les tests unitaires avec :
```sh
pytest tests/
```

---

## 👨‍💻 Auteur

- Akram33 - [akranejjari726m@gmail.com](mailto:akranejjari726m@gmail.com)
- mezyoud mohammed
- ouiam makhoukh

---

## 📜 Licence

Ce projet est open-source sous licence MIT.

---

## 🌟 N’hésite pas à contribuer, étoiler ⭐ et proposer des améliorations !
