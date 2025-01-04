import numpy as np
import pandas as pd

# Chaleur latente de vaporisation de l’eau (MJ kg-1)
LAMBDA = 2.45

# Facteur de la constante psychrométrique (kPa K-1)
FACTEUR_GAMMA = 0.665e-3

# Constante de Stefan-Boltzmann (MJ m-2 K-4 h-1)
SIGMA = 2.043e-10 

# Albedo
ALPHA = 0.23

# Émissivité
EPSILON = 1.0

# Constante solaire (MJ m-2 min-1)
G_SC = 0.0820

def calcul_rayonnement_net_ondes_courtes(df):
    # Rayonnement solaire incident en MJ m-2 h-1
    r_s = df['ray_glo01'] * 1.e-6

    # Calcul du rayonnement net aux ondes courtes
    r_ns = (1 - ALPHA) * r_s

    return r_ns

def calcul_angles_solaires_debut_fin(time, longitude_rad):
    # Calcul de la correction saisonière du temps solaire
    b = 2 * np.pi * (time.dayofyear - 81) / 364
    s_c = 0.1645 * np.sin(2 * b) - 0.1255 * np.cos(b) - 0.025 * np.sin(b) 

    # Calcul du temps solaire local
    TIMEZONE_OFFSET = 1.
    local_time = time.hour + TIMEZONE_OFFSET
    L_Z = 345.
    l_m = -np.rad2deg(longitude_rad)
    lst = local_time + 0.06667 * (L_Z - l_m) + s_c

    # Calcul de l'angle du temps solaire au milieu de la période
    omega = np.pi / 12 * (lst - 12)

    # Calcul des angles de temps solaire au début et à la fin de la période
    T_1 = 1
    omega_diff = 2 * np.pi * T_1 / 24
    omega_1 = omega - omega_diff / 2
    omega_2 = omega + omega_diff / 2
    
    return omega_1, omega_2

def calcul_rayonnement_net_ondes_longues(df, ee, latitude_rad, longitude_rad, altitude):
    # Rayonnement solaire incident en MJ m-2 h-1
    r_s = df['ray_glo01'] * 1.e-6
    
    # Calcul de la distance relative inverse Terre-Soleil
    time = pd.DatetimeIndex(df.index)
    d_r = 1. + 0.033 * np.cos(2 * np.pi / 365. * time.dayofyear)

    # Calcul de la déclinaison solaire
    delta_ang = 0.409 * np.sin(2 * np.pi / 365. * time.dayofyear - 1.39)

    # Calcul du rayonnement extraterrestre
    omega_1, omega_2 = calcul_angles_solaires_debut_fin(time, longitude_rad)

    r_a = np.maximum(0., 12 * 60 / np.pi * G_SC * d_r * (
        (omega_2 - omega_1) * np.sin(latitude_rad) * np.sin(delta_ang) +
        np.cos(latitude_rad) * np.cos(delta_ang) * (np.sin(omega_2) - np.sin(omega_1))))

    # Calcul du rayonnement solaire incident pour un ciel clair
    r_so = (0.75 + 2.e-5 * altitude) * r_a

    # Calcul de la clareté
    clarete = np.minimum(1., r_s / r_so).values
    # Durant la nuit la clareté est suppossée égale à celle 2h avant le couché
    # Si des heures de journée avant la nuit ne sont pas disponibles on utilise
    # les heures après le levé
    tol = 1.e-8
    try:
        idx_couche = np.nonzero((r_s.values[1:] < tol) & (r_s.values[:-1] > tol))[0][0]
        clarete[idx_couche + 1:] = clarete[idx_couche - 1]
    except IndexError:
        pass
    try:
        idx_leve = np.nonzero((r_s.values[1:] > tol) & (r_s.values[:-1] < tol))[0][0] + 1
        clarete[:idx_leve] = clarete[idx_leve + 1]
    except IndexError:
        pass

    # Calcul du rayonnement net aux ondes longues
    r_nl = SIGMA * df['t']**4 * (0.34 - 0.14 * np.sqrt(ee)) * (
        1.35 * clarete - 0.35)

    return r_nl

def calcul_etp(df, latitude, longitude, altitude):
    '''Calcul de l'évapotranspiration potentielle pour une station.'''
    # Conversion de degrés en radians pour la référence
    latitude_rad, longitude_rad = np.deg2rad([latitude, longitude])
    
    # Calcul de la pression de vapeur saturante (kPa)
    es = 0.6108 * np.exp(17.27 * (df['t'] - 273.15) / (df['t'] - 35.85))
    
    # Calcul de la pente de la courbe de pression de vapeur à la température moyenne de l'air (kPa K-1)
    delta = 4098. * es / (df['t'] - 35.85)**2

    # Calcul standard de la pression moyenne en fonction de l'altitude (kPa)
    pression = 101.3 * ((293. - 0.0065 * altitude) / 293.)**5.26

    # Calcul de la constante psychrométrique
    gamma = FACTEUR_GAMMA * pression

    # Calcul de la pression de vapeur effective (kPa)
    ee = es * df['u'] / 100

    # Calcul du rayonnement net
    r_ns = calcul_rayonnement_net_ondes_courtes(df)
    r_nl = calcul_rayonnement_net_ondes_longues(
        df, ee, latitude_rad, longitude_rad, altitude)
    r_n = r_ns - r_nl
    
    # Calcul de la vitesse du vent à 2 m à partir de celle à 10 m
    u2 = df['ff'] * 4.87 / np.log(67.8 * 10 - 5.42)

    # Calcul de l'ETP (mm h-1)
    denominateur = delta + gamma * (1. + 0.34 * u2)
    etp1 = np.maximum(0, delta * r_n / LAMBDA / denominateur)
    etp2 = np.maximum(0, gamma * 37. / df['t'] * u2 * (es - ee) / denominateur)
    etp = etp1 + etp2

    return etp