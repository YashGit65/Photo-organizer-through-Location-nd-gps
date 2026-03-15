import os
import shutil
import time
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim

def get_location_name(lat, lon, geolocator):
    """Uses OpenStreetMap to find the name of the location."""
    try:
        time.sleep(1) 
        location = geolocator.reverse((lat, lon), exactly_one=True, language='en')
        if location and location.raw.get('address'):
            addr = location.raw['address']
            name = (addr.get('tourism') or addr.get('leisure') or addr.get('beach') or 
                    addr.get('suburb') or addr.get('neighbourhood') or addr.get('village') or 
                    addr.get('town') or addr.get('city') or addr.get('county'))
            if name:
                return name.replace(" ", "").lower()
    except Exception as e:
        print(f"Geocoding error: {e}")
    return "unknown_location"

def create_folders_and_copy(df, dest_dir):
    """Creates a nested folder structure: Date -> Location."""
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    geolocator = Nominatim(user_agent="my_personal_photo_organizer")
    clusters = df.groupby('cluster_id')
    
    # We now track the full path to handle collisions
    used_folder_paths = {} 

    for cluster_id, cluster_df in clusters:
        if cluster_id == -1 or pd.isna(cluster_id):
            # Outliers go straight to the manual sorting root folder
            final_folder_path = os.path.join(dest_dir, "Needs_Manual_Sorting")
        else:
            # 1. Get the Parent Folder Name (The Date)
            avg_timestamp = cluster_df['timestamp'].median()
            dt = datetime.fromtimestamp(avg_timestamp)
            date_folder = dt.strftime("%d %b").lower() # e.g., "27 feb"
            
            # 2. Get the Subfolder Name (The Location)
            avg_lat = cluster_df['lat'].mean()
            avg_lon = cluster_df['lon'].mean()
            loc_name = get_location_name(avg_lat, avg_lon, geolocator)
            
            base_sub_folder = loc_name
            sub_folder = base_sub_folder
            counter = 2
            
            # 3. Construct the nested path: dest_dir/27 feb/bagabeach
            final_folder_path = os.path.join(dest_dir, date_folder, sub_folder)
            
            # --- THE COLLISION CHECKER ---
            # If you went to "northgoa" twice on "27 feb", make "northgoa (2)"
            while final_folder_path in used_folder_paths and used_folder_paths[final_folder_path] != cluster_id:
                sub_folder = f"{base_sub_folder} ({counter})"
                final_folder_path = os.path.join(dest_dir, date_folder, sub_folder)
                counter += 1
                
            used_folder_paths[final_folder_path] = cluster_id

        # Create the nested directories (os.makedirs handles multiple levels safely)
        if not os.path.exists(final_folder_path):
            os.makedirs(final_folder_path)
            # Print the clean relative path (e.g., "27 feb\bagabeach")
            print(f"Organizing into: {os.path.relpath(final_folder_path, dest_dir)}")
            
        for _, row in cluster_df.iterrows():
            filepath = row['filepath']
            filename = os.path.basename(filepath)
            dest_path = os.path.join(final_folder_path, filename)
            try:
                shutil.copy2(filepath, dest_path)
            except Exception as e:
                print(f"Error copying {filepath}: {e}")