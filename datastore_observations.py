import pandas as pd
import param
import panel as pn
import traceback

import bilan
import etp
import geo
import meteofrance

# Météo-France API
METEOFRANCE_API = 'DPPaquetObs'

# Fréquence des données climatiques
METEOFRANCE_FREQUENCE = 'horaire'

# Variables utilisées pour le calcul de l'ETP et du bilan hydrique 
VARIABLES_POUR_CALCULS = dict(
    **etp.VARIABLES_CALCUL_ETP,
    **bilan.VARIABLES_CALCUL_BILAN)
VARIABLES_POUR_CALCULS_SANS_ETP = VARIABLES_POUR_CALCULS.copy()
del VARIABLES_POUR_CALCULS_SANS_ETP['etp']

class DataStoreObservations(pn.viewable.Viewer):
    application_id = param.String(
        doc="""Entrer l'Application ID de l'API Météo-France ici et cliquer ENTER..."""
    )
    lire_liste_stations = param.Boolean(
        default=False,
        doc="""Cliquer pour lire la liste des stations au lieu de la télécharger..."""
    )
    ref_station_name = param.String(
        doc="""Entrer le nom de la station de référence et cliquer ENTER..."""
    )
    ref_station_altitude = param.Number(
        bounds=(0., None),
        doc="""Entrer l'altitude de la station de référence..."""
    )
    ref_station_lat = param.Number(
        bounds=(-90, 90.),
        doc="""Entrer la latitude de la station de référence..."""
    )
    ref_station_lon = param.Number(
        bounds=(-180., 180.),
        doc="""Entrer la longitude de la station de référence..."""
    )
    nn_rayon_km = param.Number(
        softbounds=(1., 100.), bounds=(0., 1000.), step=1.,
        doc="""Entrer la distance maximale des stations à la référence..."""
    )
    lire_donnee_liste_stations = param.Boolean(
        default=False,
        doc="""Cliquer pour lire la donnée météo pour la liste des stations au lieu de la télécharger..."""
    )
    date_deb = param.String(
        doc="""Entrer la date de début de la donnée météo au et cliquer ENTER..."""
    )
    date_fin = param.String(
        doc="""Entrer la date de fin de la donnée météo et cliquer ENTER..."""
    )
    lire_donnee_ref = param.Boolean(
        default=False,
        doc="""Cliquer pour lire la donnée météo pour la station de référence au lieu de la télécharger..."""
    )
    
    def __init__(self, **params):
        super().__init__(**params)
    
        # Initialisation d'un client pour accéder à l'API Météo-France
        self._client = meteofrance.Client(METEOFRANCE_API)
        
        # Donnée
        self.tab_liste_stations = pn.widgets.Tabulator(
            pd.DataFrame(), disabled=True, pagination="local")
        self.tab_liste_stations_nn = pn.widgets.Tabulator(
            pd.DataFrame(), disabled=True, pagination="local")
        self.tab_meteo = pn.widgets.Tabulator(
            pd.DataFrame(), disabled=True, pagination="local")
        self.tab_meteo_ref_heure_si = pn.widgets.Tabulator(
            pd.DataFrame(), disabled=True, pagination="local",
            layout='fit_data_table')
        self.tab_meteo_ref_si = pn.widgets.Tabulator(
            pd.DataFrame(), disabled=True, pagination="local",
            layout='fit_data_table')

        # Widget pour lire les jeux de donnée ou non
        self._lire_liste_stations_widget = pn.widgets.Checkbox.from_param(
            self.param.lire_liste_stations,
            name="Lire la liste des stations")
        self._lire_donnee_liste_stations_widget = pn.widgets.Checkbox.from_param(
            self.param.lire_donnee_liste_stations,
            name="Lire la donnée pour la liste des stations")
        self._lire_donnee_ref_widget = pn.widgets.Checkbox.from_param(
            self.param.lire_donnee_ref,
            name="Lire la donnée pour la station de référence")

        # Widgets pour l'Application ID
        self._application_id_widget = pn.widgets.TextInput.from_param(
            self.param.application_id, name="Application ID Météo-France")
        self._sortie_entrer_application_id = pn.bind(
            self._entrer_application_id, self.param.application_id)

        # Widgets pour la liste des stations
        self._sortie_recuperer_liste_stations = pn.bind(
            self._montrer_liste_stations_widgets, self.param.application_id)
        self._bouton_liste_stations = pn.widgets.Button(
            name='Récupérer la liste des stations Météo-France',
            button_type='primary')
        self._sortie_liste_stations = pn.bind(
            self._recuperer_liste_stations, self._bouton_liste_stations)
        self._sortie_selectionner_plus_proches_voisins = pn.bind(
            self._montrer_plus_proches_voisins_widgets, self.tab_liste_stations)
        
        # Widgets pour la station de référence
        self._ref_station_name_widget = pn.widgets.TextInput.from_param(
            self.param.ref_station_name,
            name="Nom de la station de référence")
        self._ref_station_altitude_widget = pn.widgets.FloatInput.from_param(
            self.param.ref_station_altitude,
            name="Altitude de la station de référence")
        self._ref_station_lat_widget = pn.widgets.FloatInput.from_param(
            self.param.ref_station_lat,
            name="Latitude de la station de référence")
        self._ref_station_lon_widget = pn.widgets.FloatInput.from_param(
            self.param.ref_station_lon,
            name="Longitude de la station de référence")

        # Widgets pour les plus proches voisins
        self._nn_rayon_km_widget = pn.widgets.EditableFloatSlider.from_param(
            self.param.nn_rayon_km,
            name="Distance maximale des stations à la référence")
        self._bouton_liste_stations_nn = pn.widgets.Button(
            name='Sélectionner les plus proches voisins',
            button_type='primary')
        self._sortie_liste_stations_nn = pn.bind(
            self._selectionner_plus_proches_voisins, self._bouton_liste_stations_nn)
        self._sortie_recuperer_donnee_liste_stations = pn.bind(
            self._montrer_donnee_liste_stations_widgets, self.tab_liste_stations_nn)

        # Widgets pour la donnée météo pour la liste des stations
        placeholder = "YYYY-mm-ddTHH:MM:SSZ"
        self._date_deb_widget = pn.widgets.TextInput.from_param(
            self.param.date_deb, placeholder=placeholder,
            name="Date de début de la donnée météo")
        self._date_fin_widget = pn.widgets.TextInput.from_param(
            self.param.date_fin, placeholder=placeholder,
            name="Date de fin de la donnée météo")
        self._bouton_donnee_liste_stations = pn.widgets.Button(
            name='Récupérer la donnee météo pour la liste des stations',
            button_type='primary')
        self._sortie_donnee_liste_stations = pn.bind(
            self._recuperer_donnee_liste_stations, self._bouton_donnee_liste_stations)
        self._sortie_montrer_dates_widgets = pn.bind(
            self._montrer_dates_widgets,
            self.tab_liste_stations_nn,
            self._lire_donnee_ref_widget, self.tab_meteo)

        # Widgets pour la donnée météo pour la station de référence
        self._sortie_recuperer_donnee_ref = pn.bind(
            self._montrer_donnee_ref_widgets,
            self.tab_meteo, self.tab_liste_stations_nn,
            self._lire_donnee_ref_widget)
        self._bouton_donnee_ref = pn.widgets.Button(
            name='Récupérer la donnee météo pour la station de référence',
            button_type='primary')
        self._sortie_donnee_ref = pn.bind(
            self._recuperer_donnee_ref, self._bouton_donnee_ref)

    def _sortie_application_id(self):
        return pn.Column(
            "## Accès à l'API Météo-France",
            self._application_id_widget,
            self._sortie_entrer_application_id
        )
        
    def _entrer_application_id(self, application_id):
        sortie = "Application ID vide. Recommencer."
        if application_id:
            self._client.application_id = application_id
            sortie = pn.pane.Markdown(f"Application ID entré: {application_id}")
        return sortie

    def _montrer_liste_stations_widgets(self, application_id):
        sortie = None
        if application_id:
            sortie = pn.Column(
                "## Liste des stations",
                self._bouton_liste_stations,
                self._sortie_liste_stations
            )
        return sortie

    def _recuperer_liste_stations(self, event):
        sortie = pn.pane.Markdown("Cliquer pour récupérer la liste des stations...")
        if event:
            # Écraser la liste des stations précédente
            self.tab_liste_stations.value = pd.DataFrame()
            try:
                filepath = meteofrance.get_filepath_liste_stations(
                    self._client)
                if self._lire_liste_stations_widget.value:
                    # Lecture de la liste des stations
                    self.tab_liste_stations.value = pd.read_csv(
                        filepath, index_col=self._client.id_station_label)
                    msg = pn.pane.Markdown("Liste des stations lue:")
                else:
                    # Demande de la liste des stations
                    section = meteofrance.SECTION_LISTE_STATIONS
                    response = meteofrance.demande(self._client, section)
                    self.tab_liste_stations.value = meteofrance.response_text_to_frame(
                        self._client, response, index_col=self._client.id_station_label)
                    # Sauvegarde de la liste des stations
                    self.tab_liste_stations.value.to_csv(filepath)
                    msg = pn.pane.Markdown("Liste des stations téléchargée:")
                    
                dst_filename, bouton_telechargement = self.tab_liste_stations.download_menu(
                    text_kwargs={'name': 'Entrer nom de fichier', 'value': filepath.name},
                    button_kwargs={'name': 'Télécharger la liste des stations'}
                )
                sortie = pn.Column(msg, self.tab_liste_stations,
                                   pn.Row(dst_filename, bouton_telechargement))
            except Exception as exc:
                sortie = pn.pane.Str(traceback.format_exc())
            return sortie
        else:
            return sortie

    def _montrer_plus_proches_voisins_widgets(self, df_liste_stations):
        sortie = None
        if len(df_liste_stations) > 0:
            sortie = pn.Column(
                "## Définition de la station de référence",
                pn.Row(self._ref_station_name_widget, self._ref_station_altitude_widget),
                pn.Row(self._ref_station_lat_widget, self._ref_station_lon_widget),
                "## Sélection des plus proches voisins",
                self._nn_rayon_km_widget,
                self._bouton_liste_stations_nn,
                self._sortie_liste_stations_nn,
            )
        return sortie        

    def _selectionner_plus_proches_voisins(self, event):
        sortie = "Cliquer pour sélectionner les stations les plus proches..."
        if event:
            # Écraser la liste des stations les plus proches précédente
            self.tab_liste_stations_nn.value = pd.DataFrame()
            try:
                ref_station_latlon = [self._ref_station_lat_widget.value,
                                      self._ref_station_lon_widget.value]
                self.tab_liste_stations_nn.value = geo.selection_plus_proches_voisins(
                    self.tab_liste_stations.value, ref_station_latlon,
                    self._client.latlon_labels,
                    rayon_km=self._nn_rayon_km_widget.value)

                filepath = meteofrance.get_filepath_liste_stations_nn(
                    self._client, self.ref_station_name, self.tab_liste_stations_nn.value)
                dst_filename, bouton_telechargement = self.tab_liste_stations_nn.download_menu(
                    text_kwargs={'name': 'Entrer nom de fichier', 'value': filepath.name},
                    button_kwargs={'name': 'Télécharger la liste des stations les plus proches'}
                )
                sortie = pn.Column(
                    pn.pane.Markdown("Stations les plus proches sélectionnées:"),
                    self.tab_liste_stations_nn,
                    pn.Row(dst_filename, bouton_telechargement))
            except Exception as exc:
                sortie = pn.pane.Str(traceback.format_exc())
            return sortie
        else:
            return sortie

    def _montrer_dates_widgets(self, df_liste_stations_nn,
                               lire_donnee_ref, df_meteo):
        sortie = None
        if ((len(df_liste_stations_nn) > 0) and
            lire_donnee_ref and (len(df_meteo) == 0)):
            sortie = pn.Column(
                "## Période de la donnée météo (stations et référence)",
                pn.Row(self._date_deb_widget, self._date_fin_widget))
        return sortie

    def _montrer_donnee_liste_stations_widgets(self, df_liste_stations_nn):
        sortie = None
        if len(df_liste_stations_nn) > 0:
            sortie = pn.Column(
                "## Obtention des données météorologiques horaires pour les stations voisines",
                self._bouton_donnee_liste_stations,
                self._sortie_donnee_liste_stations
            )
        return sortie    

    def _recuperer_donnee_liste_stations(self, event):
        sortie = "Cliquer pour récupérer les données météo pour la liste des stations..."
        if event:
            # Écraser donnee météo pour la liste des stations précédente
            self.tab_meteo.value = pd.DataFrame()
            try:
                if self._lire_donnee_liste_stations_widget.value:
                    # Lecture de la donnée météo pour la liste des stations
                    filepath = meteofrance.get_filepath_donnee_periode(
                        self._client, self.ref_station_name, self.tab_liste_stations_nn.value,
                        self._date_deb_widget.value, self._date_fin_widget.value)
                    self.tab_meteo.value = pd.read_csv(
                        filepath, parse_dates=[self._client.time_label],
                        index_col=[self._client.id_station_donnee_label,
                                   self._client.time_label])
                    msg = pn.pane.Markdown("Donnée météo pour la liste des stations lue:")
                else:
                    # Demande de la donnée météo pour la liste des stations
                    variables = [self._client.variables_labels[METEOFRANCE_FREQUENCE][k]
                         for k in VARIABLES_POUR_CALCULS_SANS_ETP]
                    self.tab_meteo.value = meteofrance.compiler_donnee_des_departements(
                        self._client, self.tab_liste_stations_nn.value,
                        frequence=METEOFRANCE_FREQUENCE)[variables]
    
                    # Sauvegarde de la donnée météo pour la liste des stations
                    time = self.tab_meteo.value.index.to_frame()[self._client.time_label]
                    date_deb_periode = time.min().isoformat().replace("+00:00", "Z")
                    date_fin_periode = time.max().isoformat().replace("+00:00", "Z")
                    filepath = meteofrance.get_filepath_donnee_periode(
                        self._client, self.ref_station_name, self.tab_liste_stations_nn.value,
                        date_deb_periode, date_fin_periode)
                    self.tab_meteo.value.to_csv(filepath)
                    msg = pn.pane.Markdown("Donnée météo pour la liste des stations téléchargée:")
                dst_filename, bouton_telechargement = self.tab_meteo.download_menu(
                    text_kwargs={'name': 'Entrer nom de fichier',
                                 'value': filepath.name},
                    button_kwargs={'name': 'Télécharger la donnée météo pour la liste des stations'}
                )
                sortie = pn.Column(msg, self.tab_meteo,
                                   pn.Row(dst_filename, bouton_telechargement))
            except Exception as exc:
                sortie = pn.pane.Str(traceback.format_exc())
            return sortie
        else:
            return sortie

    def _montrer_donnee_ref_widgets(self, df_meteo, df_liste_stations_nn,
                                    lire_donnee_ref):
        sortie = None
        if ((len(df_meteo) > 0) or
            ((len(df_liste_stations_nn) > 0) and lire_donnee_ref)):
            sortie = pn.Column(
                "## Interpolation des données météorologiques à la station de référence",
                self._bouton_donnee_ref,
                self._sortie_donnee_ref
            )
        return sortie    

    def _recuperer_donnee_ref(self, event):
        sortie = "Cliquer pour récupérer les données météo de station de référence..."
        if event:
            # Écraser donnee météo pour la station de référence précédente
            self.tab_meteo_ref_heure_si.value = pd.DataFrame()
            self.tab_meteo_ref_si.value = pd.DataFrame()
            try:
                if self.date_deb is None:
                    time = self.tab_meteo.value.index.to_frame()[self._client.time_label]
                    self.date_deb = time.min().isoformat().replace("+00:00", "Z")
                if self.date_fin is None:
                    time = self.tab_meteo.value.index.to_frame()[self._client.time_label]
                    self.date_fin = time.max().isoformat().replace("+00:00", "Z")    
                filepath = meteofrance.get_filepath_donnee_periode(
                    self._client, self.ref_station_name, self.tab_liste_stations_nn.value,
                    self.date_deb, self.date_fin, ref=True)
                if self._lire_donnee_ref_widget.value:
                    # Lecture de la donnée météo pour la station de référence
                    df_meteo_ref_heure = pd.read_csv(
                        filepath, parse_dates=[self._client.time_label],
                        index_col=self._client.time_label)
                    msg = pn.pane.Markdown("Donnée météo pour la station de référence lue:")
                else:
                    # Demande de la donnée météo pour la station de référence
                    df_meteo_ref_heure = geo.interpolation_inverse_distance_carre(
                        self.tab_meteo.value, self.tab_liste_stations_nn.value['distance'])
    
                    # Sauvegarde de la donnée météo pour la station de référence
                    df_meteo_ref_heure.to_csv(filepath)
                    msg = pn.pane.Markdown("Donnée météo pour la station de référence interpolée:")

                df_meteo_ref_heure_renom = meteofrance.renommer_variables(
                    self._client, df_meteo_ref_heure, METEOFRANCE_FREQUENCE)


                df_meteo_ref_heure_si = meteofrance.convertir_unites(
                    self._client, df_meteo_ref_heure_renom)

                df_meteo_ref_heure_si['etp'] = etp.calcul_etp(
                    df_meteo_ref_heure_si,
                    self._ref_station_lat_widget.value,
                    self._ref_station_lon_widget.value,
                    self._ref_station_altitude_widget.value)

                # Calcul des valeurs journalières des variables météo
                df_meteo_ref_si = pd.DataFrame()
                for variable, series in df_meteo_ref_heure_si.items():
                    df_meteo_ref_si[variable] = [
                        getattr(df_meteo_ref_heure_si[variable],
                                VARIABLES_POUR_CALCULS[variable])(0)]
                df_meteo_ref_si.index = [(
                    f"{df_meteo_ref_heure_si.index.min()} - "
                    f"{df_meteo_ref_heure_si.index.max()}")]

                self.tab_meteo_ref_heure_si.value = df_meteo_ref_heure_si
                self.tab_meteo_ref_si.value = df_meteo_ref_si
                dst_filename, bouton_telechargement = self.tab_meteo_ref_heure_si.download_menu(
                    text_kwargs={'name': 'Entrer nom de fichier', 'value': filepath.name},
                    button_kwargs={'name': 'Télécharger la donnée météo pour la station de référence'}
                )
                sortie = pn.Column(
                    msg,
                    self.tab_meteo_ref_heure_si,
                    pn.Row(dst_filename, bouton_telechargement),
                    self.tab_meteo_ref_si.value
                )
            except Exception as exc:
                sortie = pn.pane.Str(traceback.format_exc())
            return sortie
        else:
            return sortie

    def __panel__(self):
        p = pn.Column(
            "# Récupération des données météo",
            self._lire_liste_stations_widget,
            self._lire_donnee_liste_stations_widget,
            self._lire_donnee_ref_widget,
            self._sortie_application_id,
            self._sortie_recuperer_liste_stations,
            self._sortie_selectionner_plus_proches_voisins,
            self._sortie_montrer_dates_widgets,
            self._sortie_recuperer_donnee_liste_stations,
            self._sortie_recuperer_donnee_ref
        )

        return p
