from sqlalchemy import create_engine, text
import pyodbc
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
import os
import pickle

# Define your connection string
connection_string = "mssql+pyodbc://SHIMRIT-DESKTOP/SatPics?driver=ODBC+Driver+17+for+SQL+Server"

# Create an engine
engine = create_engine(connection_string)

if os.path.exists('geocode_cache.pkl'):
    with open('geocode_cache.pkl', 'rb') as f:
        geo_cache = pickle.load(f)
else:
    geo_cache = {}

query_keys = ['Image Link', 'Header Link', 'File1', 'File2', 'File3',
              'Date', 'Place', 'Satellite', 'Frequency Band', 'Sensor', 'Keywords']


def save_geo_cache():
    with open('geocode_cache.pkl', 'wb') as f:
        pickle.dump(geo_cache, f)


def fetch_location(geo_zone, geolocator, retries=5):
    if geo_zone in geo_cache:
        return geo_cache[geo_zone]

    attempt = 0
    while attempt < retries:
        try:
            location = geolocator.geocode(geo_zone)
            if location:
                geo_cache[geo_zone] = (location.latitude, location.longitude)
                save_geo_cache()
                return geo_cache[geo_zone]
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            attempt += 1
            time.sleep(2 ** attempt)  # Exponential backoff

    print(f"Failed to geocode {geo_zone} after {retries} attempts")
    return None


def get_geo_dict():
    with engine.connect() as connection:
        query = text(f"SELECT DISTINCT GeoZone FROM SatPictures")
        result = connection.execute(query)
        rows = [row[0] for row in result]

    geolocator = Nominatim(user_agent="AlmogSiel", timeout=5)
    geo_dict = {}

    for geo_zone in rows:
        coords = fetch_location(geo_zone, geolocator)
        if coords:
            geo_dict[geo_zone] = coords

    return geo_dict


def time_preprocess(start_date_str, end_date_str):
    start_date_str = start_date_str.replace('-', '')
    end_date_str = end_date_str.replace('-', '')
    year_start = start_date_str[:4]
    year_end = end_date_str[:4]
    year_and_month_start = start_date_str[:6]
    year_and_month_end = end_date_str[:6]
    return ((start_date_str, end_date_str),
            (year_start, year_end), (year_and_month_start, year_and_month_end))


def get_db_results(query_dict):
    where_clauses = 'WHERE '
    for key, value in query_dict.items():
        if key != "TimeTakenFinal" and key != "FreqBand" and key != "GeoZone":
            where_clauses += f"AND {key} = '{value}' "
        elif key == "TimeTakenFinal":
            dates_full, dates_year_only, dates_year_and_month = time_preprocess(value[0],
                                                                                value[1])
            where_clauses += (f"AND (({key} BETWEEN {dates_full[0]} AND {dates_full[1]}) "
                              f"OR ({key} BETWEEN {dates_year_only[0]} AND {dates_year_only[1]}) "
                              f"OR ({key} BETWEEN {dates_year_and_month[0]} AND {dates_year_and_month[1]})) ")
        elif key == "FreqBand":
            where_clauses += "AND "
            where_clauses += "AND ".join([f"{key} LIKE '%{band}%' " for band in value])
        elif key == "GeoZone":
            # where_clauses += f"AND {key} = '{value[0]}' "
            where_clauses += f"AND {key} = '{value}' "
    if where_clauses[6: 9] == 'AND':
        where_clauses = 'WHERE ' + where_clauses[10:]
    if where_clauses == 'WHERE ':
        where_clauses = ''
    with engine.connect() as connection:
        # Wrap the SQL string with text()
        query = text(f"SELECT PicPath,HeaderPath,file1,file2,file3,TimeTaken,GeoZone,"
                     f"Satellite,FreqBand,Sensor,Keywords FROM SatPictures LEFT JOIN "
                     f"FilesPath ON FilesPath.PicID = SatPictures.PicID {where_clauses}")
        print(query)

        result = connection.execute(query)
        rows = []
        for row in result:
            # Convert FreqBand slashes to commas
            row = list(row)  # Convert to mutable list
            row[8] = row[8].replace('/', ',').replace('\\', ',') if row[8] else row[8]
            rows.append(row)
            print(f"{len(rows)})", row)

        if not rows:
            raise ValueError("No Images Found :(")
        else:
            return rows


def get_keywords(query_results):
    keyword_col = 8
    keywords = set([query_result[keyword_col] for query_result in query_results])
    print(keywords)
