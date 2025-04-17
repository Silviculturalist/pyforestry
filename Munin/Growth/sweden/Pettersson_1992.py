#Nils Petterssons functions describe two scenarios:
#i) For planted stands
#ii) For naturally regenerated stands which have been thinned to density (PCT).

#Clarify stem Distributions. Complete implementation of randomly sampling individual trees from distribution.
#Each tree should get a Species, Diameter, Height, Volume .. ? 

#CHECK ERRONEOUS VOLDISTR FUNCTIONS!


#Stem distributions looks ok. But why does Spruce have such a stem # discrepancy between function and volume / diameter class volumes.?

import numpy as np
from math import log, exp, pi, factorial, sqrt, log10
from scipy.optimize import minimize, brentq, fsolve
from scipy import integrate
#import warnings
import matplotlib.pyplot as plt
import pandas as pd

class Pettersson1992:
    @staticmethod
    def cramerNormalPDF(x, mean, sd, skew, kurtosis, total):
        X = (x - mean) / sd  # X is the number of standard deviations from the mean
    
        def phi0(X):
            return (1 / sqrt(2 * pi)) * exp(-((X ** 2) / 2))
    
        def phi3(X):
            return (-X ** 3 + 3 * X) * phi0(X)
    
        def phi4(X):
            return (X ** 4 - 6 * X ** 2 + 3) * phi0(X)
    
        def phi6(X):
            return (X ** 6 - 15 * X ** 4 + 45 * X ** 2 - 15) * phi0(X)
    
        return ((total / sd) * (phi0(X) - (skew / factorial(3)) * phi3(X) + 
                (kurtosis / factorial(4)) * phi4(X) + 
                ((10 * skew ** 2) / factorial(6)) * phi6(X)))
    
    @staticmethod
    def getQMD(BA,stems):
        return sqrt((BA)/(((pi/4)/10E3)*stems))
    
    @staticmethod
    def sample(n,distr):
        def inverse_cdf(y):
            return brentq(lambda x: integrate.quad(distr, 0, x)[0] - y,0,50)

        return [inverse_cdf(np.random.uniform(0,50)) for _ in range(n)]
           
    @staticmethod
    def getVolumePine(latitude,height,diameter): #Brandel 1990
        if latitude>60:
            return 10**( -1.20914 + 	1.94740*log10(diameter)	-0.05947*log10(diameter+20) +	1.40958*log10(height)	-0.45810*log10(height-1.3))
        else:
            return 10**(-1.38903 +1.84493*log10(diameter) +	0.06563*log10(diameter+20) +	2.02122*log10(height)	-1.01095*log10(height-1.3))

    @staticmethod
    def getVolumeSpruce(latitude,height,diameter): #Brandel 1990
        if latitude>60:
            return 10**(-0.79783 + 	2.07157*log10(diameter)	-0.73882*log10(diameter+20) +	3.16332*log10(height)	-1.82622*log10(height-1.3))
        else:
            return 10**(-1.02039 +2.00128*log10(diameter) +	-0.47473*log10(diameter+20) +	2.87138*log10(height)	-1.61803*log10(height-1.3))




