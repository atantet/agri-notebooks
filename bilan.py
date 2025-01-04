import pandas as pd


# Coefficients culturaux (KC) par culture et par stade
KC = {
    'Pomme de terre': {'Vegetation': 0.9, 'Maximale': 1.05}
}

# Réserve Utile (RU) par cm de terre fine (mm/cm de terre fine) en fonction de la texture du sol
RU_PAR_CM_DE_TF = {
    'Terres argileuses': 1.85,
    'Argiles sableuses': 1.7, 'Argiles sablo-limoneuses': 1.8, 'Argiles limono-sableuses': 1.8, 'Argiles limoneuses': 1.9,
    'Terres argilo-sableuses': 1.7, 'Terres argilo-limono-sableuses': 1.8, 'Terres argilo-limoneuses': 2.,
    'Terres sablo-argileuses': 1.4, 'Terres sablo-limono-argileuses': 1.5, 'Terres limono-sablo-argileuses': 1.65, 'Terres limono-argileuses': 2.00,
    'Terres sableuses': 0.7, 'Terres sablo-limoneuses': 1., 'Terres limono-sableuses': 1.55, 'Terres limoneuses': 1.8
}

# Coefficient de conversion de la RU en RFU (entre 1/2 et 2/3)
RU_VERS_RFU_PAR_DEFAUT = 2. / 3

# Fraction de la réserve utile du sol remplie d'eau (entre 0 pour une période sèche et 1 pour une période pluvieuse)
FRACTION_REMPLIE_PAR_DEFAUT = 1.

# Profondeurs d'enracinement typiques
PROFONDEUR_ENRACINEMENT_TYPIQUE = {
    'Radis': 15.,
    'Salade': 15.,
    'Choux': 20.,
    'Epinard': 20.,
    'Oignon': 20.,
    'Aubergine': 30.,
    'Carotte': 30.,
    'Courge': 30.,
    'Courgette': 30.,
    'Poivron': 30.,
    'Pomme de terre': 30.,
    'Tomate': 30.
}

def calcul_reserve_utile(
    texture, fraction_cailloux, culture, fraction_remplie=FRACTION_REMPLIE_PAR_DEFAUT):
    ''' Calcul de la RU (mm).'''
    # RU par cm de terre fine pour cette texture
    ru_par_cm_de_tf_texture = RU_PAR_CM_DE_TF[texture]

    # Calcul de la profondeur de terre fine
    profondeur_enracinement = PROFONDEUR_ENRACINEMENT_TYPIQUE[culture]
    profondeur_terrefine = profondeur_enracinement * (1. - fraction_cailloux)

    ru = ru_par_cm_de_tf_texture * profondeur_terrefine * fraction_remplie

    return ru, profondeur_terrefine, profondeur_enracinement

def calcul_reserve_facilement_utilisable(
    ru, ru_vers_rfu=RU_VERS_RFU_PAR_DEFAUT):
    ''' Calcul de la RFU (mm).'''
    return ru * ru_vers_rfu

def calcul_etm_culture(culture, stade, s_meteo, etp_label='etp'):
    ''' Calcul de l'évalotranspiration maximale de la culture (mm).'''
    # KC de la culture pour ce stade
    kc_culture = KC[culture][stade]

    etm_culture = kc_culture * s_meteo.loc[etp_label]

    return etm_culture

def calcul_bilan(
    texture, fraction_cailloux,
    culture, stade,
    s_meteo,
    fraction_remplie=FRACTION_REMPLIE_PAR_DEFAUT, ru_vers_rfu=RU_VERS_RFU_PAR_DEFAUT,
    rfu_cible=None, precipitation_label='rr1'):
    ''' Calcul du besoin en irrigation (mm).'''
    s = pd.Series(dtype=float)

    s.loc['ru'], s.loc['profondeur_terrefine'], s.loc['profondeur_enracinement'] = (
        calcul_reserve_utile(texture, fraction_cailloux, culture, fraction_remplie))
    
    s.loc['rfu'] = calcul_reserve_facilement_utilisable(s.loc['ru'], ru_vers_rfu)

    s.loc['etm_culture'] = calcul_etm_culture(culture, stade, s_meteo)

    if rfu_cible is None:
        rfu_cible = s.loc['rfu']
    s.loc['rfu_cible'] = rfu_cible
    
    s.loc['precipitation'] = s_meteo.loc[precipitation_label]

    s.loc['besoin_irrigation'] = s.loc['rfu_cible'] + s.loc['etm_culture'] - (
        s.loc['rfu'] + s.loc['precipitation'])

    return s