from pyspark.sql import SparkSession, Window
from pyspark.sql.functions import col, lag, min, max, rand
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.regression import RandomForestRegressor, GBTRegressor
from pyspark.ml.evaluation import RegressionEvaluator
from datetime import timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Spark session
spark = SparkSession.builder \
    .appName("Bikes_Model_Training") \
    .config("spark.mongodb.read.connection.uri", "mongodb://mongodb:27017") \
    .getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

try:
    # Read data from MongoDB
    logger.info("Reading data from MongoDB...")
    df_combined = spark.read \
        .format("mongodb") \
        .option("uri", "mongodb://mongodb:27017") \
        .option("database", "velib_DB") \
        .option("collection", "df_combined") \
        .load()
    logger.info(f"Rows before processing: {df_combined.count()}")

    # Prepare data for ML
    logger.info("Preparing data for machine learning model...")
    df_ml = df_combined.select(
        "kafka_timestamp",
        "station_id",
        "Timestamp",
        "num_bikes_available", 
        "num_docks_available",
        "mechanical_bikes", 
        "ebikes",
        "hour_of_day",
        "day_of_week",
        "is_weekend",
        "is_rush_hour", 
        "occupation_rate",
        "capacity", 
        "lat",
        "lon"
    )

    # Create lag feature
    window_spec = Window.partitionBy("station_id").orderBy("kafka_timestamp")
    df_ml = df_ml.withColumn("prev_bikes_available", lag("num_bikes_available").over(window_spec))
    df_ml = df_ml.withColumn("prev_bikes_4h", lag("num_bikes_available", 4).over(window_spec))
    logger.info(f"Rows after lag creation: {df_ml.count()}")
    df_ml = df_ml.fillna({"prev_bikes_available": 0, "prev_bikes_4h": 0})
    logger.info(f"Rows after lag filter: {df_ml.count()}")

    # Feature columns
    feature_columns = [
        "prev_bikes_available",
        "prev_bikes_4h",
        "num_docks_available", 
        "mechanical_bikes", 
        "ebikes",
        "hour_of_day", 
        "day_of_week", 
        "is_weekend",
        "is_rush_hour",
        "occupation_rate",
        "capacity", 
        "lat", 
        "lon"
    ]

    # Assemble features
    assembler = VectorAssembler(inputCols=feature_columns,
                               outputCol="features",
                               handleInvalid="skip")
    df_ml = assembler.transform(df_ml)

    # Time-based data split
    logger.info("Splitting dataset temporally...")
    time_stats = df_ml.select(min("kafka_timestamp").alias("min_ts"), max("kafka_timestamp").alias("max_ts")).collect()[0]
    min_timestamp = time_stats["min_ts"]
    max_timestamp = time_stats["max_ts"]
    logger.info(f"Dataset time range: {min_timestamp} to {max_timestamp}")

    total_duration = (max_timestamp - min_timestamp).total_seconds()
    train_end = min_timestamp + timedelta(seconds=total_duration * 0.7)
    val_end = min_timestamp + timedelta(seconds=total_duration * 0.85)

    train_df = df_ml.filter(col("kafka_timestamp") <= train_end)
    validation_df = df_ml.filter((col("kafka_timestamp") > train_end) & (col("kafka_timestamp") <= val_end))
    test_df = df_ml.filter(col("kafka_timestamp") > val_end)

    logger.info(f"Training set size: {train_df.count()}")
    logger.info(f"Validation set size: {validation_df.count()}")
    logger.info(f"Test set size: {test_df.count()}")

    logger.info("Training set Time Interval : ")
    train_df.select(min("kafka_timestamp"), max("kafka_timestamp")).show()
    
    logger.info("Validation set Time Interval : ")
    validation_df.select(min("kafka_timestamp"), max("kafka_timestamp")).show()
    
    logger.info("Test set Time Interval : ")
    test_df.select(min("kafka_timestamp"), max("kafka_timestamp")).show()

    train_df.select("num_bikes_available").describe().show()
    validation_df.select("num_bikes_available").describe().show()
    test_df.select("num_bikes_available").describe().show()

    # Scale features
    logger.info("Scaling features...")
    scaler = StandardScaler(inputCol="features", outputCol="scaled_features")
    scaler_model = scaler.fit(train_df)
    train_df = scaler_model.transform(train_df)
    validation_df = scaler_model.transform(validation_df)
    test_df = scaler_model.transform(test_df)

    # Train Random Forest
    logger.info("Training Random Forest model...")
    rf = RandomForestRegressor(
        featuresCol="scaled_features",
        labelCol="num_bikes_available",
        numTrees=20,  
        maxDepth=5, 
        seed=42
    )
    model = rf.fit(train_df)


    # Evaluate on validation set
    logger.info("Evaluating model on validation set...")
    val_predictions = model.transform(validation_df)
    evaluator = RegressionEvaluator(
        labelCol="num_bikes_available", 
        predictionCol="prediction", 
        metricName="rmse"
    )
    val_rmse = evaluator.evaluate(val_predictions)
    
    evaluator_r2 = RegressionEvaluator(
        labelCol="num_bikes_available",
        predictionCol="prediction",
        metricName="r2"
    )
    val_r2 = evaluator_r2.evaluate(val_predictions)
    
    logger.info(f"Validation RMSE: {val_rmse}")
    logger.info(f"Validation R2: {val_r2}")

    # Evaluate on test set
    logger.info("Evaluating model on test set...")
    test_predictions = model.transform(test_df)
    test_rmse = evaluator.evaluate(test_predictions)
    test_r2 = evaluator_r2.evaluate(test_predictions)
    logger.info(f"Test RMSE: {test_rmse}")
    logger.info(f"Test R2: {test_r2}")

    # Save predictions
    logger.info("Saving predictions to MongoDB...")
    test_predictions.select(
        "station_id",
        "Timestamp", 
        "num_bikes_available", 
        "prediction",
        "hour_of_day",
        "day_of_week"
    ).write \
        .format("mongodb") \
        .option("spark.mongodb.connection.uri", "mongodb://mongodb:27017") \
        .option("spark.mongodb.database", "velib_DB") \
        .option("spark.mongodb.collection", "bike_predictions") \
        .mode("append") \
        .save()

    # Show sample predictions
    logger.info("Sample predictions:")
    test_predictions.select(
        "station_id",
        "kafka_timestamp",
        "num_bikes_available",
        "prediction"
    ).orderBy(rand()).show(20, truncate=False)

except Exception as e:
    logger.error(f"An error occurred: {str(e)}")
    import traceback
    traceback.print_exc()

finally:
    spark.stop()
    logger.info("Spark session stopped")
    
    
    