class PlantedSpruce (Pettersson1992):
    def __init__(self, H100, dominantHeight=14, latitude=64, saplingsPlanted=3500,saplingSquareSpacingM=None):
        self.species='Picea abies'
        self.latitude = latitude
        self.H100 = H100
        self.dominantHeight=dominantHeight
        if saplingsPlanted is None and saplingSquareSpacingM is not None:
            self.saplingsPlanted = 10000/saplingSquareSpacingM**2
        elif saplingsPlanted is not None:
            self.saplingsPlanted = saplingsPlanted
        self.HL = exp(-0.4168+log(dominantHeight)*1.0095-log(self.saplingsPlanted)*0.0558+ log(H100)*0.2054) #f.2
        self.TotalVolume = self.saplingsPlanted/(8094*(dominantHeight**-2.8673) + 0.2511*self.saplingsPlanted*(dominantHeight**-1.6611))
        self.FormHeight = exp(-0.9204-0.0286*log(self.saplingsPlanted)+0.8294*log(dominantHeight)+0.2265*log(self.H100))
        self.TotalBA = self.TotalVolume/self.FormHeight # Fh = V / BA
        self.BA = exp(0.0803+1.0018*log(self.TotalBA)-0.0072*log(self.saplingsPlanted)-0.0133*log(self.dominantHeight))
        self.stems = self.getStems()
        self.QMD = self.getQMD(self.BA,self.stems)
        self.DGV = exp(0.3731 + 0.0632*log(self.dominantHeight) + 0.8332*log(self.QMD))
        self.D800 = exp(0.7246 + 0.2639*log(self.dominantHeight) + 0.5345*log(self.QMD))
        self.D400 = exp(0.8600 + 0.2045*log(self.dominantHeight) + 0.5722*log(self.QMD))
        self.D100 = exp(1.1124 + 0.1263*log(self.dominantHeight)+ 0.5923*log(self.QMD))
        self.VolDistrMean =exp(0.5271 + 0.8418*log(self.QMD))
        self.VolDistrStd = exp(2.1613 + 0.4634*log(self.QMD) - 0.6656*log(self.H100))
        self.VolDistrSkew = exp(0.9021 + 0.1278*log(self.saplingsPlanted)-0.2647*log(self.H100)) - 3
        self.VolDistrKurtosis = exp(1.2019-0.1900*log(self.saplingsPlanted)+0.4445*log(self.H100)) - 3

        def eqSystem(variables):
            a, b = variables
            f1 = (self.D100/(a+b*self.D100))**2 + 1.3 - self.dominantHeight
            f2 = (self.QMD/(a+b*self.QMD))**2 + 1.3 - self.HL
            return [f1,f2]
        initial_guess = [1,1]

        self.HD_a, self.HD_b = fsolve(eqSystem,initial_guess)

    def getHeightofDiameter(self,Diameter):
        return (Diameter/(self.HD_a+self.HD_b*Diameter))**3 + 1.3 #Petterson 1955
    
    def getStems(self):
        SIdummy = 1 if self.H100 > 24 else 0

        if self.saplingsPlanted < 2500:
            dummy = 0
        elif self.saplingsPlanted < 4000:
            dummy = -0.0404
        elif self.saplingsPlanted < 6000:
            dummy = -0.0464
        else:
            dummy = -0.0689

        return exp(-0.5791+0.180*SIdummy+1.0499*log(self.saplingsPlanted)+log(self.dominantHeight)*dummy) 
        
    def getVolumeDistribution(self,class_middle):
        return self.cramerNormalPDF(x=class_middle,mean=self.VolDistrMean,sd=self.VolDistrStd,skew=self.VolDistrSkew,kurtosis=self.VolDistrKurtosis,total=self.TotalVolume)
    
    def ViewVolumeDistribution(self,start=1.5,stop=30,Percentage=True):
        Diameters = np.linspace(start,stop,2000)
        if Percentage:
            Percent = [element / self.TotalVolume for element in [self.getVolumeDistribution(class_middle=diameter) for diameter in Diameters]]
        else:
            Percent = [self.getVolumeDistribution(class_middle=diameter) for diameter in Diameters]
        #integ = integrate.quad(self.getVolumeDistribution,0,40)[0]
        plt.plot(Diameters,Percent)
        plt.xlabel("Diameter Class, cm")
        if Percentage:
            plt.ylabel("Percent of Volume")
        else:
            plt.ylabel('Volume')
        plt.title(f"Planted Spruce H100:{round(self.H100,1)} m, BA:{round(self.BA,1)}$m^2$,\nDominant height: {round(self.dominantHeight,1)} m")
        plt.show()

    def findStemDistribution(self,minD=None,minPercent=0,maxPercent=0,classes=200):
        #Find diameter of minimum class
        if minD is None:
            minD = minimize(lambda x: abs(minPercent - integrate.quad(self.getVolumeDistribution,0,x)[0]/self.TotalVolume),x0=0.1,bounds = [(0.0,self.QMD)]).x
        
        #Maximum class
        maxD = minimize(lambda x: abs(maxPercent - integrate.quad(self.getVolumeDistribution,x,self.QMD+60)[0]/self.TotalVolume),x0=self.QMD,bounds = [(self.QMD,self.QMD+60)]).x

        Diameters = np.linspace(minD,maxD,classes)
        HalfClassWidth = (maxD-minD)/(classes*2)

        classVolumes = np.array([integrate.quad(self.getVolumeDistribution,val-HalfClassWidth,val+HalfClassWidth)[0] for val in Diameters])

        Heights = np.array([self.getHeightofDiameter(diameter) for diameter in Diameters])

        Volumes = np.array([self.getVolumeSpruce(latitude=self.latitude,height=height,diameter=diameter) for height, diameter in zip(Heights, Diameters)])/1000

        return Diameters, classVolumes/Volumes

    def ViewStemDistribution(self,minD=None,minPercent=2,maxPercent=0,classes=200,Percentage=True):
        Diameter, stems = self.findStemDistribution(minD=minD,minPercent=minPercent,maxPercent=maxPercent,classes=classes)
        Diameter = Diameter.flatten()
        if Percentage:
            plt.bar(Diameter.flatten(),height=(stems*100)/sum(stems))
        else:
            plt.bar(Diameter.flatten(),stems)
        plt.xlabel("Diameter Class, cm")
        if Percentage:
            plt.ylabel("Percent of Stems")
        else:
            plt.ylabel('Stems')
        plt.suptitle(f"Planted Spruce H100:{round(self.H100,1)} m, BA:{round(self.BA,1)}$m^2$ \nDominant height:{round(self.dominantHeight,1)} m")
        plt.title(f"Function stems:{round(self.stems,1)}, Sum from Volume Distribution:{round(sum(stems),1)}")
        plt.show()      


    def generateStems(self):
        return self.sample(n=self.stems,distr=self.getVolumeDistribution)
        

