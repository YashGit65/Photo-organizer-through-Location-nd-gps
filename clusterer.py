from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN

def assign_clusters(df, eps=0.2, min_samples=3, time_weight=3, gps_weight=3.0):
    """
    Strictly runs DBSCAN. Requires valid GPS and timestamps.
    Normalizes features and applies custom weights.
    """
    if df.empty:
        return []

    features = df[['timestamp', 'lat', 'lon']]
    
    # Normalize features
    scaler = StandardScaler()
    normalized_features = scaler.fit_transform(features)

    # Apply Custom Weights (Prioritize GPS)
    normalized_features[:, 0] *= time_weight  # timestamp
    normalized_features[:, 1] *= gps_weight   # lat
    normalized_features[:, 2] *= gps_weight   # lon

    # Run DBSCAN
    dbscan = DBSCAN(eps=eps, min_samples=min_samples)
    cluster_labels = dbscan.fit_predict(normalized_features)

    # Map the results back to the database IDs
    cluster_mappings = []
    for index, cluster_id in enumerate(cluster_labels):
        db_id = df.iloc[index]['id']
        cluster_mappings.append((int(cluster_id), int(db_id)))
        
    return cluster_mappings