from Munin.Geo import *

print(Odin_temperature_sum(57.9,100))

print(RetrieveGeoCode.getDistanceToCoast(14.784528,56.892405)) #Växjö
print(RetrieveGeoCode.getDistanceToCoast(20.270130,63.827857)) #Umeå

print(RetrieveGeoCode.getCountyCode(14.784528,56.892405)) #Växjö
print(RetrieveGeoCode.getCountyCode(20.270130,63.827857)) #Umeå

print(RetrieveGeoCode.getClimateCode(14.784528,56.892405)) #Växjö
print(RetrieveGeoCode.getClimateCode(20.270130,63.827857)) #Umeå

print(eriksson_1986_humidity(14.784528,56.892405)) #Växjö
print(eriksson_1986_humidity(20.270130,63.827857)) #Umeå
