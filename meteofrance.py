from io import StringIO
import json
import numpy as np
import pandas as pd
from pathlib import Path
import requests
import warnings

# Host
HOST = 'https://public-api.meteofrance.fr'
DOMAIN = 'public'
VERSION = 'v1'
SECTION_LISTE_STATIONS = 'liste-stations'
AVAILABLE_APIS = ['DPObs', 'DPPaquetObs', 'DPClim']
FMT = 'csv'

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

# Étiquette des noms des stations
STATION_NAME_LABEL = {
    'DPObs': 'Nom_usuel',
    'DPPaquetObs': 'Nom_usuel',
    'DPClim': 'nom'
}

# Étiquette des identifiants des stations
ID_STATION_LABEL = {
    'DPObs': 'Id_station',
    'DPPaquetObs': 'Id_station',
    'DPClim': 'id'
}

# Étiquette du drapeau d'ouverture des stations
OUVERT_STATION_LABEL = {
    'DPObs': None,
    'DPPaquetObs': None,
    'DPClim': 'posteOuvert'
}

# Étiquette du drapeau du caractère public des stations
PUBLIC_STATION_LABEL = {
    'DPObs': None,
    'DPPaquetObs': None,
    'DPClim': 'postePublic'
}

# Étiquette du type de station
TYPE_STATION_LABEL = {
    'DPObs': None,
    'DPPaquetObs': None,
    'DPClim': 'typePoste'
}


# Dossier des données
DATA_DIR = Path('data')

class Client(object):
    def __init__(self, application_id, api):
        self.session = requests.Session()
        self.application_id = application_id
        if api not in AVAILABLE_APIS:
            raise ValueError(f"Choix invalide: {api}. "
                             f"Les choix possibles sont: {AVAILABLE_APIS}")
        self.api = api
        self.latlon_labels = LATLON_LABELS[self.api]
        self.station_name_label = STATION_NAME_LABEL[self.api]
        self.id_station_label = ID_STATION_LABEL[self.api]
        self.ouvert_station_label = OUVERT_STATION_LABEL[self.api]
        self.public_station_label = PUBLIC_STATION_LABEL[self.api]
        self.type_station_label = TYPE_STATION_LABEL[self.api]
        
    def request(self, method, url, **kwargs):
        # First request will always need to obtain a token first
        if 'Authorization' not in self.session.headers:
            self.obtain_token()
            
        # Optimistically attempt to dispatch reqest
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = self.session.request(method, url, **kwargs)

        if self.token_has_expired(response):
            # We got an 'Access token expired' response => refresh token
            self.obtain_token()

            # Re-dispatch the request that previously failed
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
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
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            access_token_response = requests.post(
                TOKEN_URL, data=data, verify=False, allow_redirects=False, headers=headers)
        token = access_token_response.json()['access_token']

        # Update session with fresh token
        self.session.headers.update({'Authorization': 'Bearer %s' % token})

def response_text_to_frame(client, response, **kwargs):
    try:
        df = pd.read_csv(StringIO(response.text), sep=';', **kwargs)
    except TypeError:
        df = pd.read_json(StringIO(response.text)).set_index(
            client.id_station_label)
    
    return df

def demande(client, section, params=None, frequence=None, verify=False):
    '''Demande de la liste des stations.'''
    url = f"{HOST}/{DOMAIN}/{client.api}/{VERSION}/{section}"

    if frequence is not None:
        url += f'/{frequence}'
    
    response = client.request(
        'GET', url, params=params, verify=verify)

    return response

def get_filepath_liste_stations(client, departement):
    filename = f'liste_stations_{client.api}_{departement:d}.csv'
    parent = Path(DATA_DIR, client.api)
    parent.mkdir(parents=True, exist_ok=True)
    filepath = Path(parent, filename)

    return filepath

def compiler_donnee_des_stations_date(
    client, df_liste_stations, date, frequence=None):
    df = pd.DataFrame(dtype=float)
    for id_station in df_liste_stations.index:
        # Paramètres définissant la station, la date et le format des données
        params = {'id_station': id_station, 'date': date, 'format': FMT}
        
        # Requête pour la station
        section = 'station'
        response = demande(client, section, params=params, frequence=frequence)

        # DataFrame de la station
        s_station = response_text_to_frame(response).iloc[0]
        df_station = s_station.to_frame(id_station).transpose()

        # Compilation
        df = pd.concat([df, df_station])
        
    return df

def compiler_commandes_des_stations_periode(
    client, df_liste_stations, date_deb_periode, date_fin_periode,
    frequence=None):
    params = {
        'date-deb-periode': date_deb_periode,
        'date-fin-periode': date_fin_periode
    }
    id_commandes = {}
    for id_station in df_liste_stations.index:
        # Paramètres définissant la station, la date et le format des données
        params['id-station'] = id_station,
        
        # Requête pour la station
        section = 'commande-station'
        response = demande(client, section, params=params, frequence=frequence)

        # DataFrame de la station
        id_commandes[id_station] = (
            response.json()['elaboreProduitAvecDemandeResponse']['return'])

    return id_commandes

def compiler_donnee_des_stations_depuis_commandes(
    client, df_liste_stations, date_deb_periode, date_fin_periode,
    frequence=None):
    id_commandes = compiler_commandes_des_stations_periode(
        client, df_liste_stations, date_deb_periode, date_fin_periode,
        frequence=frequence)

    for id_station, id_cmde in id_commandes.items():
        pass
        

def compiler_donnee_des_departements(
    client, df_liste_stations, frequence=None):
    liste_id_departements = np.unique(
        [_ // 1000000 for _ in df_liste_stations.index])
    df_toutes = pd.DataFrame(dtype=float)
    for id_dep in liste_id_departements:
        # Paramètres définissant le département et le format des données
        params = {'id-departement': id_dep, 'format': FMT}
    
        # Requête pour la station
        section = 'paquet'
        response = demande(client, section, params=params, frequence=frequence)

        # DataFrame pour le département indexé par identifiant station et par date
        time_col = 'validity_time'
        df_departement = response_text_to_frame(
            client, response, parse_dates=[time_col]).set_index(
            ['geo_id_insee', time_col])
        
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

def filtrer_stations_valides(client, df_brute):
    validite = (df_brute[client.ouvert_station_label] &
                df_brute[client.public_station_label] &
                (df_brute[client.type_station_label] != 5))
    
    df = df_brute.loc[validite].drop(
        [client.ouvert_station_label, client.public_station_label], axis=1)

    return df