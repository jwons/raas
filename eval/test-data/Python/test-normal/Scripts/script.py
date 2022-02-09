import skychart as sch
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt

# Base dataframe
df = pd.read_csv("../Data/vis_hip.csv")

# DataFrame of stars that will be shown
df_show = df[df['Vmag']<5]

# Load constellation data
dc_const = sch.load_constellations()

# Show only Ursa Major and Cassiopeia constellations
dc_const = {'UMa': dc_const['UMa'],
            'Cas': dc_const['Cas']}

fig, ax, df_show = sch.draw_chart(df, df_show, dc_const, alpha=0.3)
plt.show()
