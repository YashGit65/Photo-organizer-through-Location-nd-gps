import pillow_heif
from PIL import Image, ExifTags

# Teach Pillow to read HEIC
pillow_heif.register_heif_opener()

def debug_photo(image_path):
    print(f"\n=== X-RAYING PHOTO: {image_path} ===")
    
    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f"CRITICAL ERROR: Pillow cannot even open this file. ({e})")
        return

    # Check for modern getexif()
    if not hasattr(img, 'getexif'):
        print("CRITICAL ERROR: This image object doesn't support getexif().")
        return

    exif = img.getexif()
    if not exif:
        print("RESULT: Image opened, but absolutely zero EXIF data was found.")
        return

    # 1. Print General Tags
    print("\n--- 1. GENERAL EXIF TAGS ---")
    for k, v in exif.items():
        if k in ExifTags.TAGS:
            print(f"[{k}] {ExifTags.TAGS[k]}: {v}")

    # 2. Print EXIF IFD (Usually contains DateTimeOriginal)
    print("\n--- 2. EXIF IFD (Time Data) ---")
    try:
        exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
        if not exif_ifd:
            print("No EXIF IFD directory found.")
        else:
            for k, v in exif_ifd.items():
                if k in ExifTags.TAGS:
                    print(f"[{k}] {ExifTags.TAGS[k]}: {v}")
    except Exception as e:
         print(f"Error reading EXIF IFD: {e}")

    # 3. Print GPS IFD (Contains Coordinates)
    print("\n--- 3. GPS IFD (Location Data) ---")
    try:
        gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
        if not gps_ifd:
            print("No GPS IFD directory found. (Location is stripped!)")
        else:
            for k, v in gps_ifd.items():
                # We use GPSTAGS here to translate the specific GPS keys
                if k in ExifTags.GPSTAGS:
                    print(f"[{k}] {ExifTags.GPSTAGS[k]}: {v}")
                else:
                    print(f"[Unknown GPS Key {k}]: {v}")
    except Exception as e:
        print(f"Error reading GPS IFD: {e}")

if __name__ == "__main__":
    # ---> PUT THE PATH TO A PROBLEM PHOTO HERE <---
    # Pick ONE photo from your 'Needs_Manual_Sorting' folder that you KNOW has location data
    test_image = "organized_events/Needs_Manual_Sorting/2026_02_28_16_10_30_IMG_6068.JPG" 
    
    debug_photo(test_image)