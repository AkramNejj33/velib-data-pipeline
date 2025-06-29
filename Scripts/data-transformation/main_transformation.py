from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, stddev, hour, dayofweek, expr, from_json, from_unixtime, window, round as spark_round, when, array, lit
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, ArrayType, TimestampType

# Initialize Spark session
spark = SparkSession.builder \
    .appName("KafkaSparkStreaming") \
    .config("spark.mongodb.write.connection.uri", "mongodb://mongodb:27017") \
    .getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

# Define Kafka bootstrap server
kafka_bootstrap_server = "kafka:9092"
    
# Schéma pour les topics Kafka
schema_station_status = StructType([
    StructField("station_id", StringType(), True),
    StructField("num_bikes_available", IntegerType(), True),
    StructField("num_bikes_available_types", ArrayType(
        StructType([
            StructField("mechanical", IntegerType(), True),
            StructField("ebike", IntegerType(), True)
        ])
    ), True),
    StructField("num_docks_available", IntegerType(), True),
    StructField("last_reported", DoubleType(), True),
])

schema_station_info = StructType([
    StructField("station_id", StringType()),
    StructField("stationCode", StringType()),
    StructField("name", StringType()),
    StructField("lat", DoubleType()),
    StructField("lon", DoubleType()),
    StructField("capacity", IntegerType()),
    StructField("rental_methods", ArrayType(StringType())),
    StructField("station_opening_hours", StringType()) 
])

print("Démarrage de la lecture des flux Kafka...")

