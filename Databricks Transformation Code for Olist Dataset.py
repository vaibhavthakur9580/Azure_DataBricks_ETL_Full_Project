# Databricks notebook source
spark

# COMMAND ----------

storage_account = "oliststorageaccountvt"
application_id = "8bd099b1-ca21-4122-9649-4753d7bcdab1"
directory_id = "dc60f1e9-6082-416e-9df7-dfe400bc7936"
service_credential = "lpn8Q~cryEuHDyZLHG71J975SiWSVVXXHGOkrbJj"


# COMMAND ----------

storage_account = "oliststorageaccountvt"
application_id = "8bd099b1-ca21-4122-9649-4753d7bcdab1"
directory_id = "dc60f1e9-6082-416e-9df7-dfe400bc7936"
service_credential = "lpn8Q~cryEuHDyZLHG71J975SiWSVVXXHGOkrbJj"

print(" Direct OAuth Configuration")
try:
    spark.conf.set(f"fs.azure.account.auth.type.{storage_account}.dfs.core.windows.net", "OAuth")
    spark.conf.set(f"fs.azure.account.oauth.provider.type.{storage_account}.dfs.core.windows.net", "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider")
    spark.conf.set(f"fs.azure.account.oauth2.client.id.{storage_account}.dfs.core.windows.net", application_id)
    spark.conf.set(f"fs.azure.account.oauth2.client.secret.{storage_account}.dfs.core.windows.net", service_credential)
    spark.conf.set(f"fs.azure.account.oauth2.client.endpoint.{storage_account}.dfs.core.windows.net", f"https://login.microsoftonline.com/{directory_id}/oauth2/token")
    print("Direct OAuth method configured!")
    
    # Test connection (uncomment when ready)
    # dbutils.fs.ls(f"abfss://your-container@{storage_account}.dfs.core.windows.net/")
    
except Exception as e:
    print(f"Direct OAuth method failed: {e}")




# COMMAND ----------

# MAGIC %md
# MAGIC # Reading Data 

# COMMAND ----------

customer_df = spark.read.format("csv").option("header", "true").load("abfss://olistdatacontainer@oliststorageaccountvt.dfs.core.windows.net/Bronze/olist_customers_dataset.csv")
display(customer_df)

# COMMAND ----------

geolocation_df = spark.read.format("csv").option("header", "true").load("abfss://olistdatacontainer@oliststorageaccountvt.dfs.core.windows.net/Bronze/olist_geolocation_dataset.csv")
display(geolocation_df)

# COMMAND ----------

items_df = spark.read.format("csv").option("header", "true").load("abfss://olistdatacontainer@oliststorageaccountvt.dfs.core.windows.net/Bronze/olist_order_items_dataset.csv")
display(items_df)

# COMMAND ----------

payments_df = spark.read.format("csv").option("header", "true").load("abfss://olistdatacontainer@oliststorageaccountvt.dfs.core.windows.net/Bronze/olist_order_payments_dataset.csv")
display(payments_df)

# COMMAND ----------

reviews_df = spark.read.format("csv").option("header", "true").load("abfss://olistdatacontainer@oliststorageaccountvt.dfs.core.windows.net/Bronze/olist_order_reviews_dataset.csv")
display(reviews_df)

# COMMAND ----------

products_df = spark.read.format("csv").option("header", "true").load("abfss://olistdatacontainer@oliststorageaccountvt.dfs.core.windows.net/Bronze/olist_products_dataset.csv")
display(products_df)

# COMMAND ----------

sellers_df = spark.read.format("csv").option("header", "true").load("abfss://olistdatacontainer@oliststorageaccountvt.dfs.core.windows.net/Bronze/olist_sellers_dataset.csv")
display(sellers_df)

# COMMAND ----------

orders_df = spark.read.format("csv").option("header", "true").load("abfss://olistdatacontainer@oliststorageaccountvt.dfs.core.windows.net/Bronze/olist_orders_dataset.csv")
display(orders_df)

# COMMAND ----------