class PlantedPine (Pettersson1992):
    def __init__(self, H100, dominantHeight=14, latitude=64, saplingsPlanted=3500,saplingSquareSpacingM=None):
        self.species='Pinus sylvestris'
        self.latitude = latitude
        self.H100 = H100
        self.dominantHeight=dominantHeight
        if saplingsPlanted is None and saplingSquareSpacingM is not None:
            self.saplingsPlanted = 10000/saplingSquareSpacingM**2
        elif saplingsPlanted is not None:
            self.saplingsPlanted = saplingsPlanted
        self.HL = exp(-0.1534 + log(dominantHeight)*1.0637- 0.0100*log(self.saplingsPlanted)) #f.1 
        self.TotalVolume = self.saplingsPlanted/(1873*(dominantHeight**-2.4173)+0.1482*self.saplingsPlanted*dominantHeight**-1.4247)
        self.FormHeight = exp(0.1666-0.0282*log(self.saplingsPlanted)+0.7054*log(dominantHeight))
        self.TotalBA = self.TotalVolume/self.FormHeight #Fh = V / BA
        self.BA = exp(0.1582+1.0176*log(self.TotalBA)-0.0178*log(self.saplingsPlanted)-0.0359*log(self.dominantHeight))
        self.stems = exp(-0.5256-0.2160*log(self.dominantHeight)+0.8760*log(self.saplingsPlanted)+0.5789*log(self.H100))
        self.QMD = self.getQMD(self.BA,self.stems)
        self.DGV = exp(0.2924 + 0.1235*log(self.dominantHeight) + 0.8028*log(self.QMD))
        self.D800 = exp( 0.8596 + 0.3010 * log(dominantHeight) + 0.4435 * log(self.QMD))
        self.D400 = exp( 0.9216 + 0.4888 * log(self.QMD) + 0.2684 * log(self.dominantHeight))
        self.D100 = exp( 1.0489 + 0.5018 * log(self.QMD) + 0.2421 * log(self.dominantHeight))
        self.VolDistrMean = exp(0.3607+ 0.8345*log(self.QMD)+0.0675*log(dominantHeight))
        self.VolDistrStd = exp(-0.2696 + 0.1336*log(self.QMD)+0.3949*log(dominantHeight))
        self.VolDistrSkew = exp(0.2825+0.0863*log(self.saplingsPlanted)) -3
        self.VolDistrKurtosis = exp(2.6786-0.1827*log(self.saplingsPlanted)) -3

        def eqSystem(variables):
            a, b = variables
            f1 = (self.D100/(a+b*self.D100))**2 + 1.3 - self.dominantHeight
            f2 = (self.QMD/(a+b*self.QMD))**2 + 1.3 - self.HL
            return [f1,f2]
        initial_guess = [1,1]

        self.HD_a, self.HD_b = fsolve(eqSystem,initial_guess)

    def getHeightofDiameter(self,Diameter): #Näslund 1936
        return (Diameter/(self.HD_a+self.HD_b*Diameter))**2 + 1.3

    def getVolumeDistribution(self,class_middle):
        return self.cramerNormalPDF(x=class_middle,mean=self.VolDistrMean,sd=self.VolDistrStd,skew=self.VolDistrSkew,kurtosis=self.VolDistrKurtosis,total=self.TotalVolume)
    
    def ViewVolumeDistribution(self,start=0,stop=30,Percentage=True):
        Diameters = np.linspace(start,stop,2000)
        if Percentage:
            Percent = [element / self.TotalVolume for element in [self.getVolumeDistribution(class_middle=diameter) for diameter in Diameters]]
        else:
            Percent = [self.getVolumeDistribution(class_middle=diameter) for diameter in Diameters]
        #integ = integrate.quad(self.getVolumeDistribution,0,40)[0]
        plt.plot(Diameters,Percent)
        plt.xlabel("Diameter Class, cm")
        if Percentage:
            plt.ylabel("Percent of Volume")
        else:
            plt.ylabel('Volume')
        plt.title(f"Planted Pine H100:{round(self.H100,1)} m, BA:{round(self.BA,1)}$m^2$ \nDominant height:{round(self.dominantHeight,1)} m")
        plt.show()

    def findStemDistribution(self,minD=None,minPercent=0,maxPercent=0,classes=200):
        #Find diameter of minimum class
        if minD is None:
            minD = minimize(lambda x: abs(minPercent - integrate.quad(self.getVolumeDistribution,0,x)[0]/self.TotalVolume),x0=0.1,bounds = [(0.0,self.QMD)]).x
        
        #Maximum class
        maxD = minimize(lambda x: abs(maxPercent - integrate.quad(self.getVolumeDistribution,x,self.QMD+60)[0]/self.TotalVolume),x0=self.QMD,bounds = [(self.QMD,self.QMD+60)]).x

        Diameters = np.linspace(minD,maxD,classes)
        HalfClassWidth = (maxD-minD)/(classes*2)

        classVolumes = np.array([integrate.quad(self.getVolumeDistribution,val-HalfClassWidth,val+HalfClassWidth)[0] for val in Diameters])

        Heights = np.array([self.getHeightofDiameter(diameter) for diameter in Diameters])

        Volumes = np.array([self.getVolumePine(latitude=self.latitude,height=height,diameter=diameter) for height, diameter in zip(Heights, Diameters)])/1000

        return Diameters, classVolumes/Volumes

    def ViewStemDistribution(self,minD=None,minPercent=2,maxPercent=0,classes=200,Percentage=True):
        Diameter, stems = self.findStemDistribution(minD=minD,minPercent=minPercent,maxPercent=maxPercent,classes=classes)
        Diameter = Diameter.flatten()
        if Percentage:
            plt.bar(Diameter.flatten(),height=(stems*100)/sum(stems))
        else:
            plt.bar(Diameter.flatten(),stems)
        plt.xlabel("Diameter Class, cm")
        if Percentage:
            plt.ylabel("Percent of Stems")
        else:
            plt.ylabel('Stems')
        plt.suptitle(f"Planted Pine H100:{round(self.H100,1)} m, BA:{round(self.BA,1)}$m^2$ \nDominant height:{round(self.dominantHeight,1)} m")
        plt.title(f"Function stems:{round(self.stems,1)}, Sum from Volume Distribution:{round(sum(stems),1)}")
        plt.show()      



