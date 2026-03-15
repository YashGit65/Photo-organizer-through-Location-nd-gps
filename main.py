import os
import shutil
import database
import extractor
import clusterer
import organizer

def run_pipeline(source_dir, dest_dir, db_path="photos.db", eps=0.5, min_samples=2):
    print("1. Initializing Database...")
    database.init_db(db_path)
    
    # Create our safety net folder
    manual_sort_dir = os.path.join(dest_dir, "Needs_Manual_Sorting")
    if not os.path.exists(manual_sort_dir):
        os.makedirs(manual_sort_dir)
        
    stats = {"processed": 0, "no_metadata": 0, "unsupported_format": 0}

    print("2. Extracting EXIF and populating database...")
    for file in os.listdir(source_dir):
        full_path = os.path.join(source_dir, file)
        
        # Check if it's an image format we support
        if file.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.heif')):
            data = extractor.extract_exif_data(full_path)
            
            if data:
                # It has good data! Add to database.
                database.insert_photo(
                    db_path, 
                    data['filepath'], 
                    data['timestamp'], 
                    data['lat'], 
                    data['lon']
                )
                stats["processed"] += 1
            else:
                # It's an image, but missing GPS or Time data
                stats["no_metadata"] += 1
                shutil.copy2(full_path, os.path.join(manual_sort_dir, file))
        else:
            # It's a video or other file type
            stats["unsupported_format"] += 1
            # Check if it's a directory to avoid crashing on nested folders
            if os.path.isfile(full_path):
                shutil.copy2(full_path, os.path.join(manual_sort_dir, file))

    print(f"\n--- EXTRACTION SUMMARY ---")
    print(f"Successfully sent to clustering: {stats['processed']}")
    print(f"Sent to Manual Sorting (No GPS/Time): {stats['no_metadata']}")
    print(f"Sent to Manual Sorting (Videos/Other): {stats['unsupported_format']}")
    print(f"--------------------------\n")

    print("3. Fetching data for clustering...")
    df = database.get_data_for_clustering(db_path)
    
    if df.empty:
        print("No photos with valid GPS/Time data to process. Exiting.")
        return

    print("4. Normalizing data and running DBSCAN...")
    cluster_mappings = clusterer.assign_clusters(df, eps=eps, min_samples=min_samples)
    
    print("5. Updating database with cluster assignments...")
    database.update_clusters(db_path, cluster_mappings)
    
    print("6. Organizing files into destination folders...")
    final_df = database.get_clustered_data(db_path)
    organizer.create_folders_and_copy(final_df, dest_dir)
    
    print("Pipeline Complete!")

if __name__ == "__main__":
    SOURCE_DIRECTORY = "photo_folder"
    DESTINATION_DIRECTORY = "./organized_events"
    DATABASE_FILE = "photos.db"
    
    if not os.path.exists(SOURCE_DIRECTORY):
        os.makedirs(SOURCE_DIRECTORY)
        print(f"Please place test photos in '{SOURCE_DIRECTORY}' and run again.")
    else:
        run_pipeline(SOURCE_DIRECTORY, DESTINATION_DIRECTORY, DATABASE_FILE)