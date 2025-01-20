# TODO
# Dernières 24h checkbox
# disable
# Réinitialiser bouton
# Layout/Template
import panel as pn
import param
from datastore_observations import DataStoreObservations
from viewer_bilan_observations import ViewerBilanObservations

class AppBilanObservations(pn.viewable.Viewer):
    datastore = param.ClassSelector(class_=DataStoreObservations)
    view = param.ClassSelector(class_=ViewerBilanObservations)

    def __init__(self, **params):
        super().__init__(**params)

    def __panel__(self):
        titre = pn.pane.Markdown(
            "# Bilan hydrique à partir des dernières 24h "
            "d'observations Météo-France")
        return pn.Column(titre, self.datastore, self.view)