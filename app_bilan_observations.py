import pandas as pd
import panel as pn
import param
pn.extension(
    'plotly', 'tabulator',
    throttled=True, defer_load=True, loading_indicator=True
)

from datastore_observations import DataStoreObservations
from viewer_bilan_observations import ViewerMeteoObservations, ViewerBilanObservations

class AppBilanObservations(pn.viewable.Viewer):
    datastore = param.ClassSelector(class_=DataStoreObservations)
    view_meteo = param.ClassSelector(class_=ViewerMeteoObservations)
    view_bilan = param.ClassSelector(class_=ViewerBilanObservations)

    titre = param.String(default=(
        "Bilan hydrique à partir des dernières 24 h "
        "d'observations Météo-France"))
    sidebar_width = param.Integer(default=500)

    def __init__(self, **params):
        super().__init__(**params)
        
        self._template = pn.template.MaterialTemplate(
            title=self.titre, sidebar_width=self.sidebar_width)
        self._template.sidebar.append(self.datastore)
        self._template.main.append(self.view_meteo)
        self._template.main.append(self.view_bilan)

    def servable(self):
        if pn.state.served:
            return self._template.servable()
        return self

    def __panel__(self):

        return pn.Column(self.datastore, self.view_meteo, self.view_bilan)


APPLICATION_ID = 'ZlFGb1VCNzdlQ3c5QmhSMU1IbE8xQTluOE0wYTpUS3l1YkcweGJmSTJrQlJVaGNiSkNHTXczdHNh'
REF_STATION_NAME = 'La Petite Claye'
REF_STATION_ALTITUDE = 50.
REF_STATION_LAT = 48.541356
REF_STATION_LON = -1.615400
NN_RAYON_KM = 35.
PERIODE = (pd.Timestamp("2025-01-19T21:00:00Z"),
           pd.Timestamp("2025-01-20T20:00:00Z"))


params = dict(
    lire_liste_stations=True,
    lire_donnee_liste_stations=True,
    lire_donnee_ref=True,
    application_id=APPLICATION_ID,
    ref_station_name=REF_STATION_NAME,
    ref_station_altitude=REF_STATION_ALTITUDE,
    ref_station_lat=REF_STATION_LAT,
    ref_station_lon=REF_STATION_LON,
    nn_rayon_km=NN_RAYON_KM,
    date_fin=PERIODE[1]
)
    
datastore = DataStoreObservations(**params)
# datastore = DataStoreObservations()
view_meteo = ViewerMeteoObservations(datastore=datastore)
view_bilan = ViewerBilanObservations(datastore=datastore)
AppBilanObservations(
    datastore=datastore,
    view_meteo=view_meteo,
    view_bilan=view_bilan).servable()
