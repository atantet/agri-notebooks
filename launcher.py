import subprocess

# Path to the notebook and port
notebook = "bilan_hydrique_observation_horaire.ipynb"
port = "5006"

# Start the Panel server
subprocess.run(["panel", "serve", notebook, "--port", port])
