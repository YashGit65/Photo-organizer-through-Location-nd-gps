from datetime import datetime
from PIL import Image, ExifTags
import pillow_heif

pillow_heif.register_heif_opener()

def get_decimal_from_dms(dms, ref):
    if dms is None: return None
    try:
        if isinstance(dms, (float, int)):
            decimal = float(dms)
        elif isinstance(dms, (tuple, list)):
            def clean_val(val):
                if isinstance(val, (tuple, list)) and len(val) == 2:
                    return float(val[0]) / float(val[1]) if val[1] != 0 else 0.0
                if hasattr(val, 'numerator') and hasattr(val, 'denominator'):
                     return float(val.numerator) / float(val.denominator) if val.denominator != 0 else 0.0
                return float(val)

            d = clean_val(dms[0]) if len(dms) > 0 else 0.0
            m = clean_val(dms[1]) if len(dms) > 1 else 0.0
            s = clean_val(dms[2]) if len(dms) > 2 else 0.0
            decimal = d + (m / 60.0) + (s / 3600.0)
        else:
            decimal = float(dms)
            
        if ref and str(ref).strip("b'\"").upper() in ['S', 'W']:
            decimal = -decimal
        return decimal
    except Exception:
        return None

def extract_exif_data(image_path):
    """STRICT: Requires both Time and GPS for the clustering phase."""
    try:
        img = Image.open(image_path)
        dt_str, gps_info = None, None

        if hasattr(img, 'getexif'):
            exif = img.getexif()
            if exif:
                dt_str = exif.get(306) 
                try:
                    exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
                    if exif_ifd and 36867 in exif_ifd: dt_str = exif_ifd[36867]
                    gps_info = exif.get_ifd(ExifTags.IFD.GPSInfo)
                except AttributeError: pass
        
        if not dt_str and hasattr(img, '_getexif'):
            raw_exif = img._getexif()
            if raw_exif:
                exif_data = {ExifTags.TAGS.get(k, k): v for k, v in raw_exif.items()}
                dt_str = exif_data.get('DateTimeOriginal') or exif_data.get('DateTime')
                gps_info = exif_data.get('GPSInfo')

        if not dt_str: return None
        timestamp = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S').timestamp()

        if not gps_info or not isinstance(gps_info, dict) or 2 not in gps_info or 4 not in gps_info:
            return None

        lat = get_decimal_from_dms(gps_info.get(2), gps_info.get(1))
        lon = get_decimal_from_dms(gps_info.get(4), gps_info.get(3))

        if lat is None or lon is None: return None
        return {'filepath': image_path, 'timestamp': timestamp, 'lat': lat, 'lon': lon}
    except Exception:
        return None

def extract_partial_data(image_path):
    """FORGIVING: Grabs whatever it can find for the Rescue Phase."""
    try:
        img = Image.open(image_path)
        dt_str, gps_info = None, None

        if hasattr(img, 'getexif'):
            exif = img.getexif()
            if exif:
                dt_str = exif.get(306) 
                try:
                    exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
                    if exif_ifd and 36867 in exif_ifd: dt_str = exif_ifd[36867]
                    gps_info = exif.get_ifd(ExifTags.IFD.GPSInfo)
                except AttributeError: pass
        
        if not dt_str and hasattr(img, '_getexif'):
            raw_exif = img._getexif()
            if raw_exif:
                exif_data = {ExifTags.TAGS.get(k, k): v for k, v in raw_exif.items()}
                dt_str = exif_data.get('DateTimeOriginal') or exif_data.get('DateTime')
                gps_info = exif_data.get('GPSInfo')

        timestamp = None
        if dt_str:
            try: timestamp = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S').timestamp()
            except Exception: pass

        lat, lon = None, None
        if gps_info and isinstance(gps_info, dict) and 2 in gps_info and 4 in gps_info:
            lat = get_decimal_from_dms(gps_info.get(2), gps_info.get(1))
            lon = get_decimal_from_dms(gps_info.get(4), gps_info.get(3))

        if timestamp or (lat is not None and lon is not None):
            return {'filepath': image_path, 'timestamp': timestamp, 'lat': lat, 'lon': lon}
        return None
    except Exception:
        return None