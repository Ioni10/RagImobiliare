import pandas as pd

# df = pd.read_csv("Bucurestiv2.csv")
# df['parking'] = df['parking'].map({"yes": 1, "unknown": 0})
# df['parking'] = df['parking'].astype(int)
#
# df.to_csv("Bucurestiv3.csv", index=False)

df = pd.read_csv("Bucurestiv3.csv")


df.loc[df['region'] == 'Rahova', 'neighborhood_real'] = 'Sector 5'
df.loc[df['region'] == 'Brâncuși', 'neighborhood_real'] = 'Sector 6'
df.loc[df['region'] == 'Dămăroaia', 'neighborhood_real'] = 'Sector 6'
df.loc[df['region'] == 'Drumul Taberei', 'neighborhood_real'] = 'Sector 6'
df.loc[df['region'] == 'Centrul Civic', 'neighborhood_real'] = 'Sector 3'
df.loc[df['region'] == 'Gramont', 'neighborhood_real'] = 'Sector 4'
df.loc[df['region'] == 'Bucureștii Noi', 'neighborhood_real'] = 'Sector 1'
df.loc[df['region'] == 'Grozăvești', 'neighborhood_real'] = 'Sector 6'
df.loc[df['region'] == 'Ghencea', 'neighborhood_real'] = 'Sector 6'
df.loc[df['region'] == 'Progresul', 'neighborhood_real'] = 'Sector 4'
df.loc[df['region'] == 'Titan - Balta Albă', 'neighborhood_real'] = 'Sector 3'
df.loc[df['region'] == 'Traian', 'neighborhood_real'] = 'Sector 2'
df.loc[df['region'] == 'Colentina', 'neighborhood_real'] = 'Sector 2'
df.loc[df['region'] == 'Doamna Ghica', 'neighborhood_real'] = 'Sector 2'
df.loc[df['region'] == 'Tineretului', 'neighborhood_real'] = 'Sector 4'
df.loc[df['region'] == 'Grivița', 'neighborhood_real'] = 'Sector 1'
df.loc[df['region'] == 'Fundeni', 'neighborhood_real'] = 'Sector 2'

print(df['neighborhood_real'].head(20))

df.to_csv("bbb.csv", index=False)