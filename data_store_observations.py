import pandas as pd
import param
import panel as pn

import bilan
import etp
import geo
import meteofrance

LECTURE_DONNEE = True
LECTURE_DONNEE_REF = True


# Météo-France API
METEOFRANCE_API = 'DPPaquetObs'

# Fréquence des données climatiques
METEOFRANCE_FREQUENCE = 'horaire'

# Identification de l'API Météo-France
DEFAULT_APPLICATION_ID = 'ZlFGb1VCNzdlQ3c5QmhSMU1IbE8xQTluOE0wYTpUS3l1YkcweGJmSTJrQlJVaGNiSkNHTXczdHNh'

DEFAULT_REF_STATION_LAT = 48.541356
DEFAULT_REF_STATION_LON = -1.615400
DEFAULT_NN_RAYON_KM = 35.


class DataStoreObservations(pn.viewable.Viewer):
    application_id = param.String(
        default=DEFAULT_APPLICATION_ID,
        doc="""Entrer l'Application ID de l'API Météo-France ici et cliquer ENTER..."""
    )
    lecture_liste_stations = param.Boolean(
        default=False,
        doc="""Cliquer pour lire la liste des stations au lieu de la télécharger..."""
    )
    ref_station_lat = param.Number(
        default=DEFAULT_REF_STATION_LAT,
        doc="""Entrer la latitude de la station de référence..."""
    )
    ref_station_lon = param.Number(
        default=DEFAULT_REF_STATION_LON,
        doc="""Entrer la longitude de la station de référence..."""
    )
    nn_rayon_km = param.Number(
        softbounds=(1., 100.), step=1., default=DEFAULT_NN_RAYON_KM,
        doc="""Entrer la distance maximale des stations à la référence..."""
    )
    
    def __init__(self, **params):
        super().__init__(**params)
    
        # Initialisation d'un client pour accéder à l'API Météo-France
        self._client = meteofrance.Client(METEOFRANCE_API)

        # Widgets
        self._application_id_widget = pn.widgets.TextInput.from_param(
            self.param.application_id)
        self._lecture_liste_stations_widget = pn.widgets.Checkbox.from_param(
            self.param.lecture_liste_stations)
        self._ref_station_lat_widget = pn.widgets.FloatInput.from_param(
            self.param.ref_station_lat)
        self._ref_station_lon_widget = pn.widgets.FloatInput.from_param(
            self.param.ref_station_lon)
        self._nn_rayon_km_widget = pn.widgets.EditableFloatSlider.from_param(
            self.param.nn_rayon_km)
        
        # Bindings de l'Application ID
        self._sortie_application_id = pn.bind(
            self._entrer_application_id, self.param.application_id)

        # Bouton et sortie pour la liste des stations
        self._bouton_liste_stations = pn.widgets.Button(
            name='Récupérer la liste des stations Météo-France',
            button_type='primary')
        self._sortie_liste_stations = pn.bind(
            self._recuperer_liste_stations, self._bouton_liste_stations)

        # Bouton et sortie pour la liste des stations les plus proches
        self._bouton_liste_stations_nn = pn.widgets.Button(
            name='Sélectionner les plus proches voisins',
            button_type='primary')
        self._sortie_liste_stations_nn = pn.bind(
            self._selectionner_plus_proches_voisins, self._bouton_liste_stations_nn)

        # Data
        self.df_liste_stations = None
        self.df_liste_stations_nn = None

    def _entrer_application_id(self, application_id):
        self._client.application_id = application_id

        return pn.pane.Str(f"Application ID entré: {application_id}")

    def _recuperer_liste_stations(self, event):
        sortie = "Cliquer pour récupérer la liste des stations..."
        if event:
            # Écraser la précédente liste
            self.df_liste_stations = None
            try:
                filepath_liste_stations = meteofrance.get_filepath_liste_stations(
                    self._client)
                if self._lecture_liste_stations_widget.value:
                    # Lecture de la liste des stations
                    self.df_liste_stations = pd.read_csv(
                        filepath_liste_stations,
                        index_col=self._client.id_station_label)
                    msg = pn.pane.Str("Liste des stations lue:")
                else:
                    # Demande de la liste des stations
                    section = meteofrance.SECTION_LISTE_STATIONS
                    response = meteofrance.demande(self._client, section)
                    self.df_liste_stations = meteofrance.response_text_to_frame(
                        self._client, response, index_col=self._client.id_station_label)
                    # Sauvegarde de la liste des stations
                    self.df_liste_stations.to_csv(filepath_liste_stations)
                    msg = pn.pane.Str("Liste des stations téléchargée:")
                    
                sortie = pn.Column(msg, pn.pane.DataFrame(self.df_liste_stations.head()))
            except Exception as exc:
                sortie = pn.pane.Str(f"Error: {exc}")
            
            return sortie
        else:
            return sortie

    def _selectionner_plus_proches_voisins(self, event):
        sortie = "Cliquer pour sélectionner les stations les plus proches..."
        if event:
            # Écraser la précédente liste
            self.df_liste_stations_nn = None
            try:
                ref_station_latlon = [self._ref_station_lat_widget.value,
                                      self._ref_station_lon_widget.value]
                self.df_liste_stations_nn = geo.selection_plus_proches_voisins(
                    self.df_liste_stations, ref_station_latlon, self._client.latlon_labels,
                    rayon_km=self._nn_rayon_km_widget.value)
                sortie = pn.Column(
                    pn.pane.Str("Stations les plus proches sélectionnées:"),
                    pn.pane.DataFrame(self.df_liste_stations_nn))
            except Exception as exc:
                sortie = pn.pane.Str(f"Error: {exc}")
            
            return sortie
        else:
            return sortie



    def __panel__(self):
        p = pn.Column(
            "# Données\n\n## Accès à l'API Météo-France",
            self._application_id_widget,
            self._sortie_application_id,
            "## Liste des stations",
            pn.Row(self._bouton_liste_stations, self._lecture_liste_stations_widget),
            self._sortie_liste_stations,
            "## Sélection des plus proches voisins",
            pn.Row(self._ref_station_lat_widget, self._ref_station_lon_widget),
            self._nn_rayon_km_widget,
            self._bouton_liste_stations_nn, 
            self._sortie_liste_stations_nn,
            "## Obtention des données météorologiques pour les stations voisines"
        )

        return p