display(sellers_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Reading Data from Pymongo
# MAGIC

# COMMAND ----------

import pymongo

# COMMAND ----------

from pymongo import MongoClient

# COMMAND ----------

# importing module
from pymongo import MongoClient

hostname = "6pkdo2.h.filess.io"
database = "OlistDataNoSQL_cracknoun"
port = "27018"
username = "OlistDataNoSQL_cracknoun"
password = "0d0c823c21ed1b5792df6148fff631899f397d21"

uri = "mongodb://" + username + ":" + password + "@" + hostname + ":" + port + "/" + database

# Connect with the portnumber and host
client = MongoClient(uri)

# Access database
mydatabase = client[database]
mydatabase

# COMMAND ----------

import pandas as pd
collection = mydatabase["product_categories"]

mongo_data = pd.DataFrame(list(collection.find()))



# COMMAND ----------

display(products_df)

# COMMAND ----------

mongo_data

# COMMAND ----------

# MAGIC %md
# MAGIC # Cleaning the DATA

# COMMAND ----------

from pyspark.sql.functions import col, to_date, datediff, current_date, when

# COMMAND ----------

def clean_dataframe(df,name):
    print('cleaning ', name)
    return df.dropDuplicates().na.drop('all')

orders_df = clean_dataframe(orders_df, "Orders")
display(orders_df)

# COMMAND ----------

orders_df = orders_df.withColumn('order_purchase_timestamp', to_date(col("order_purchase_timestamp")))\
    .withColumn("order_delivered_customer_date", to_date(col("order_delivered_customer_date")))\
        .withColumn("order_estimated_delivery_date", to_date(col("order_estimated_delivery_date")))

# COMMAND ----------

orders_df = orders_df.withColumn("actual_delivery_time", datediff("order_delivered_customer_date", "order_purchase_timestamp"))
orders_df = orders_df.withColumn("estimated_delivery_time", datediff("order_estimated_delivery_date", "order_purchase_timestamp"))
orders_df = orders_df.withColumn("delay_days", when(col("actual_delivery_time") > col("estimated_delivery_time"), col("actual_delivery_time") - col("estimated_delivery_time")).otherwise(0))
orders_df =  orders_df.withColumn("if_delayed", col("actual_delivery_time") > col("estimated_delivery_time"))
orders_df = orders_df.drop("delay")
orders_df = orders_df.withColumn("days_delayed", col("delay_days"))
orders_df = orders_df.drop("delay_days")

display(orders_df)

# COMMAND ----------

orders_customers_df = orders_df.join(customer_df, orders_df.customer_id == customer_df.customer_id, "left")
orders_payment_df = orders_customers_df.join(payments_df, orders_customers_df.order_id == payments_df.order_id, "left")
orders_items_df = orders_payment_df.join(items_df, "order_id", "left")

order_items_products_df = orders_items_df.join(products_df, orders_items_df.product_id == products_df.product_id, "left")
final_df = order_items_products_df.join(sellers_df, order_items_products_df.seller_id == sellers_df.seller_id, "left")
display(order_items_products_df)


# COMMAND ----------

mongo_data.drop(columns=["_id"], inplace=True)

# COMMAND ----------


mongo_spark_df = spark.createDataFrame(mongo_data)
display(mongo_spark_df)

# COMMAND ----------

final_df = final_df.join(mongo_spark_df, "product_category_name", "left")
display(final_df)

# COMMAND ----------

def remove_duplicate_columns(df):

    columns = df.columns
    seen = set()
    columns_to_drop = []

    for column in columns:
        if column in seen:
            columns_to_drop.append(column)
        else:
            seen.add(column)
    df_cleaned = df.drop(*columns_to_drop)
    return df_cleaned
final_df = remove_duplicate_columns(final_df)


# COMMAND ----------

final_df.write.mode("overwrite").parquet("abfss://olistdatacontainer@oliststorageaccountvt.dfs.core.windows.net/Silver")

# COMMAND ----------

# MAGIC %md
# MAGIC
