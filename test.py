import pandas as pd
d = pd.read_csv("pilot_profiles.csv")
print(d[d.match_status != "matched"][["Title","match_status","oa_name","title_sim"]].to_string())