class PCTSpruce (Pettersson1992):
    def __init__(self, H100, dominantHeight=14, latitude=64, InitStems=5000):
        self.species='Picea abies'
        self.latitude = latitude
        self.H100 = H100
        self.dominantHeight=dominantHeight
        self.InitStems = InitStems
        self.stems = exp(0.168 + -0.038*log(self.dominantHeight) + 0.989*log(self.InitStems))
        self.TotalVolume = self.getTotalVolume()
        self.HL = exp(0.759 + 0.832*log(dominantHeight) - 0.054*log(InitStems)) #f.2
        
        self.FormHeight = exp(0.830 + 0.737*log(dominantHeight) + -0.113*log(InitStems))
        self.TotalBA = self.TotalVolume/self.FormHeight # Fh = V / BA
        self.BA = exp((log(self.TotalBA) - 0.044)/0.980)
        self.QMD = self.getQMD(self.BA,self.stems)
        
        self.DGV = exp(0.194 + 0.129*log(dominantHeight) + 0.824*log(self.QMD)) #Spruce PCT
        
        self.D800 =  exp(0.676 + 0.352 * log(self.dominantHeight) + 0.452 * log(self.QMD)) #Spruce PCT
        
        self.D400 = exp(0.591 + 0.387 * log(self.QMD) + 0.482 * log(self.dominantHeight)) #Spruce PCT
        
        self.D100 = exp(0.605 + 0.441 * log(self.QMD) + 0.463 * log(self.dominantHeight)) #Spruce PCT
        self.VolDistrMean =exp(0.5271 + 0.8418*log(self.QMD))
        self.VolDistrStd = exp(2.1613 + 0.4634*log(self.QMD) - 0.6656*log(self.H100))
        self.VolDistrSkew = exp(0.9021 + 0.1278*log(self.saplingsPlanted)-0.2647*log(self.H100)) - 3
        self.VolDistrKurtosis = exp(1.2019-0.1900*log(self.saplingsPlanted)+0.4445*log(self.H100)) - 3

        def eqSystem(variables):
            a, b = variables
            f1 = (self.D100/(a+b*self.D100))**2 + 1.3 - self.dominantHeight
            f2 = (self.QMD/(a+b*self.QMD))**2 + 1.3 - self.HL
            return [f1,f2]
        initial_guess = [1,1]

        self.HD_a, self.HD_b = fsolve(eqSystem,initial_guess)

    def getTotalVolume(self):
        if self.H100<=30:
            a = 1000
            b = -2.331
            aP = 0.259
            bP = -1.537
        else:
            a = 1000
            b = -2.488
            aP = 1.066
            bP = -2.098
        
        return (self.InitStems/(a*(self.dominantHeight**b)+self.InitStems*aP*(self.dominantHeight**bP)))


    def getHeightofDiameter(self,Diameter):
        return (Diameter/(self.HD_a+self.HD_b*Diameter))**3 + 1.3 #Petterson 1955
    

    def getVolumeDistribution(self,class_middle):
        return self.cramerNormalPDF(x=class_middle,mean=self.VolDistrMean,sd=self.VolDistrStd,skew=self.VolDistrSkew,kurtosis=self.VolDistrKurtosis,total=self.TotalVolume)
    
    def ViewVolumeDistribution(self,start=1.5,stop=30,Percentage=True):
        Diameters = np.linspace(start,stop,2000)
        if Percentage:
            Percent = [element / self.TotalVolume for element in [self.getVolumeDistribution(class_middle=diameter) for diameter in Diameters]]
        else:
            Percent = [self.getVolumeDistribution(class_middle=diameter) for diameter in Diameters]
        #integ = integrate.quad(self.getVolumeDistribution,0,40)[0]
        plt.plot(Diameters,Percent)
        plt.xlabel("Diameter Class, cm")
        if Percentage:
            plt.ylabel("Percent of Volume")
        else:
            plt.ylabel('Volume')
        plt.title(f"Planted Spruce H100:{round(self.H100,1)} m, BA:{round(self.BA,1)}$m^2$,\nDominant height: {round(self.dominantHeight,1)} m")
        plt.show()

    def findStemDistribution(self,minD=None,minPercent=0,maxPercent=0,classes=200):
        #Find diameter of minimum class
        if minD is None:
            minD = minimize(lambda x: abs(minPercent - integrate.quad(self.getVolumeDistribution,0,x)[0]/self.TotalVolume),x0=0.1,bounds = [(0.0,self.QMD)]).x
        
        #Maximum class
        maxD = minimize(lambda x: abs(maxPercent - integrate.quad(self.getVolumeDistribution,x,self.QMD+60)[0]/self.TotalVolume),x0=self.QMD,bounds = [(self.QMD,self.QMD+60)]).x

        Diameters = np.linspace(minD,maxD,classes)
        HalfClassWidth = (maxD-minD)/(classes*2)

        classVolumes = np.array([integrate.quad(self.getVolumeDistribution,val-HalfClassWidth,val+HalfClassWidth)[0] for val in Diameters])

        Heights = np.array([self.getHeightofDiameter(diameter) for diameter in Diameters])

        Volumes = np.array([self.getVolumeSpruce(latitude=self.latitude,height=height,diameter=diameter) for height, diameter in zip(Heights, Diameters)])/1000

        return Diameters, classVolumes/Volumes

    def ViewStemDistribution(self,minD=None,minPercent=2,maxPercent=0,classes=200,Percentage=True):
        Diameter, stems = self.findStemDistribution(minD=minD,minPercent=minPercent,maxPercent=maxPercent,classes=classes)
        Diameter = Diameter.flatten()
        if Percentage:
            plt.bar(Diameter.flatten(),height=(stems*100)/sum(stems))
        else:
            plt.bar(Diameter.flatten(),stems)
        plt.xlabel("Diameter Class, cm")
        if Percentage:
            plt.ylabel("Percent of Stems")
        else:
            plt.ylabel('Stems')
        plt.suptitle(f"Planted Spruce H100:{round(self.H100,1)} m, BA:{round(self.BA,1)}$m^2$ \nDominant height:{round(self.dominantHeight,1)} m")
        plt.title(f"Function stems:{round(self.stems,1)}, Sum from Volume Distribution:{round(sum(stems),1)}")
        plt.show()      


    def generateStems(self):
        return self.sample(n=self.stems,distr=self.getVolumeDistribution)
        

