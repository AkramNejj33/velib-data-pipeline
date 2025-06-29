pipeline {
    agent any

    environment {
        MODEL_DIR = 'models'
        VERSION = "v${env.BUILD_NUMBER}"
    }

    stages {
        stage('Nettoyer les anciens modèles') {
            steps {
                sh 'rm -f ${MODEL_DIR}/model_*.pkl || true'
                sh 'mkdir -p ${MODEL_DIR}'
            }
        }

        stage('Installer les dépendances') {
            steps {
                sh 'pip install -r requirements.txt'
            }
        }

        stage('Tests') {
            steps {
                echo "Lancement des tests unitaires..."
                sh 'pytest tests/'
            }
        }

        stage('Exécuter le script ML') {
            steps {
                sh 'python Scripts/ML_model/predict_bikes.py --output ${MODEL_DIR}/model_${VERSION}.pkl'
            }
        }

        stage('Archiver le modèle') {
            steps {
                archiveArtifacts artifacts: 'models/model_*.pkl', fingerprint: true
            }
        }
    }

    post {
        success {
            echo "Modèle entraîné, testé et versionné avec succès !"
        }
        failure {
            echo "Échec du pipeline : erreur dans les tests ou l’entraînement."
        }
    }
}
