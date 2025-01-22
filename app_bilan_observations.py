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