class PCTPine (Pettersson1992):
    def __init__(self, H100, dominantHeight=14, latitude=64, InitStems=5000):
        self.species='Pinus sylvestris'
        self.latitude = latitude
        self.H100 = H100
        self.dominantHeight=dominantHeight
        self.InitStems = InitStems
        self.stems = exp(0.460 + -0.050*log(dominantHeight) + 0.953*log(InitStems))
        if latitude <= 60:
            self.FormHeight = exp(-0.516 + 0.857*log(dominantHeight) + 0.004*log(InitStems))
        else: 
            self.FormHeight = exp(-0.460 + 0.857*log(dominantHeight) + 0.004*log(InitStems))
        
        self.HL = exp(0.109 + 1.009*log(dominantHeight) - 0.028*log(InitStems))
        self.TotalVolume = self.getTotalVolume()
        
        self.TotalBA = self.TotalVolume/self.FormHeight #Fh = V / BA
        self.BA = exp((log(self.TotalBA) - 0.063)/0.973)
        
        self.QMD = self.getQMD(self.BA,self.stems)
        self.DGV = exp(0.296+0.140*log(dominantHeight)+0.777*log(self.QMD)) #Pine PCT
        self.D800 = exp(0.751 + 0.281*log(dominantHeight)+0.502*log(self.QMD))
        self.D400 = exp(0.756 + 0.339*log(dominantHeight) + 0.472*log(self.QMD))
        self.D100 = exp(0.858 + 0.351*log(dominantHeight) + 0.459*log(self.QMD))
        self.VolDistrMean = exp(0.517 + 0.836*log(self.QMD))
        self.VolDistrStd = exp(-1.346 + 0.707*log(dominantHeight) + 0.073*log(InitStems))
        self.VolDistrSkew = exp(-1.071 + 0.264*log(self.InitStems)) -3
        self.VolDistrKurtosis = exp(3.154 + -0.492*log(dominantHeight) + -0.105*log(InitStems)) -3

        def eqSystem(variables):
            a, b = variables
            f1 = (self.D100/(a+b*self.D100))**2 + 1.3 - self.dominantHeight
            f2 = (self.QMD/(a+b*self.QMD))**2 + 1.3 - self.HL
            return [f1,f2]
        initial_guess = [1,1]

        self.HD_a, self.HD_b = fsolve(eqSystem,initial_guess)
    
    def getTotalVolume(self):
        if self.H100 <= 25:
            a = 83.1
            b = -1.310
            aP = 0.918
            bP = -2.036
        else:
            a = 3422
            b = -3.130
            aP = 0.445
            bP = -1.765
        return self.InitStems/(a*(self.dominantHeight**b)+self.stems*aP*(self.dominantHeight**bP))


    def getHeightofDiameter(self,Diameter): #Näslund 1936
        return (Diameter/(self.HD_a+self.HD_b*Diameter))**2 + 1.3

    def getVolumeDistribution(self,class_middle):
        return self.cramerNormalPDF(x=class_middle,mean=self.VolDistrMean,sd=self.VolDistrStd,skew=self.VolDistrSkew,kurtosis=self.VolDistrKurtosis,total=self.TotalVolume)
    
    def ViewVolumeDistribution(self,start=0,stop=30,Percentage=True):
        Diameters = np.linspace(start,stop,2000)
        if Percentage:
            Percent = [element / self.TotalVolume for element in [self.getVolumeDistribution(class_middle=diameter) for diameter in Diameters]]
        else:
            Percent = [self.getVolumeDistribution(class_middle=diameter) for diameter in Diameters]
        #integ = integrate.quad(self.getVolumeDistribution,0,40)[0]
        plt.plot(Diameters,Percent)
        plt.xlabel("Diameter Class, cm")
        if Percentage:
            plt.ylabel("Percent of Volume")
        else:
            plt.ylabel('Volume')
        plt.title(f"Planted Pine H100:{round(self.H100,1)} m, BA:{round(self.BA,1)}$m^2$ \nDominant height:{round(self.dominantHeight,1)} m")
        plt.show()

    def findStemDistribution(self,minD=None,minPercent=0,maxPercent=0,classes=200):
        #Find diameter of minimum class
        if minD is None:
            minD = minimize(lambda x: abs(minPercent - integrate.quad(self.getVolumeDistribution,0,x)[0]/self.TotalVolume),x0=0.1,bounds = [(0.0,self.QMD)]).x
        
        #Maximum class
        maxD = minimize(lambda x: abs(maxPercent - integrate.quad(self.getVolumeDistribution,x,self.QMD+60)[0]/self.TotalVolume),x0=self.QMD,bounds = [(self.QMD,self.QMD+60)]).x

        Diameters = np.linspace(minD,maxD,classes)
        HalfClassWidth = (maxD-minD)/(classes*2)

        classVolumes = np.array([integrate.quad(self.getVolumeDistribution,val-HalfClassWidth,val+HalfClassWidth)[0] for val in Diameters])

        Heights = np.array([self.getHeightofDiameter(diameter) for diameter in Diameters])

        Volumes = np.array([self.getVolumePine(latitude=self.latitude,height=height,diameter=diameter) for height, diameter in zip(Heights, Diameters)])/1000

        return Diameters, classVolumes/Volumes

    def ViewStemDistribution(self,minD=None,minPercent=2,maxPercent=0,classes=200,Percentage=True):
        Diameter, stems = self.findStemDistribution(minD=minD,minPercent=minPercent,maxPercent=maxPercent,classes=classes)
        Diameter = Diameter.flatten()
        if Percentage:
            plt.bar(Diameter.flatten(),height=(stems*100)/sum(stems))
        else:
            plt.bar(Diameter.flatten(),stems)
        plt.xlabel("Diameter Class, cm")
        if Percentage:
            plt.ylabel("Percent of Stems")
        else:
            plt.ylabel('Stems')
        plt.suptitle(f"Planted Pine H100:{round(self.H100,1)} m, BA:{round(self.BA,1)}$m^2$ \nDominant height:{round(self.dominantHeight,1)} m")
        plt.title(f"Function stems:{round(self.stems,1)}, Sum from Volume Distribution:{round(sum(stems),1)}")
        plt.show()


