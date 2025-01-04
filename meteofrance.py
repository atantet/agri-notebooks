from io import StringIO
import json
import numpy as np
import pandas as pd
import requests

# Host
METEOFRANCE_HOST = 'https://public-api.meteofrance.fr'
METEOFRANCE_DOMAIN = 'public'
METEOFRANCE_VERSION = 'v1'
METEOFRANCE_DIR_LISTE_STATIONS = 'liste-stations'
METEOFRANCE_AVAILABLE_APIS = ['DPObs', 'DPPaquetObs', 'DPClim']
METEOFRANCE_GRANULARITE = {
    'DPObs': 'station',
    'DPPaquetObs': 'paquet',
    'DPClim': 'commande-station'
}
METEOFRANCE_FMT = 'csv'

# URL de la liste des stations
URL_LISTE_STATIONS = {
    api: (
        f"{METEOFRANCE_HOST}/{METEOFRANCE_DOMAIN}/{api}/"
        f"{METEOFRANCE_VERSION}/{METEOFRANCE_DIR_LISTE_STATIONS}")
    for api in METEOFRANCE_AVAILABLE_APIS
}

# URL de base des données horaires
URL_DONNEE = {
    api: (
        f"{METEOFRANCE_HOST}/{METEOFRANCE_DOMAIN}/{api}/"
        f"{METEOFRANCE_VERSION}/{METEOFRANCE_GRANULARITE[api]}")
    for api in METEOFRANCE_AVAILABLE_APIS
}

# Definitions pour accéder à l'API Météo-France via un token OAuth2
# unique application id : you can find this in the curl's command to generate jwt token 
# url to obtain acces token
TOKEN_URL = "https://portail-api.meteofrance.fr/token"

# Étiquettes de la latitude et de la longitude
LATLON_LABELS = {
    'DPObs': ['Latitude', 'Longitude'],
    'DPPaquetObs': ['Latitude', 'Longitude'],
    'DPClim': ['lat', 'lon']
}

STATION_NAME_LABEL = {
    'DPObs': 'Nom_usuel',
    'DPPaquetObs': 'Nom_usuel',
    'DPClim': 'nom'
}

class Client(object):
    def __init__(self, application_id, api):
        self.session = requests.Session()
        self.application_id = application_id
        self.api = api
        self.latlon_labels = LATLON_LABELS[self.api]
        self.station_name_label = STATION_NAME_LABEL[self.api]
        
    def request(self, method, url, **kwargs):
        # First request will always need to obtain a token first
        if 'Authorization' not in self.session.headers:
            self.obtain_token()
            
        # Optimistically attempt to dispatch reqest
        response = self.session.request(method, url, **kwargs)

        if self.token_has_expired(response):
            # We got an 'Access token expired' response => refresh token
            self.obtain_token()

            # Re-dispatch the request that previously failed
            response = self.session.request(method, url, **kwargs)

        response.raise_for_status()

        return response

    def token_has_expired(self, response):
        status = response.status_code
        content_type = response.headers['Content-Type']
        repJson = response.text

        if status == 401 and 'application/json' in content_type:
            repJson = response.text
            
            if 'Invalid JWT token' in repJson['description']:
                return True

        return False

    def obtain_token(self):
        # Obtain new token
        data = {'grant_type': 'client_credentials'}
        headers = {'Authorization': 'Basic ' + self.application_id}
        access_token_response = requests.post(
            TOKEN_URL, data=data, verify=False, allow_redirects=False, headers=headers)
        token = access_token_response.json()['access_token']

        # Update session with fresh token
        self.session.headers.update({'Authorization': 'Bearer %s' % token})

def response_text_to_frame(response, **kwargs):
    try:
        df = pd.read_csv(StringIO(response.text), sep=';', **kwargs)
    except TypeError:
        df = pd.read_json(StringIO(response.text)).set_index('id')
    
    return df

def demande_liste_stations(client, frequence=None, params=None):
    '''Demande de la liste des stations.'''
    url = URL_LISTE_STATIONS[client.api]

    if frequence is not None:
        url += f'/{frequence}'
    
    response = client.request('GET', url, params=params, verify=False)

    df = response_text_to_frame(response, index_col='Id_station')

    return df

def demande_donnee(client, params, frequence=None, verify=False):
    '''Demande des données d'observations.'''
    url = URL_DONNEE[client.api]

    if frequence is not None:
        url += f'/{frequence}'

    # Demande de la liste des stations
    response = client.request(
        'GET', url, verify=verify, params=params)

    return response

def compiler_donnee_des_stations_date(
    client, df_liste_stations, date, frequence=None):
    df = pd.DataFrame(dtype=float)
    for id_station in df_liste_stations.index:
        # Paramètres définissant la station, la date et le format des données
        params = {'id_station': id_station, 'date': date, 'format': METEOFRANCE_FMT}
        
        # Requête pour la station
        response = demande_donnee(client, params, frequence=frequence)

        # DataFrame de la station
        s_station = response_text_to_frame(response).iloc[0]
        df_station = s_station.to_frame(id_station).transpose()

        # Compilation
        df = pd.concat([df, df_station])
        
    return df

def compiler_donnee_des_departements(
    client, df_liste_stations, frequence=None):
    liste_id_departements = np.unique(
        [_ // 1000000 for _ in df_liste_stations.index])
    df_toutes = pd.DataFrame(dtype=float)
    for id_departement in liste_id_departements:
        # Paramètres définissant le département et le format des données
        params = {'id-departement': id_departement, 'format': METEOFRANCE_FMT}
    
        # Requête pour la station
        response = demande_donnee(client, params, frequence=frequence)

        # DataFrame pour le département indexé par identifiant station et par date
        time_col = 'validity_time'
        df_departement = response_text_to_frame(
            response, parse_dates=[time_col]).set_index(['geo_id_insee', time_col])
        
        # Compilation
        df_toutes = pd.concat([df_toutes, df_departement])

    # Sélection des stations de la liste
    df = df_toutes.loc[df_liste_stations.index]

    # Réindexer à partir des noms usuels
    id_stations_df = df.index.to_frame()['geo_id_insee']
    liste_noms_stations = [df_liste_stations.loc[_, client.station_name_label]
                           for _ in id_stations_df]
    df.insert(0, client.station_name_label, liste_noms_stations)
        
    return df