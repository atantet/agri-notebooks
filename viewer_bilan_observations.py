import pandas as pd
import panel as pn
import param
import plotly.graph_objects as go
import numpy as np

import bilan
from datastore_observations import DataStoreObservations

# Choix de la texture
DEFAUT_TEXTURE = 'Terres limoneuses'

# Fraction du sol occupé par des cailloux et graviers (entre 0 pour absence de cailloux et 1 pour totalité de cailloux)
DEFAUT_FRACTION_CAILLOUX = 0.1

# Part de la RU facilement utilisable (entre 1/2 et 2/3)
DEFAUT_RU_VERS_RFU = 0.67

# Fraction de la réserve utile du sol remplie d'eau (entre 0 pour une période sèche et 1 pour une période pluvieuse)
DEFAUT_FRACTION_RU_REMPLIE = 1.

# Besoin d'irrigation minimal à partir du quel irriguer (mm)
DEFAUT_SEUIL_IRRIGATION = 0.1

# Conversion de hauteur (mm) vers durée d'irrigation (min)
DEFAUT_HAUTEUR_VERS_DUREE_IRRIGATION = 10

class View(pn.viewable.Viewer):
    datastore = param.ClassSelector(class_=DataStoreObservations)

class ViewerBilanObservations(View):    
    def __init__(self, **params):
        super().__init__(**params)

        # Widgets
        margin = (5, 40)
        self._texture_widget = pn.widgets.Select(
            name='Texture', options=list(bilan.RU_PAR_CM_DE_TF),
            value=DEFAUT_TEXTURE, margin=margin)
        self._fraction_cailloux_widget = pn.widgets.EditableFloatSlider(
            name='Pierrosité',
            start=0., end=1., step=0.01,
            value=DEFAUT_FRACTION_CAILLOUX, margin=margin)
        self._fraction_ru_remplie_widget = pn.widgets.EditableFloatSlider(
            name="Fraction de la RU remplie d'eau",
            start=0., end=1., step=0.1,
            value=DEFAUT_FRACTION_RU_REMPLIE, margin=margin)
        self._ru_vers_rfu_widget = pn.widgets.EditableFloatSlider(
            name="Part de la RU facilement utilisable",
            start=0.5, end=0.7, step=0.05,
            value=DEFAUT_RU_VERS_RFU, margin=margin)
        self._seuil_irrigation_widget = pn.widgets.EditableFloatSlider(
            name="Besoin au-dessus duquel irriguer (mm)", 
            start=0., end=10., step=0.1,
            value=DEFAUT_SEUIL_IRRIGATION, margin=margin) 
        self._hauteur_vers_duree_irrigation_widget = pn.widgets.EditableIntSlider(
            name="Hauteur vers durée d'irrigation (mm min-1)", 
            start=1, end=180, step=1,
            value=DEFAUT_HAUTEUR_VERS_DUREE_IRRIGATION, margin=margin)
        list_kc = list(bilan.KC)
        self._culture_widget = pn.widgets.Select(
            name='Culture', options=list_kc, value=list_kc[0],
            margin=margin)
        self._stade_widget = pn.widgets.Select(
            name='Stade', options=list(bilan.KC[list_kc[0]]),
            margin=margin)

        # Liaison des stades au choix de culture
        self._sortie_maj_stades_culture_choisie = pn.bind(
            self._maj_stades_culture_choisie, self._culture_widget)

        # Liaison du plot au widgets
        self._sortie_plots = pn.bind(
            self._creer_plots, self.datastore.tab_meteo_ref_si,
            self._texture_widget, self._fraction_cailloux_widget,
            self._fraction_ru_remplie_widget, self._ru_vers_rfu_widget,
            self._seuil_irrigation_widget,
            self._hauteur_vers_duree_irrigation_widget,
            self._culture_widget, self._stade_widget
        )
        
    def _maj_stades_culture_choisie(self, culture_choisie):
        self._stade_widget.options = list(bilan.KC[culture_choisie])
        self._stade_widget.value = list(bilan.KC[culture_choisie])[0]

        return self._stade_widget
    
    def _creer_plot_sol(self, s, width=500, height=400):
        idx_deb = 1
        idx_fin = 5
        x = s.index[idx_deb:]
        s_ru = s.iloc[1:5].astype(float).values
        y = np.concatenate([[s_ru[0]], s_ru[1:] - s_ru[:-1]])
        measure = ['absolute'] + ['delta'] * (idx_fin - idx_deb - 1)
        wf = go.Waterfall(x=x, y=y, measure=measure,
                          texttemplate='%{final:.1f}', cliponaxis=False)
        fig = go.Figure(wf)
        fig.update_layout(
            title="Réserve accessible aux racines (valeurs absolues)",
            yaxis_title="Hauteur (mm)",
            width=width,
            height=height
        )
        p = pn.pane.Plotly(fig)
    
        return p

    def _creer_plot_besoin(self, s, width=500, height=400):
        idx_deb = 4
        idx_fin = 9
        x = s.index[idx_deb:]
        y = s.iloc[idx_deb:idx_fin].astype(float)
        measure = ['absolute'] + ['relative'] * (idx_fin - idx_deb - 2) + ['absolute']
        wf = go.Waterfall(x=x, y=y, measure=measure,
                          texttemplate='%{delta:.1f}', cliponaxis=False)
        fig = go.Figure(wf)
        fig.update_layout(
            title="Bilan hydrique (différences)",
            yaxis_title="Hauteur (mm)",
            width=width,
            height=height
        )
        p = pn.pane.Plotly(fig)

        return p

    def _creer_plots(
        self, df, texture, fraction_cailloux,
        fraction_ru_remplie, ru_vers_rfu,
        seuil_irrigation, hauteur_vers_duree_irrigation,
        culture, stade
    ):
        guide = pn.pane.Str(
            "Récupérérer la donnée météo de la station de référence "
            "pour pouvoir exécuter le bilan hydrique...")
        sortie = guide
        if len(df) > 0:
            sortie = pn.Column(
                pn.Row(self._texture_widget,
                       self._fraction_cailloux_widget),
                pn.Row(self._fraction_ru_remplie_widget,
                       self._ru_vers_rfu_widget),
                pn.Row(self._seuil_irrigation_widget,
                       self._hauteur_vers_duree_irrigation_widget),
                pn.Row(self._culture_widget,
                       self._sortie_maj_stades_culture_choisie)
            )
            
            # Get the data
            df_bilan = bilan.calcul_bilan(
                df.iloc[0],
                texture, fraction_cailloux,
                culture, stade,
                fraction_ru_remplie, ru_vers_rfu,
                seuil_irrigation=seuil_irrigation,
                hauteur_vers_duree_irrigation=hauteur_vers_duree_irrigation)  

            plot_sol = self._creer_plot_sol(df_bilan)
            plot_besoin = self._creer_plot_besoin(df_bilan)
            plot_titre = pn.pane.Markdown(
                f"### Pour {culture.lower()} au stade {stade.lower()}")

            sortie = pn.Column(
                sortie,
                plot_titre,
                pn.Row(plot_sol, plot_besoin)
            )
    
            if df_bilan['irrigation']:
                plot_irrigation = pn.pane.Markdown(
                    f"### Besoin d'arroser {df_bilan['duree_irrigation']:.0f} min")
                sortie = pn.Column(
                    sortie,
                    plot_irrigation
                )
    
        return sortie
        
    def __panel__(self):
        return pn.Column(
            pn.pane.Markdown("## Exécution du bilan hydrique"),
            self._sortie_plots
        )