### TESTS ###
Spruce1 = PlantedSpruce(H100=24,dominantHeight=12,saplingSquareSpacingM=1)
print(Spruce1.TotalVolume)
print(Spruce1.QMD)
print(Spruce1.HL)
Spruce1.ViewVolumeDistribution(Percentage=True)
Spruce1.ViewStemDistribution(minD=4.5, classes=30, Percentage=True)

Spruce1 = PlantedPine(H100=24,dominantHeight=12,saplingSquareSpacingM=1)
print(Spruce1.TotalVolume)
print(Spruce1.QMD)
print(Spruce1.HL)
Spruce1.ViewVolumeDistribution(Percentage=True)
Spruce1.ViewStemDistribution(minD=4.5, classes=30, Percentage=True)

Spruce1 = PCTPine(H100=24,dominantHeight=12,InitStems=7500)
print(Spruce1.TotalVolume)
print(Spruce1.QMD)
print(Spruce1.HL)
Spruce1.ViewVolumeDistribution(Percentage=True)
Spruce1.ViewStemDistribution(minD=4.5, classes=30, Percentage=True)

Spruce1 = PCTSpruce(H100=24,dominantHeight=12,InitStems=7500)
print(Spruce1.TotalVolume)
print(Spruce1.QMD)
print(Spruce1.HL)
Spruce1.ViewVolumeDistribution(Percentage=True)
Spruce1.ViewStemDistribution(minD=4.5, classes=30, Percentage=True)
######