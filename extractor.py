from datetime import datetime
from PIL import Image, ExifTags
import pillow_heif

# Teaches Pillow how to open and read .heic / .heif files
pillow_heif.register_heif_opener()

def get_decimal_from_dms(dms, ref):
    """A bulletproof converter for all the weird ways phones save GPS."""
    if dms is None:
        return None
        
    try:
        # Case 1: The phone already did the math and saved a single decimal
        if isinstance(dms, (float, int)):
            decimal = float(dms)
            
        # Case 2: It's a tuple or list (The standard format)
        elif isinstance(dms, (tuple, list)):
            
            # Helper to handle nested fractions like ((28, 1), (30, 1))
            def clean_val(val):
                if isinstance(val, (tuple, list)) and len(val) == 2:
                    return float(val[0]) / float(val[1]) if val[1] != 0 else 0.0
                # Handle Pillow IFDRational objects safely
                if hasattr(val, 'numerator') and hasattr(val, 'denominator'):
                     return float(val.numerator) / float(val.denominator) if val.denominator != 0 else 0.0
                return float(val)

            d = clean_val(dms[0]) if len(dms) > 0 else 0.0
            m = clean_val(dms[1]) if len(dms) > 1 else 0.0
            s = clean_val(dms[2]) if len(dms) > 2 else 0.0
            
            decimal = d + (m / 60.0) + (s / 3600.0)
            
        else:
            # Fallback for weird Pillow objects
            decimal = float(dms)
            
        # Apply N/S/E/W reference (make negative if South or West)
        # We use str(ref) in case the phone saved the reference as bytes like b'N'
        if ref and str(ref).strip("b'\"").upper() in ['S', 'W']:
            decimal = -decimal
            
        return decimal
        
    except Exception as e:
        print(f"Warning: Could not parse this specific GPS format {dms}: {e}")
        return None

def extract_exif_data(image_path):
    """Extracts timestamp, latitude, and longitude from JPEGs and HEICs."""
    try:
        img = Image.open(image_path)
        
        dt_str = None
        gps_info = None

        # --- EXIF EXTRACTION LOGIC ---
        # Try modern getexif() (Works for HEIC and modern JPEGs)
        if hasattr(img, 'getexif'):
            exif = img.getexif()
            if exif:
                # Get standard DateTime as fallback
                dt_str = exif.get(306) 
                
                # Dig into the specific Image File Directories (IFDs)
                try:
                    exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
                    if exif_ifd and 36867 in exif_ifd: # 36867 is DateTimeOriginal
                        dt_str = exif_ifd[36867]
                        
                    gps_info = exif.get_ifd(ExifTags.IFD.GPSInfo)
                except AttributeError:
                    pass
        
        # Fallback to old _getexif() (For older JPEGs if the above fails)
        if not dt_str and hasattr(img, '_getexif'):
            raw_exif = img._getexif()
            if raw_exif:
                exif_data = {ExifTags.TAGS.get(k, k): v for k, v in raw_exif.items()}
                dt_str = exif_data.get('DateTimeOriginal') or exif_data.get('DateTime')
                gps_info = exif_data.get('GPSInfo')

        # --- PARSING THE EXTRACTED DATA ---
        # --- PARSING THE EXTRACTED DATA ---
       # --- PARSING THE EXTRACTED DATA ---
        if not dt_str:
            return None 
            
        timestamp = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S').timestamp()

        # STRICT MODE: If GPS is missing or invalid, reject the photo entirely
        if not gps_info or not isinstance(gps_info, dict) or 2 not in gps_info or 4 not in gps_info:
            return None

        lat = get_decimal_from_dms(gps_info.get(2), gps_info.get(1))
        lon = get_decimal_from_dms(gps_info.get(4), gps_info.get(3))

        # STRICT MODE: If our decimal math failed, reject the photo
        if lat is None or lon is None:
            return None

        # Only return data if we have a perfect timestamp AND perfect GPS
        return {'filepath': image_path, 'timestamp': timestamp, 'lat': lat, 'lon': lon}
    
    except Exception as e:
        print(f"Warning: Could not read EXIF for {image_path} ({e})")
        return None
   