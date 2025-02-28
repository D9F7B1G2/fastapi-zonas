from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Depends
from fastapi.security import APIKeyHeader
import xml.etree.ElementTree as ET
import shutil
import os

app = FastAPI()

# Configuración de API Key
API_KEY = "MI_CLAVE_SECRETA"  # Cambia esto por una clave más segura
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Clave API inválida")

# Ruta del archivo KML (Usamos la misma carpeta para evitar errores)
KML_FILE_PATH = "zonas_medellin.kml"

def extract_coordinates(kml_file):
    try:
        tree = ET.parse(kml_file)
        root = tree.getroot()
        
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        coordinates_data = []
        
        for placemark in root.findall(".//kml:Placemark", ns):
            name = placemark.find("kml:name", ns)
            name = name.text if name is not None else "Unnamed"
            
            coords_text = placemark.find(".//kml:coordinates", ns)
            if coords_text is not None:
                coordinates = [
                    tuple(map(float, point.split(',')[:2])) 
                    for point in coords_text.text.strip().split()
                ]
                coordinates_data.append({"name": name, "coordinates": coordinates})
        
        return coordinates_data
    except Exception as e:
        return []

# Inicialización de zonas
zones = extract_coordinates(KML_FILE_PATH)

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de Zonas de Medellín"}

@app.get("/zonas", dependencies=[Depends(verify_api_key)])
def get_zones():
    return zones

@app.get("/zona/{nombre}", dependencies=[Depends(verify_api_key)])
def get_zone(nombre: str):
    for zone in zones:
        if zone["name"].lower() == nombre.lower():
            return zone
    raise HTTPException(status_code=404, detail="Zona no encontrada")

@app.get("/buscar_zona/", dependencies=[Depends(verify_api_key)])
def buscar_zona(lat: float = Query(...), lon: float = Query(...)):
    for zona in zones:
        if (lon, lat) in zona["coordinates"]:
            return {"zona": zona["name"]}
    
    raise HTTPException(status_code=404, detail="Zona no encontrada")

@app.post("/upload-kml/", dependencies=[Depends(verify_api_key)])
def upload_kml(file: UploadFile = File(...)):
    try:
        with open(KML_FILE_PATH, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        global zones
        zones = extract_coordinates(KML_FILE_PATH)
        
        return {"message": "Archivo KML actualizado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")
