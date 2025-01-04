from io import StringIO
import json
import numpy as np
import pandas as pd
import requests

# Host
METEOFRANCE_HOST = 'https://public-api.meteofrance.fr'
METEOFRANCE_DOMAIN = 'public'
METEOFRANCE_VERSION = 'v1'
METEOFRANCE_FREQUENCE = 'horaire'
METEOFRANCE_DIR_LISTE_STATIONS = 'liste-stations'
METEOFRANCE_API_STATION = ''
METEOFRANCE_GRANULARITE_STATION = 'station'
METEOFRANCE_API_PAQUET = 'DPPaquetObs'
METEOFRANCE_GRANULARITE_PAQUET = 'paquet'
METEOFRANCE_FMT = 'csv'

# URL de la liste des stations
URL_LISTE_STATIONS_STATION = (f'{METEOFRANCE_HOST}/{METEOFRANCE_DOMAIN}/{METEOFRANCE_API_STATION}/'
                              f'{METEOFRANCE_VERSION}/{METEOFRANCE_DIR_LISTE_STATIONS}')
URL_LISTE_STATIONS_PAQUET = (f'{METEOFRANCE_HOST}/{METEOFRANCE_DOMAIN}/{METEOFRANCE_API_PAQUET}/'
                             f'{METEOFRANCE_VERSION}/{METEOFRANCE_DIR_LISTE_STATIONS}')

# URL de base des données horaires
URL_DONNEE_STATION = (f'{METEOFRANCE_HOST}/{METEOFRANCE_DOMAIN}/{METEOFRANCE_API_STATION}/'
                      f'{METEOFRANCE_VERSION}/{METEOFRANCE_GRANULARITE_STATION}/{METEOFRANCE_FREQUENCE}')
URL_DONNEE_PAQUET = (f'{METEOFRANCE_HOST}/{METEOFRANCE_DOMAIN}/{METEOFRANCE_API_PAQUET}/'
                     f'{METEOFRANCE_VERSION}/{METEOFRANCE_GRANULARITE_PAQUET}/{METEOFRANCE_FREQUENCE}')

# Definitions pour accéder à l'API Météo-France via un token OAuth2
# unique application id : you can find this in the curl's command to generate jwt token 
# url to obtain acces token
TOKEN_URL = "https://portail-api.meteofrance.fr/token"

# Étiquettes de la latitude et de la longitude
LATLON_LABELS = ['Latitude', 'Longitude']

class Client(object):
    def __init__(self, application_id):
        self.session = requests.Session()
        self.application_id = application_id
        
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

def response_text_to_frame(response, **read_csv_kwargs):
    return pd.read_csv(StringIO(response.text), sep=';', **read_csv_kwargs)

def demande_liste_stations(client):
    '''Demande de la liste des stations.'''
    # Choix de l'api
    url_liste_stations = URL_LISTE_STATIONS_PAQUET

    response_liste_stations = client.request('GET', url_liste_stations, verify=False)
    df = response_text_to_frame(response_liste_stations, index_col='Id_station')

    return df

def demande_donnee_station_date(client, id_station, date, verify=False):
    '''Demande des données horaires pour une station et une date données.'''
    # Paramètres définissant la station, la date et le format des données
    params = {'id_station': id_station, 'date': date, 'format': METEOFRANCE_FMT}

    # Demande de la liste des stations
    response = client.request(
        'GET', URL_DONNEE_STATION, verify=verify, params=params)

    return response

def compiler_donnee_des_stations_date(client, df_liste_stations, date):
    df = pd.DataFrame(dtype=float)
    for id_station in df_liste_stations.index:
        # Requête pour la station
        response = demande_donnee_station_date(client, id_station, date)

        # DataFrame de la station
        s_station = response_text_to_frame(response).iloc[0]
        df_station = s_station.to_frame(id_station).transpose()

        # Compilation
        df = pd.concat([df, df_station])
        
    return df

def demande_donnee_departement(client, id_departement, verify=False):
    '''Demande des données empaquetées pour un département.'''
    # Paramètres définissant le département et le format des données
    params = {'id-departement': id_departement, 'format': METEOFRANCE_FMT}

    # Demande de la liste des stations
    response = client.request(
        'GET', URL_DONNEE_PAQUET, verify=verify, params=params)

    return response

def compiler_donnee_des_departements(client, df_liste_stations):
    liste_id_departements = np.unique(
        [_ // 1000000 for _ in df_liste_stations.index])
    df_toutes = pd.DataFrame(dtype=float)
    for id_departement in liste_id_departements:
        # Requête pour la station
        response = demande_donnee_departement(client, id_departement)

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
    liste_noms_stations = [df_liste_stations.loc[_, 'Nom_usuel']
                           for _ in id_stations_df]
    df.insert(0, 'Nom_usuel', liste_noms_stations)
        
    return df