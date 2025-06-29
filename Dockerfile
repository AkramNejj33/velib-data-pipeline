# Use Bitnami Spark base image
FROM bitnami/spark:3.4.0

# Set working directory
WORKDIR /app

# Install curl
USER root
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all scripts
COPY Scripts/data-ingestion/*.py /app/
COPY Scripts/data-transformation/main_transformation.py /app/
COPY Scripts/ML_model/predict_bikes.py /app/

# Set environment variables for Spark
ENV SPARK_HOME=/opt/bitnami/spark
ENV PATH=$SPARK_HOME/bin:$PATH

# Download Spark Kafka and MongoDB JARs
RUN curl -L -o /opt/bitnami/spark/jars/spark-sql-kafka-0-10_2.12-3.4.0.jar https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.4.0/spark-sql-kafka-0-10_2.12-3.4.0.jar
RUN curl -L -o /opt/bitnami/spark/jars/mongo-spark-connector_2.12-10.1.1.jar https://repo1.maven.org/maven2/org/mongodb/spark/mongo-spark-connector_2.12/10.1.1/mongo-spark-connector_2.12-10.1.1.jar

# Expose ports for Prometheus
EXPOSE 8080 8081 8082 8083


