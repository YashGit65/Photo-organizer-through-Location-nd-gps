import os
import shutil
import zipfile
import database
import extractor
import clusterer
import organizer

# --- NEW: SPLASH SCREEN CLOSER ---
try:
    # This module is injected by PyInstaller. 
    # It will fail in normal VS Code, which is why we use try/except!
    import pyi_splash
    pyi_splash.update_text('UI Loaded ...')
    pyi_splash.close()
except ImportError:
    pass
# ---------------------------------


# time=1 and gps =7
def run_pipeline(source_dir, dest_dir, db_path="photos.db", eps=0.3, min_samples=1, time_weight=1.0, gps_weight=7.0):
    print("1. Initializing Database...")
    database.init_db(db_path)
    
    manual_sort_dir = os.path.join(dest_dir, "Needs_Manual_Sorting")
    if not os.path.exists(manual_sort_dir):
        os.makedirs(manual_sort_dir)
        
    stats = {"processed": 0, "no_metadata": 0, "unsupported_format": 0}

    print("1.5 Checking for ZIP files...")
    for file in os.listdir(source_dir):
        if file.lower().endswith('.zip'):
            zip_path = os.path.join(source_dir, file)
            print(f"Unzipping: {file}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(source_dir)
            os.remove(zip_path)

    print("2. Extracting EXIF and populating database...")
    
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            full_path = os.path.join(root, file)
            
            # 1. PROCESS IMAGES
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.heif')):
                data = extractor.extract_exif_data(full_path)
                
                if data:
                    database.insert_photo(db_path, data['filepath'], data['timestamp'], data['lat'], data['lon'])
                    stats["processed"] += 1
                else:
                    # Images missing data go to the root of Needs_Manual_Sorting
                    stats["no_metadata"] += 1
                    shutil.copy2(full_path, os.path.join(manual_sort_dir, file))
            
            # 2. PROCESS EVERYTHING ELSE (Videos, Documents, etc.)
            else:
                stats["unsupported_format"] += 1
                if os.path.isfile(full_path):
                    # Check if it's a video file
                    if file.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                        # Create a specific 'Videos' folder inside manual sorting
                        video_dir = os.path.join(manual_sort_dir, "Videos")
                        if not os.path.exists(video_dir):
                            os.makedirs(video_dir)
                            
                        shutil.copy2(full_path, os.path.join(video_dir, file))
                    else:
                        # Anything else (like .pdf or .txt) goes to the root
                        shutil.copy2(full_path, os.path.join(manual_sort_dir, file))

    print(f"\n--- EXTRACTION SUMMARY ---")
    print(f"Successfully sent to clustering: {stats['processed']}")
    print(f"Sent to Manual Sorting (No valid GPS/Time): {stats['no_metadata']}")
    print(f"Sent to Manual Sorting (Videos/Other): {stats['unsupported_format']}")
    print(f"--------------------------\n")

    print("3. Fetching data for clustering...")
    df = database.get_data_for_clustering(db_path)
    
    if df.empty:
        print("No photos with valid GPS/Time data to process. Exiting.")
        return

    print("4. Normalizing data and running DBSCAN...")
    cluster_mappings = clusterer.assign_clusters(
        df, 
        eps=eps, 
        min_samples=min_samples, 
        time_weight=time_weight, 
        gps_weight=gps_weight
    )
    
    print("5. Updating database with cluster assignments...")
    database.update_clusters(db_path, cluster_mappings)
    
    print("6. Organizing files into destination folders...")
    final_df = database.get_clustered_data(db_path)
    cluster_centroids = organizer.create_folders_and_copy(final_df, dest_dir)
    
    print("7. Rescuing photos with missing metadata...")
    organizer.rescue_leftovers(manual_sort_dir, cluster_centroids, max_hours=6, max_km=5)
    
    # --- ADD THIS NEW STEP ---
    print("8. Sweeping unrescued files into Miscellaneous...")
    organizer.cleanup_manual_folder(manual_sort_dir)
    
    print("\nPipeline Complete!")

if __name__ == "__main__":
    SOURCE_DIRECTORY = "./raw_photos"
    DESTINATION_DIRECTORY = "./Organized_events"
    DATABASE_FILE = "photos.db"
    INSTRUCTIONS_FILE = "Instructions.txt"
    
    # 1. Auto-generate the Instruction Manual if it doesn't exist
    if not os.path.exists(INSTRUCTIONS_FILE):
        with open(INSTRUCTIONS_FILE, "w", encoding="utf-8") as f:
            f.write("📸 WELCOME TO THE SMART PHOTO ORGANIZER 📸\n")
            f.write("============================================\n\n")
            
            f.write("HOW TO USE:\n")
            f.write("1. Since you are reading this, you already opened the Organizer app once! It just created a 'raw_photos' folder next to it.\n")
            f.write("2. Close the black Organizer window if it is still open.\n")
            f.write("3. Copy and paste all your messy photos or .zip files into the 'raw_photos' folder.\n")
            f.write("4. Double-click the Organizer application again.\n")
            f.write("5. Wait for the magic to happen!\n\n")
            
            f.write("WHERE DO MY PHOTOS GO?\n")
            f.write("- Successfully sorted photos will appear in 'organized_events'.\n")
            f.write("- Videos and photos missing GPS data will be safely placed in 'Needs_Manual_Sorting'.\n\n")
            
            f.write("⚠️ TROUBLESHOOTING: 'unknown_location' FOLDERS ⚠️\n")
            f.write("If your folders are being named 'unknown_location', Windows Defender Firewall is blocking the app from asking the internet for the street names.\n\n")
            f.write("How to give the app internet access:\n")
            f.write("  Step 1: Click your Windows Start button and type 'Firewall'.\n")
            f.write("  Step 2: Open 'Windows Defender Firewall'.\n")
            f.write("  Step 3: On the left side, click 'Allow an app or feature through Windows Defender Firewall'.\n")
            f.write("  Step 4: Click the 'Change settings' button at the top right (you might need admin permission).\n")
            f.write("  Step 5: Click 'Allow another app...' at the bottom right.\n")
            f.write("  Step 6: Click 'Browse', find your 'Organizer.exe' file, click 'Open', then 'Add'.\n")
            f.write("  Step 7: Check both the 'Private' and 'Public' boxes next to Organizer in the list.\n")
            f.write("  Step 8: Click OK, delete your 'unknown_location' folders, and run the app again!\n\n")
            
            f.write("Enjoy your clean gallery!\n")

    # 2. Check if the raw_photos folder exists
    if not os.path.exists(SOURCE_DIRECTORY):
        os.makedirs(SOURCE_DIRECTORY)
        print(f"\n[SETUP] I just created a folder named '{SOURCE_DIRECTORY}'.")
        print(f"-> Please read the '{INSTRUCTIONS_FILE}', put your photos inside the folder, and run me again!\n")
        
    # 3. Check if the folder is empty
    elif not os.listdir(SOURCE_DIRECTORY):
        print(f"\n[WAITING] The '{SOURCE_DIRECTORY}' folder is empty.")
        print(f"-> Please put all your photos (or a .zip file) inside that folder and run me again!\n")
        
    # 4. If it exists and has files, run the pipeline!
    else:
        run_pipeline(
            SOURCE_DIRECTORY, 
            DESTINATION_DIRECTORY, 
            DATABASE_FILE, 
            eps=0.3,             # Search radius
            min_samples=1,       # Minimum photos to make an event
            time_weight=1.0,     # How much to care about time gaps
            gps_weight=7.0       # How much to care about location changes
        )