### Processing cities.CSV

def process_citiesCSV(citiesDF, countries):
    from shapely.geometry import Point
    import geopandas as gpd
    print("----------------------------------------------------------------")
    print("START: PROCESSING cities.csv") 
    
    empty_entries = citiesDF.index[citiesDF.isnull().all(1)]                            # Drop empty entries
    DF = citiesDF.drop(citiesDF.index[empty_entries]).copy()
    print('[1/5] %d empty rows (from %d) found and dropped from DF' % (len(empty_entries), DF.count()[0]))
    
    DF['city'] = DF["city"].str.replace("√§", "ä", case=False)                          # Fix macintosh encoding errors
    DF['city'] = DF["city"].str.replace('√∂', 'ö', case=False)
    DF['city'] = DF["city"].str.replace("√º", "ü", case=False)
    DF['city'] = DF["city"].str.replace('√ü', 'ß', case=False)
    print("[2/5] Fixed Macintosh encoding errors")
    
    DF.iso2.fillna(DF.country.apply(lambda x: extract_iso('iso2', x)), inplace=True)    # Replace iso2 == NaN given country name
    print("[3/5] Filled missing iso2 entries")
    
    DF['iso3'] = DF.country.apply(lambda x: extract_iso('iso3', x))                     # Modify DF-columns to match demoDF
    DF = DF.rename(columns={"city": "City", "lng": "lon"})
    geoDF = DF[DF.iso2.isin(countries)]
    print("[4/5] Matched DF to demoDF (added iso3 column, renamed and dropped columns)")
    
    geoDF['coordinates'] = list(zip(geoDF.lon, geoDF.lat))                              # Convert DF to geoDF by setting lat/lon as geometry attributes
    geoDF['coordinates'] = geoDF.coordinates.apply(Point)
    geoDF = gpd.GeoDataFrame(geoDF, geometry='coordinates')
    geoDF.crs = {'init' :'epsg:4326'}
    print("[5/5] Converted DF to geoDF using lon/lat")
    
    print("END: PROCESSED cities.csv")
    print("----------------------------------------------------------------")
    
    return geoDF

def extract_iso(iso ,country):
    import pycountry
    if iso == 'iso2':
        try:
            iso2 = pycountry.countries.lookup(country).alpha_2
        except:
            iso2 = float('NaN')
            pass
        return iso2
    elif iso == 'iso3':
        try:
            iso3 = pycountry.countries.lookup(country).alpha_3
        except:
            iso3 = float('NaN')
            pass
        return iso3
    else:
        return None


### GeoDF Functions

def extract_polygonDF(country):
    import geopandas as gpd
    import json
    
    with open("DB.json") as text:
        DB = json.load(text)   
       
    ref = DB['countries'].get(country, "empty")
    if ref == "empty":
        print("No data available for {0}. Make sure your country input was formatted as iso2.".format(country))
        return None, None
    df_polygon = gpd.read_file(DB['sources'][ref]['db_path'])
    polyID = DB['sources'][ref]['db_id']    
    print("[1/5] Extracted polygonDF for {0}".format(country))
    
    return df_polygon, polyID
    
def ensure_WGS84projection(df_polygon):
    """
        Tests whether df_polygon has the proper projection.
        Changes projection to WGS84 if necessary.
    """
    if df_polygon.crs != {'init': 'epsg:4326'}:
        prev_proj = df_polygon.crs['init']
        df_polygon['geometry'] = df_polygon['geometry'].to_crs(epsg=4326)
        df_polygon.crs = {'init': 'epsg:4326'}
        print("[2/5] Switched projection from ", prev_proj, "to epsg:4326 (WGS84)")
    else:
        print("[2/5] Projection checked.")
    return df_polygon

def generate_pointsDF(geoDF, country):
    """
        Returns df_points for one specific country.
    """
    df_points = geoDF[geoDF.iso2 == country]
    df_points.crs = {'init': 'epsg:4326'}
    print("[3/5] Generated pointsDF for {0}".format(country))
    return df_points

def merge_pointsDF_polygonDF(df_points, df_polygon, polyID):
    """
        Merges df_points and df_polygon with a left spatial join (op='within').
        Reduces df_merge to relevant columns.
        * polyID: unique row-identifier of df_polygon to restore 'geography' information after spatial join.
    """
    import geopandas as gpd
    df_merge = gpd.sjoin(df_points, df_polygon[[polyID, "geometry"]], op='within', how='left')  # Perform left spatial join
    df_merge = df_merge.merge(df_polygon[[polyID, "geometry"]], on=polyID)                      # Add 'geometry' to DF again and keep relevant columns
    df_merge = df_merge[['City', 'lon', 'lat', 'iso2', 'iso3', 'country', 'geometry']]
    df_merge = gpd.GeoDataFrame(df_merge, geometry='geometry')                                  # Ensure df_merge is geo-DF
    print('[4/5] {0} entries from {1} lost in spatial join ({2}%)'.format(df_points.count()[0] - df_merge.count()[0],df_points.count()[0],100*((df_points.count()[0] - df_merge.count()[0])/df_points.count()[0])))
    return df_merge

def convert_to_GeoJSON(df_merge, country):
    """
        Convert df_merge to GeoJSON.
        Returns one GeoJSON if DF has only one geometry type.
        Returns two GeoJSONs that have to be merged in terminal if DF has multiply geometry types (fiona cannot process that yet).
    """
    import os
    path = "./GeoJSON/"+country+"/"
    os.makedirs(path, exist_ok=True)
    
    df_copy = df_merge.copy()
    if len(df_copy.geom_type.unique()) != 1:
        df_poly = df_copy[df_copy.geom_type == 'Polygon']
        df_multi = df_copy[df_copy.geom_type == 'MultiPolygon']    
        df_poly.to_file(path+country+"_poly.geojson", driver="GeoJSON")
        df_multi.to_file(path+country+"_multi.geojson", driver="GeoJSON")
        print("""[5/5] {0}_poly.geojson and {0}_multi.geojson were generated.
        \nRun \"geojson-merge {0}_poly.geojson {0}_multi.geojson > {0}.geojson\" in terminal to generate {0}.geojson.
        \n(You may have to run \"npm install @mapbox/geojson-normalize\" first.)""".format(country))
    else: 
        df_merge.to_file(path+country+".geojson", driver="GeoJSON")
        print('[5/5] {0}.geojson was generated.'.format(country))
    return
        
def generate_GeoJSON(country, geoDF):
    print("----------------------------------------------------------------")
    print("START: GENERATE GEOJSON FOR", country)
    df_polygon, polyID = extract_polygonDF(country)                     # Generate polyDF for given country
    if df_polygon is not None:  
        df_polygon = ensure_WGS84projection(df_polygon)                     # Convert geo-DF from epsg:3347 to epsg:4326
        df_points = generate_pointsDF(geoDF, country)                       # Generate df_points
        df_merge = merge_pointsDF_polygonDF(df_points, df_polygon, polyID)  # Merge DFs
        convert_to_GeoJSON(df_merge, country)                               # Convert DF to GeoJSON
        print("END: GEOJSON FOR", country, "GENERATED")
    print("----------------------------------------------------------------")
    return None
