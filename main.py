import requests
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

#create function to download data source and save to csv file
def download_data(url, destination):
    r = requests.get(url)
    open(destination, 'wb').write(r.content)

#data sources
DATA_SOURCES = [
    {'url': 'https://opendata.ecdc.europa.eu/covid19/vaccine_tracker/csv/data.csv', 'filename': 'EU Vaccinations.csv'},
    {'url': 'https://gist.githubusercontent.com/radcliff/f09c0f88344a7fcef373/raw/2753c482ad091c54b1822288ad2e4811c021d8ec/wikipedia-iso-country-codes.csv', 'filename': 'country_codes.csv'},
    {'url': 'https://opendata.ecdc.europa.eu/covid19/virusvariant/csv/data.csv', 'filename': 'EU Variants.csv'},
]

#download data sources using function defined above
for source in DATA_SOURCES:
    download_data(source['url'], source['filename'])

#read in csv files to pandas datasets.
vaccines = pd.read_csv('EU Vaccinations.csv')
variants = pd.read_csv('EU Variants.csv')
country = pd.read_csv('country_codes.csv')

#view dataframe info and check for NaN. Drop columns where there is a lot of missing values. Check for duplicates

#vaccines.info()
#print(vaccines.isnull().values.any())       #NaN True
#NaN_vaccines = vaccines.isnull().sum()      #find which columns have nan. If many Nan, drop.
#print(NaN_vaccines)
vaccines['Vaccine'] = vaccines['Vaccine'].fillna(0)
vaccines = vaccines.drop(columns=['Denominator','FirstDoseRefused'])
# duplicateRows = vaccines[vaccines.duplicated()]   #No duplicate rows
# print(duplicateRows)

# variants.info()
# print(variants.isnull().values.any())       #NaN True
# NaN_variants = variants.isnull().sum()
# print(NaN_variants)
variants = variants.drop(columns=['number_sequenced_known_variant','percent_variant'])

# country.info()
# print(country.isnull().values.any())
# NaN_country = country.isnull().sum()      #NaN True but the only value was 'NA' which is the Alpha 2 code for Namibia so not a real 'NaN'
# print(NaN_country)
# duplicateRows = country[country.duplicated()]  #no duplicate rows
# print(duplicateRows)

#sum columns and prevent overlap
vaccines = vaccines[vaccines['TargetGroup']=='ALL']     #To prevent duplication/overlap of groups
vaccines['Total_Dose'] = vaccines['FirstDose']+vaccines['SecondDose']+vaccines['DoseAdditional1']+vaccines['UnknownDose']

#Merge country codes and EU variants, drop duplicate code column & rename
country = country.drop(columns=['Alpha-3 code','Numeric code','ISO 3166-2'])    #drop unecessary columns before merge
vaccines = vaccines.merge(country,left_on='ReportingCountry', right_on='Alpha-2 code')
vaccines = vaccines.drop(columns=['Alpha-2 code', 'ReportingCountry','Region'])
vaccines = vaccines.rename(columns={'English short name lower case':'Country'})

#Pivot table on Vaccine rollout to find top 5 and bottom 5 (per population)
vacc_pivot = pd.pivot_table(vaccines, values=['Total_Dose', 'Population'], columns=['Country'], aggfunc={'Total_Dose' : np.sum, 'Population' : np.min})
vacc_pivot = vacc_pivot.sort_values(by ='Total_Dose', axis=1)
vacc_pivot = vacc_pivot.transpose()
vacc_pivot['vacc_per_pop'] = vacc_pivot['Total_Dose']/vacc_pivot['Population']

# FIG 1: investigate correlation between countries' population and vaccine rollout
sns.set_theme(style="white")

plt.figure(1)
Fig1 = sns.scatterplot(data = vacc_pivot/10000000, x = 'Population', y = 'Total_Dose', size='vacc_per_pop', hue='vacc_per_pop', sizes=(20,200))
Fig1.set_title('EU Countries Population vs. COVID-19 Vaccine Rollout')
Fig1.set_xlabel('Population (Millions)')
Fig1.set_ylabel('Total Doses of Vaccine Administered (Millions)')

#FIG2
plt.figure(2)
received_pivot = pd.pivot_table(vaccines, values=['NumberDosesReceived', 'Population', 'NumberDosesExported'], columns=['Country'], aggfunc={'NumberDosesReceived' : np.sum, 'Population' : np.min, 'NumberDosesExported' : np.sum})
received_pivot = received_pivot.transpose()
received_pivot['received_per_pop'] = received_pivot['NumberDosesReceived']/received_pivot['Population']
received_pivot['vacc_per_pop'] = vacc_pivot['Total_Dose']/vacc_pivot['Population']
received_pivot = received_pivot.reset_index()
received_pivot = received_pivot.sort_values(by='received_per_pop', ascending=False)

ax = sns.barplot(x="Country", y="received_per_pop", data=received_pivot,  palette="Blues_d")
ax.set(xlabel='Country', ylabel='# Vaccines Received Per Population', title = 'Vaccines Received per EU Country by Population')
plt.xticks(rotation='vertical')

# Fig3 - Heatmap of vaccine types administered
plt.figure(3)
vaccines['Total_Dose_m'] = vaccines['Total_Dose']/1000000
vacc_breakdown = pd.pivot_table(vaccines, values=['Total_Dose_m'] ,columns = ['Country', 'Vaccine'], aggfunc=({'Total_Dose_m': np.sum}))
vacc_breakdown = vacc_breakdown.transpose()
vacc_breakdown = vacc_breakdown.reset_index()

heatmap = vacc_breakdown.pivot('Vaccine','Country', 'Total_Dose_m')
ax = sns.heatmap(heatmap, linewidths=.5, cmap='flare', xticklabels=True, yticklabels=True)
ax.set_title('Heatmap of administered vaccine dose type per EU Country')
plt.ylabel('Vaccines Administered (millions)')

ax.figure.tight_layout()

#Fig 4 - vaccines per age group across all
vaccines_all=vaccines[vaccines['TargetGroup']=='ALL']
vacc_age = pd.pivot_table(vaccines_all, index='Vaccine', values=('FirstDose','SecondDose','DoseAdditional1', 'UnknownDose'))

vacc_age=vacc_age.reset_index()
vacc_age = pd.melt(vacc_age, id_vars = 'Vaccine', value_vars=('FirstDose','SecondDose','DoseAdditional1','UnknownDose'), var_name='Dose', value_name='count')

h = sns.FacetGrid(vacc_age, col='Dose')
h= (h.map(sns.barplot, 'Vaccine', 'count', order=['AZ', 'COM', 'JANSS', 'MOD', 'UNK', 'BECNBG', 'SPU'], palette="Paired").add_legend())
h.set_titles("{col_name}")
h.set_axis_labels(x_var="Vaccine", y_var="# Administered Doses")
h.set_xticklabels(rotation = 90)
h.fig.suptitle('Breakdown of Vaccine Types per Administered Dose - EU')

#Figure 5
g = sns.FacetGrid(vacc_age, col='Vaccine', height=2.5)
g= (g.map(sns.barplot, 'Dose', 'count', order=['FirstDose','SecondDose', 'DoseAdditional1','UnknownDose'], palette="Paired").add_legend())
g.set_titles("{col_name}")
g.set_axis_labels(x_var="Vaccine", y_var="# Administered Doses")
g.set_xticklabels(rotation = 90)
g.fig.suptitle('Breakdown of Dose Type per Vaccine - EU')
plt.tight_layout
plt.show()

print('Finished!')