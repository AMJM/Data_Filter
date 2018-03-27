import pandas as pd

df = pd.read_csv("C:\\Users\\Alex\\Google Drive\\2018-1\\PMR3500\\Dados\\Caso26\\smh_v00036.txt", escapechar="%", skiprows=2, delim_whitespace=True)
df.rename(columns=lambda x: x.strip(), inplace=True)
df = df[["time_stamp", "x", "y", "zz", "vx", "vy", "vzz", "rudder_demanded_orientation_0", "propeller_demanded_direction_0", "propeller_demanded_rpm_0"]]

df.to_csv("../Output/filtered.txt", index=False, sep=' ')