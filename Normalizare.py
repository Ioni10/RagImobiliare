import pandas as pd

df = pd.read_csv("olx_bucuresti_imobiliare_enhanced.csv")


df['parking'] = df['parking'].map({"yes": 1, "unknown": 0})
df['parking'] = df['parking'].astype(int)

df.to_csv("Bucuresti.csv", index=False)