# Lecture des données en temps réel
try:
    station_status_stream = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap_server) \
        .option("subscribe", "velib-station-status") \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()

    station_info_stream = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:9092") \
        .option("subscribe", "velib-station-information") \
        .option("startingOffsets", "earliest") \
        .load()
        
    print("Connexion aux topics Kafka a réussie!")
    
    # Décodage des messages Kafka (la colonne 'value') en texte
    station_status_decoded = station_status_stream.selectExpr("CAST(value AS STRING) as value", "timestamp as kafka_timestamp")
    station_info_decoded = station_info_stream.selectExpr("CAST(value AS STRING) as json_str") 
    
    # Transformation des messages JSON en DataFrame
    station_status_df = station_status_decoded.select(
        from_json(col("value"), schema_station_status).alias("data"),
        col("kafka_timestamp")
    ).select("data.*", "kafka_timestamp")

    station_info_df = station_info_decoded.select(
        from_json(col("json_str"), schema_station_info).alias("data")
    ).select("data.*")
    
    print("Décodage des données a réussie!")

    ################################################################# Cleaning ####################################################################################

    # Filtrer les lignes avec des valeurs nulles
    station_status_df = station_status_df.filter(
        (col("station_id").isNotNull()) & 
        (col("num_bikes_available") >= 0) & 
        (col("num_docks_available") >= 0) & 
        (col("last_reported").isNotNull())
    )

    station_info_df = station_info_df.filter(
        col("station_id").isNotNull() & 
        col("lat").isNotNull() & 
        col("lon").isNotNull() & 
        col("capacity").isNotNull() & 
        (col("lat").between(48.6, 49.1)) &
        (col("lon").between(2.0, 2.7))
    )

    # Conversion de last_reported en timestamp
    station_status_df = station_status_df.withColumn(
        "Timestamp", from_unixtime(col("last_reported")).cast(TimestampType())
    )

    # Supprimez la colonne last_reported
    station_status_df = station_status_df.drop("last_reported")

    # Placer la colonne 'Timestamp' en premier
    columns = ["Timestamp"] + [c for c in station_status_df.columns if c != "Timestamp"]
    station_status_df = station_status_df.select(columns)

    # Définir un Watermark
    station_status_df = station_status_df.withWatermark("Timestamp", "10 minutes")

    print("Nettoyage des données terminé")

    ############################################################# Feature Engineering ############################################################################

    # Exposer la colonne 'num_bikes_available_types'
    station_status_df = station_status_df.withColumn("mechanical_bikes", expr("num_bikes_available_types[0].mechanical"))
    station_status_df = station_status_df.withColumn("ebikes", expr("num_bikes_available_types[1].ebike"))

        
    # Supprimez la colonne num_bikes_available_types et station_opening_hours
    station_status_df = station_status_df.drop("num_bikes_available_types")
    station_info_df = station_info_df.drop("station_opening_hours")
    
    # Remplacer les NULL dans rental_methods par 'CASH'
    station_info_df = station_info_df.withColumn("rental_methods",
        when(col("rental_methods").isNull(), array(lit("CASH"))).otherwise(col("rental_methods"))
    )
    
    # DateTime Features
    station_status_df = station_status_df \
        .withColumn("hour_of_day", hour(col("Timestamp"))) \
        .withColumn("day_of_week", dayofweek(col("Timestamp"))) \
        .withColumn("is_weekend", col("day_of_week").isin([1, 7]).cast("int")) \
        .withColumn("is_rush_hour", ((col("hour_of_day").isin([7, 8, 9])) | (col("hour_of_day").isin([17, 18, 19]))).cast("int"))
        
    # Calcul du taux d'occupation
    station_status_df = station_status_df.withColumn("occupation_rate",
        spark_round(col("num_bikes_available") / (col("num_bikes_available") + col("num_docks_available")), 4)
    )

    print("Feature engineering terminé")

    # Ecriture des données dans des collections mongoDB
    station_status_df.writeStream \
        .format("mongodb") \
        .option("spark.mongodb.connection.uri", "mongodb://mongodb:27017") \
        .option("spark.mongodb.database", "velib_DB") \
        .option("spark.mongodb.collection", "station_status_collection") \
        .option("checkpointLocation", "/tmp/checkpoints/status_raw") \
        .outputMode("append") \
        .start()

    station_info_df.writeStream \
        .format("mongodb") \
        .option("spark.mongodb.connection.uri", "mongodb://mongodb:27017") \
        .option("spark.mongodb.database", "velib_DB") \
        .option("spark.mongodb.collection", "station_information_collection") \
        .option("checkpointLocation", "/tmp/checkpoints/info_raw") \
        .outputMode("append") \
        .start()
    
    print("Écriture des données dans MongoDB démarrée")
    
    ########################################################################### Data Aggregation #############################################################################

    # Suppression des duplicats exacts
    station_status_df = station_status_df.dropDuplicates(["station_id", "Timestamp", "num_bikes_available", "num_docks_available"])

    # Aggrégation par fenêtre d'une heure
    station_status_df_aggregated = station_status_df.groupBy(
        col("station_id"),
        window(col("Timestamp"), "1 hour").alias("1_hour_window") 
    ).agg(
        spark_round(avg("num_bikes_available"), 4).alias("avg_bikes_available"),
        spark_round(stddev("num_bikes_available"), 4).alias("stddev_bikes"),
        spark_round(avg("num_docks_available"), 4).alias("avg_docks_available"),
    )

    print("Agrégation des données terminée")

    station_status_df_aggregated.writeStream \
        .format("mongodb") \
        .option("spark.mongodb.connection.uri", "mongodb://mongodb:27017") \
        .option("spark.mongodb.database", "velib_DB") \
        .option("spark.mongodb.collection", "station_status_df_aggregated") \
        .option("checkpointLocation", "/tmp/checkpoints/status_aggregated") \
        .outputMode("append") \
        .start()
        
    print("Écriture des données agrégées dans MongoDB démarrée")
    
    # Combinaison des DataFrames
    df_combined = station_status_df.join(
        station_info_df,
        "station_id",
        "inner"
    )
    
    df_combined = df_combined.dropDuplicates(["station_id", "kafka_timestamp"])
    # Écriture des données combinées dans MongoDB
    df_combined.writeStream \
        .format("mongodb") \
        .option("spark.mongodb.connection.uri", "mongodb://mongodb:27017") \
        .option("spark.mongodb.database", "velib_DB") \
        .option("spark.mongodb.collection", "df_combined") \
        .option("checkpointLocation", "/tmp/checkpoints/df_combined") \
        .outputMode("append") \
        .start()

    print("Écriture des données combinées dans MongoDB démarrée")
    
    # Définir les queries de streaming pour la console (pour le débogage)
    console_query = df_combined.writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", "false") \
        .option("numRows", 50) \
        .trigger(processingTime="1 minute") \
        .start()

    print("Query console démarrée")
        
    
    # Attendre la fin du traitement
    print("Attendez la fin des queries...")
    spark.streams.awaitAnyTermination()

except Exception as e:
    print(f"Une erreur s'est produite: {str(e)}")
    import traceback
    traceback.print_exc()