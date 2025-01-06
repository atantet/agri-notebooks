import pandas as pd
from pathlib import Path
import meteofrance


METEOFRANCE_API = 'DPPaquetObs'
ID_DEPARTEMENTS = [35, 50]
NN_NOMBRE = 9
REF_STATION_NAME = 'La Petite Claye'
PERIODES = [
    ['2025-01-04T16:00:00Z', '2025-01-05T15:00:00Z'],
    ['2025-01-04T19:00:00Z', '2025-01-05T18:00:00Z'],
    ['2025-01-05T10:00:00Z', '2025-01-06T10:00:00Z']
]

client = meteofrance.Client('', METEOFRANCE_API)
index_col = [client.id_station_donnee_label, client.time_label]
index_col_ref = [client.time_label]

str_ref_station_name = REF_STATION_NAME.lower().replace(' ', '')

df_meteo = pd.DataFrame(dtype=float)
df_meteo_ref = pd.DataFrame(dtype=float)
for date_deb_periode_src, date_fin_periode_src in PERIODES:
    # Donnee des stations
    filepath_donnee_src = meteofrance.get_filepath_donnee_periode(
        client, date_deb_periode_src, date_fin_periode_src,
        id_departements=ID_DEPARTEMENTS, nn_nombre=NN_NOMBRE)
    
    df_periode = pd.read_csv(
        filepath_donnee_src, parse_dates=[client.time_label],
        index_col=index_col)

    df_meteo = pd.concat([df_meteo, df_periode])

    # Donnee de la référence
    filepath_donnee_ref_src = filepath_donnee_src.with_name(
        filepath_donnee_src.stem + '_' + str_ref_station_name +
        filepath_donnee_src.suffix)

    
    df_periode_ref = pd.read_csv(
        filepath_donnee_ref_src, parse_dates=[client.time_label],
        index_col=index_col_ref)

    df_meteo_ref = pd.concat([df_meteo_ref, df_periode_ref])
    
df_meteo_clean = df_meteo.reset_index().drop_duplicates(
    subset=index_col).set_index(index_col).sort_index()

# Donnee des stations
time = df_meteo_clean.index.to_frame()[client.time_label]
date_deb_periode_dst = time.min().isoformat().replace("+00:00", "Z")
date_fin_periode_dst = time.max().isoformat().replace("+00:00", "Z")
filepath_donnee_dst = meteofrance.get_filepath_donnee_periode(
    client, date_deb_periode_dst, date_fin_periode_dst,
    id_departements=ID_DEPARTEMENTS, nn_nombre=NN_NOMBRE)
df_meteo_clean.to_csv(filepath_donnee_dst)

# Donnee de la référence
df_meteo_ref_clean = df_meteo_ref.reset_index().drop_duplicates(
    subset=index_col_ref).set_index(index_col_ref).sort_index()

filepath_donnee_ref_dst = filepath_donnee_dst.with_name(
    filepath_donnee_dst.stem + '_' + str_ref_station_name +
    filepath_donnee_dst.suffix)
df_meteo_ref_clean.to_csv(filepath_donnee_ref_dst)
