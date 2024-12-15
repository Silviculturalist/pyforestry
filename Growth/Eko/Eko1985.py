# Growth Model Ekö 
# Version 0.8 Carl Vigren 2024-12-15


import numpy as np
from math import pi, exp, log, log10, sqrt
import warnings


class EkoStandSite:
    def __init__(self, latitude, altitude, vegetation, soil_moisture, H100_Spruce, region='South', H100_Pine=None, fertilised=False, thinned_5y=False, thinned=False, TAX77=False):
        '''
        Vegetation Codes: 1-6 Herbs, 7 No Field Layer, 8-9 Grasses, 13 Bilberry, 14 Cowberry.
        Soil moisture Codes: 1 for Dry or Very Dry, 5 for wet or very wet.
        H100 Spruce, H100 Pine is Hägglund Site Index 1972,1973,1974.
        Region: string, 'North','Central','South'.
        '''
        if region in ('North','Central','South'):
            self.region = region
        else:
            raise ValueError(f"Region must be one of 'North','Central','South', not: '{region}'.")

        if H100_Spruce is None and H100_Pine is None:
            raise ValueError("At least one of H100_Spruce or H100_Pine must be provided")
        
        elif H100_Pine is None and H100_Spruce is not None:
            self.H100_Spruce = H100_Spruce
            self.H100_Pine = self.__Leijon_Spruce_to_Pine(H100_Spruce)
        
        elif H100_Pine is not None and H100_Spruce is None:
            self.H100_Pine = H100_Pine
            self.H100_Spruce = self.__Leijon_Pine_to_Spruce(H100_Pine)
        
        self.TAX77 = TAX77

        #Set FieldLayer
        if vegetation==13 or vegetation==14:
            self.Bilberry_or_Cowberry = True
            self.HerbsGrassesNoFieldLayer = False
        elif vegetation in [1,2,3,4,5,6,8,9]:
            self.Bilberry_or_Cowberry = False
            self.HerbsGrassesNoFieldLayer = True
        elif vegetation==7 and latitude<60:
            self.Bilberry_or_Cowberry = False
            self.HerbsGrassesNoFieldLayer = True
        
        #Set soil moisture
        if soil_moisture==1:
            self.DrySoil = True 
            self.WetSoil = False
        elif soil_moisture==5:
            self.DrySoil = False
            self.WetSoil = True
        else:
            self.DrySoil=False
            self.WetSoil=False

        self.altitude= altitude
        self.latitude = latitude

        self.fertilised = fertilised
        self.thinned=thinned
        if thinned_5y==True:
            self.thinned_5y = thinned_5y
            self.thinned= True
        else:
            self.thinned_5y = False

        match vegetation:
            case 1:
                self.vegcode = 4
            case 2:
                self.vegcode = 2.5
            case 3:
                self.vegcode = 2
            case 4:
                self.vegcode = 3
            case 5:
                self.vegcode = 2.5
            case 6:
                self.vegcode = 2
            case 7:
                self.vegcode = 3
            case 8:
                self.vegcode = 2.5
            case 9:
                self.vegcode = 1.5
            case 10:
                self.vegcode = -3
            case 11:
                self.vegcode = -3
            case 12:
                self.vegcode = 1
            case 13:
                self.vegcode = 0
            case 14:
                self.vegcode = -0.5
            case 15:
                self.vegcode = -3
            case 16:
                self.vegcode = -5
            case 17:
                self.vegcode = -0.5
            case 18:
                self.vegcode =-1
                


   

               

    @staticmethod
    def __Leijon_Pine_to_Spruce(H100_Pine):
        '''
        Leijon 1979 function 7.2.
        '''
        if H100_Pine <8 or H100_Pine>30:
            warnings.warn("SI Pine may be outside underlying material")
        
        return exp(-0.9596*log(H100_Pine*10)+
            +0.01171*(H100_Pine*10)+
            +7.9209 #approximately corrected for logarithmic bias.
            )/10

    @staticmethod    
    def __Leijon_Spruce_to_Pine(H100_Spruce):
        '''
        Leijon 1979 function 7.1.
        '''
        if H100_Spruce<8 or H100_Spruce>33:
            warnings.warn("SI Spruce may be outside underlying material.")

        return exp(
            1.6967*log(H100_Spruce*10)+
            -0.005179*(H100_Spruce*10)+
            -2.5397 #approximately corrected for logarithmic bias.
            )/10


#Holds several stands..
class EvenAgedStand:
   @staticmethod
   def getQMD(BA,stems):
      if stems == 0:
         return 0
      else:
        return sqrt((float(BA))/(((pi/4)/10E3)*float(stems)))
   @staticmethod
   def getMAI(Volume,TotalAge):
      return Volume/TotalAge
   
class EkoStand(EvenAgedStand):
    '''
    StandParts: list of objects of class EkoStandPart
    EkoSite: object of class EkoSite.
    '''
    def __init__(self,StandParts,EkoSite):
        if not all(isinstance(item, EkoStandPart) for item in StandParts):
            raise ValueError('All StandParts must be EkoStandPart objects!')
        self.Parts = StandParts
        if not isinstance(EkoSite,EkoStandSite):
            raise ValueError('Provided site must be a EkoStandSite object!')
        
        if any([isinstance(item,EkoBeech) for item in StandParts]) and EkoSite.region not in ('Central','South'):
            warnings.warn('Setting Beech stand outside of southern Sweden!')

        if any([isinstance(item,EkoOak) for item in StandParts]) and EkoSite.region not in ('Central','South'):
            warnings.warn('Setting Oak stand outside of southern Sweden!')

        self.Site = EkoSite
        for i in self.Parts:
            i.register_stand(self)

        for i in self.Parts:
            i.BAOtherSpecies = sum([j.BA for j in self.Parts if j is not i])
            i.QMDOtherSpecies = self.getQMD(i.BAOtherSpecies,sum([j.stems for j in self.Parts if j is not i]))
            i.HK = (i.QMDOtherSpecies/i.QMD)*i.BAOtherSpecies

        for i in self.Parts:
            i.VOL=i.getVolume(BA=i.BA,QMD=i.QMD,age=i.age,stems=i.stems,HK=i.HK)

        self.StandBA = sum([i.BA for i in self.Parts])
        self.StandVOL = sum([i.VOL for i in self.Parts])
        self.StandStems = sum([i.stems for i in self.Parts])

    def grow5(self,mortality=True):
        for i in self.Parts:
            if mortality:
                BAQcrowding,i.QMD_Mortality_Crowding,BAQother, i.QMD_Mortality_Other = i.getMortality(increment=5)
                i.getBAI5(ba_quotient_chronic_mortality=BAQcrowding/i.BA,ba_quotient_acute_mortality=BAQcrowding/i.BA)
                i.BA_Mortality = (BAQcrowding+BAQother)#*i.BA
                i.stems_Mortality = BAQother/(pi*((i.QMD_Mortality_Other/200)**2))+BAQcrowding/(pi*((i.QMD_Mortality_Crowding/200)**2))
            else:
                i.getBAI5(ba_quotient_chronic_mortality=0,ba_quotient_acute_mortality=0)
                i.BA_Mortality = 0
                i.QMD_Mortality = 0
                i.stems_Mortality = 0
            
            i.BA1 = i.BA+i.BAI5
            i.age2 = i.age + 5

            #Thinning performd before this function.
            #Placeholders below
            i.BA_Thinned = 0
            i.stems_Thinned = 0
            i.QMD_Thinned = 0


            ## Get volume
        for i in self.Parts:
            #Gross changes
            i.BAOtherSpecies1 = sum([j.BA1 for j in self.Parts if j is not i]) #Sum unreduced BA growth for other parts
            i.QMDOtherSpecies1 = self.getQMD(i.BAOtherSpecies1,sum([j.stems for j in self.Parts if j is not i])) #QMD given unhindered BA growth and no stem removal due to self-thinning
            i.QMD1 = i.getQMD(i.BA1,i.stems) #QMD given unhindered BA growth and no stem removals for part of interest.
            i.HK1 = (i.QMDOtherSpecies1/i.QMD1)*i.BAOtherSpecies1 #HK competition given above.
            i.VOL1 = i.getVolume(BA=i.BA1,QMD=i.QMD1,age=i.age2,stems=i.stems,HK=i.HK1) #Gross volume (before any removals)

            #Gross change - self-thinning
            i.BAOtherSpecies2 = sum([j.BA1-j.BA_Mortality for j in self.Parts if j is not i]) #Sum Net BA growth for other parts
            i.QMDOtherSpecies2 = self.getQMD(i.BAOtherSpecies2,sum([j.stems-j.stems_Mortality] for j in self.Parts if j is not i)) #Net QMD of other parts with reduced BA and removed stems. 
            i.QMD2 = i.getQMD(i.BA1-i.BA_Mortality,i.stems-i.stems_Mortality) #QMD for part of interest given BA  and stem Mortality.
            i.HK2 = (i.QMDOtherSpecies2/i.QMD2)*i.BAOtherSpecies2 #HK dito.
            i.VOL2 = i.getVolume(BA=i.BA1-i.BA_Mortality,QMD=i.QMD2,age=i.age2,stems=i.stems-i.stems_Mortality,HK=i.HK2)
            i.Vol_Mortality = i.VOL2-i.VOL1 #Self-thinned volume is raw growth - growth after removals.
            #BA mortality, was calculated at start as proportion of standing BA at period start.


#           #Gross change - thinning
#           i.BAOtherSpecies4 = sum([j.BA2-j.BA_Thinned for j in self.Parts if j is not i]) #Sum Net BA growth for other parts
#           i.QMDOtherSpecies4 = self.getQMD(i.BAOtherSpecies4,sum([j.stems-j.stems_Thinned] for j in self.Parts if j is not i)) #Net QMD of other parts with reduced BA and thinned stems.
#           i.QMD4 = i.getQMD(i.BA2-i.BA_Thinned,i.stems-i.stems_Thinned) #QMD for part of interest given BA and stem removal.
#           i.HK4 = (i.QMDOtherSpecies4/i.QMD4)*i.BAOtherSpecies4 #HK dito.
#           i.VOL4 = i.getVolume(BA=i.BA2-i.BA_Thinned,QMD=i.QMD4,age=i.age2,stems=i.stems-i.stems_Thinned,HK=i.HK4)
#           i.Vol_Thinned = i.VOL2-i.VOL4 #Self-thinned volume is gross growth - growth after removals.
            #BA thinned, was calculated before function during registration of thinning.

            #Net change (Gross - self-thinning - thinning)
            #State at end-of-period
#            i.Volume_Net = i.getVolume(BA=i.BA2-i.BA_Mortality,QMD=i.getQMD(i.BA2-i.BA_Mortality,i.stems3),age=i.age2,stems=i.stems3,HK=i.HK3) 
#            i.stems_Net = i.stems-i.stems_Mortality - i.stems_Thinned
#            i.BA_Net = i.BA2-i.BA_Mortality - i.BA_Thinned
#            i.QMD_Net = i.getQMD(i.BA_Net,i.stems_Net)



            
            
      
class EkoStandPart(EvenAgedStand):
    def __init__(self,ba,stems,age):
        self.stand= None
        self.BA = ba
        self.stems = stems
        self.age = age
        self.QMDOtherSpecies=0
        self.BAOtherSpecies=0
        self.ba_quotient_acute_mortality = 0
        self.QMD = self.getQMD(self.BA,self.stems)

    def register_stand(self,stand):
        self.stand = stand
   

class EkoSpruce(EkoStandPart):
    def __init__(self,ba,stems,age):
        super().__init__(ba,stems,age)

    def getMortality(self,increment=5):
        '''
        Gets Chronic and acute mortality according to Bengtsson, G. 1981. Handwritten note.
        Returns four values, proportion BA that will die during the coming increment and QMD of such due to crowding, and due to other factors.
        '''


        if self.stand.Site.region == 'North' or self.stand.Site.region == 'Central':
            if (self.age//10)+1 < 17:
                AKL = (self.age//10)+1 # // is floor division
            else:
                AKL = 17
            crowding = (-0.2748E-02+0.4493E-03*self.BA+0.2515E-04*self.BA**2)#*increment/100
            other = -0.3150E-03+0.3337E-01*AKL
        else:
            if self.stems>2800:
                stems2 = 2800
            else: 
                stems2 = self.stems
            
            crowding = (0.1235E-01+-0.2749E-02*self.BA+0.8214E-04*self.BA**2+0.2457E-04*stems2+-0.4498E-08*stems2**2)#*increment/100
            other= 0.36

        if crowding > 1:
            crowding = 1
        elif crowding < 0:
            crowding = 0
        
        return crowding, 0.9*self.QMD, other, self.QMD
        
    
    def getVolume(self,BA=None,QMD=None,age=None,stems=None,HK=None):
        if self.stand is None:
            raise ValueError('Volume calculator cannot be called before EkoStandPart object is connected to an EkoStand object together with an EkoStandSite object!')
        
        SIdm = self.stand.Site.H100_Spruce * 10
        
        if self.stand.Site.region == 'North':
            b1 =  -0.065
            b2 =  -2.05
            F4age = (1 - exp(b1*age))
            F4basal_area = (1- exp(b2*BA))
            
            lnVolume = (
                +0.362521E-02*BA+
                +1.35682*log(BA)+
                -1.47258*QMD+
                -0.438770*F4basal_area+
                +1.46910*F4age+
                -0.314730*log(stems)+
                +0.228700*log(SIdm)+
                +0.118700E-01*self.stand.Site.thinned+
                +0.254896E-02*HK+
                +1.970094
            )

            return exp(lnVolume + 0.0388)

        elif self.stand.Site.region == 'Central':
           b1 =  -0.065
           b2 =  -2.05
           
           F4age = (1 - exp(b1*age))
           F4basal_area = (1- exp(b2*BA))
           
           lnVolume = (
               +1.28359*log(BA)+
               -0.380690*F4basal_area+
               +1.21756*F4age+
               -0.216690*log(stems)+
               +0.350370*log(SIdm)+
               +0.413000E-01*self.stand.Site.HerbsGrassesNoFieldLayer+
               +0.362100E-01*self.stand.Site.thinned+
               +0.268645E-02*HK+
               +0.700490
           )

           return  exp( lnVolume + 0.0563)
        
        else:
            b1 =  -0.04
            b2 =  -2.05
            F4age = (1 - exp(b1*age))
            F4basal_area = (1- exp(b2*BA))
            lnVolume = (
                +1.22886*log(BA)+
                -0.349820*F4basal_area+
                +0.485170*F4age+
                -0.152050*log(stems)+
                +0.337640*log(SIdm)+
                +0.129800E-01*self.stand.Site.thinned+
                +0.548055E-03*HK+
                +0.584600
            )

            return  exp(lnVolume + 0.0325)
        
    def getBAI5(self,ba_quotient_chronic_mortality=0,ba_quotient_acute_mortality=0):
        if self.stand is None:
            raise ValueError('Basal Area increment calculator cannot be called before EkoStandPart object is connected to an EkoStand object together with an EkoStandSite object!')
        
        SIdm = self.stand.Site.H100_Spruce * 10
        
        if self.stand.Site.region == 'North':

            independent_vars = (
                -0.767477*ba_quotient_chronic_mortality+
                -0.514297*ba_quotient_acute_mortality+
                -1.43974*self.QMD+
                -0.386338E-02*self.HK+
                +0.204732*self.stand.Site.fertilised+
                +0.186343*self.stand.Site.vegcode+
                +0.392021E-01*self.stand.Site.Bilberry_or_Cowberry+
                -0.807207E-01*self.stand.Site.DrySoil+
                +0.833252
            )

            if SIdm<160:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.736655E-02*self.BA+
                        +0.875788*log(self.BA)+
                        -0.642060E-04*self.stems+
                        +0.125396*log(self.stems)+
                        +0.159356E-02*self.age+
                        -0.764340*log(self.age)+
                        -0.594334E-02*self.BAOtherSpecies
                    )
                else:
                    dependent_vars = (
                        -0.187226E-01*self.BA+
                        +0.855970*log(self.BA)+
                        +0.106942E-03*self.stems+
                        +0.107612*log(self.stems)+
                        +0.321033E-02*self.age+
                        -0.737062*log(self.age)+
                        -0.206053E-01*self.BAOtherSpecies
                    )
            elif SIdm<200:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.191493E-01*self.BA+
                        +0.942389*log(self.BA)+
                        -0.145476E-03*self.stems+
                        +0.158511*log(self.stems)+
                        +0.289628E-02*self.age+
                        -0.804217*log(self.age)+
                        -0.125949E-01*self.BAOtherSpecies
                    )
                else:
                    dependent_vars = (
                        -0.255254E-01*self.BA+
                        +0.955380*log(self.BA)+
                        -0.642149E-04*self.stems+
                        +0.164265*log(self.stems)+
                        +0.554025E-02*self.age+
                        -0.866520*log(self.age)+
                        -0.889755E-02*self.BAOtherSpecies
                    )

            else:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.210737E-01*self.BA+
                        +0.932275*log(self.BA)+
                        -0.572335E-04*self.stems+
                        +0.152017*log(self.stems)+
                        +0.342622E-02*self.age+
                        -0.811183*log(self.age)+
                        -0.905176E-02*self.BAOtherSpecies
                    )
                else : 
                    dependent_vars = (
                        -0.133941E-01*self.BA+
                        +0.837783*log(self.BA)+
                        -0.245946E-03*self.stems+
                        +0.205142*log(self.stems)+
                        +0.602419E-02*self.age+
                        -0.862195*log(self.age)+
                        -0.135941E-01*self.BAOtherSpecies
                    )

                self.BAI5 = exp(dependent_vars + independent_vars + 0.0564)



        elif self.stand.Site.region == 'Central':
            independent_vars = (
                -1.16597*ba_quotient_chronic_mortality+
                -0.299327*ba_quotient_acute_mortality+
                +0.783806E-01*self.stand.Site.thinned_5y+
                +0.572131E-01*self.stand.Site.vegcode+
                -0.112938E-01*self.stand.Site.WetSoil+ #Typo in book. No number or sign after E. Assuming -1.
                +0.546176E-01*self.stand.Site.latitude+
                +0.332621E-01*self.stand.Site.TAX77
            )

            
            if SIdm<180:
                if not self.stand.Site.thinned:
                
                    dependent_vars = (
                        -0.802837E-02*self.BA+
                        +0.751220*log(self.BA)+
                        -0.800241E-04*self.stems+
                        +0.239814*log(self.stems)+
                        -0.148757E-02*self.age+
                        -0.476534*log(self.age)+
                        -0.308451E-01*self.BAOtherSpecies+
                        -4.02484
                    )
                else:
                    dependent_vars = (
                        -0.330623E-01*self.BA+
                        +1.06539*log(self.BA)+
                        +0.145290E-03*self.stems+
                        +0.422450E-01*log(self.stems)+
                        +0.110998E-01*self.age+
                        -1.71468*log(self.age)+
                        -0.236447E-01*self.BAOtherSpecies+
                        +1.06383
                    )
            
            elif SIdm<220:
                if not self.stand.Site.thinned:
                    
                    dependent_vars = (
                        -0.211171E-01*self.BA+
                        +0.837241*log(self.BA)+
                        -0.800241E-04*self.stems+
                        +0.239814*log(self.stems)+
                        +0.492578E-02*self.age+
                        -0.839650*log(self.age)+
                        -0.269523E-02*self.BAOtherSpecies+
                        -2.91926
                    )

                else:
                    dependent_vars = (
                        -0.180419E-01*self.BA+
                        +0.943986*log(self.BA)+
                        +0.145290E-03*self.stems+
                        +0.422450E-01*log(self.stems)+
                        +0.525585E-02*self.age+
                        -0.982261*log(self.age)+
                        -0.786807E-02*self.BAOtherSpecies+
                        -1.56544
                    )
        
            elif SIdm<260:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.263745E-01*self.BA+
                        +0.915196*log(self.BA)+
                        -0.800241E-04*self.stems+
                        +0.239814*log(self.stems)+
                        -0.384471E-02*self.age+
                        -0.847753*log(self.age)+
                        -0.252559E-01*self.BAOtherSpecies+
                        +2.85518
                    )
                else:
                    dependent_vars = (
                        -0.217674E-01*self.BA+
                        +0.847682*log(self.BA)+
                        -0.145290E-03*self.stems+
                        +0.422450E-01*log(self.stems)+
                        +0.101626E-01*self.age+
                        -1.37782*log(self.age)+
                        -0.268779E-01*self.BAOtherSpecies+
                        +0.178428

                    )
            
            else:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.244742E-01*self.BA+
                        +0.787195*log(self.BA)+
                        -0.800241E-04*self.stems+
                        +0.239814*log(self.stems)+
                        +0.371613E-02*self.age+
                        -0.561641*log(self.age)+
                        -0.298097E-01*self.BAOtherSpecies+
                        -3.17570
                    )

                else:
                    dependent_vars = (
                        -0.239679E-01*self.BA+
                        +0.924765*log(self.BA)+
                        +0.145290E-03*self.stems+
                        +0.422450E-01*log(self.stems)+
                        +0.631561E-03*self.age+
                        -0.893401*log(self.age)+
                        -0.908286E-02*self.BAOtherSpecies+
                        -1.46143
                    )


            self.BAI5 = exp(dependent_vars + independent_vars + 0.0712)

        else:
            
            independent_vars = (
                        -0.780391*ba_quotient_chronic_mortality+
                        -0.252170*ba_quotient_acute_mortality+
                        -0.318464E-01*self.stand.Site.thinned_5y+
                        +0.778093E-01 *self.stand.Site.fertilised+
                        +0.127135E-02*SIdm+
                        +0.262484E-01*self.stand.Site.vegcode+
                        -0.736690E-01*self.stand.Site.DrySoil+
                        -0.269193E-01*self.stand.Site.latitude+
                        -0.959785E-01*self.stand.Site.TAX77
            )

            if SIdm<220:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.149200E-01*self.BA+
                        +0.794859*log(self.BA)+
                        -0.120956E-03*self.stems+
                        +0.255053*log(self.stems)+
                        -0.720252*log(self.age)+
                        -0.229139E-01*self.BAOtherSpecies+
                        +1.52732
                    )
                else:
                    dependent_vars = (
                        -0.227763E-01*self.BA+
                        +0.838105*log(self.BA)+
                        +0.519813E-03*self.stems+
                        +0.141232*log(self.stems)+
                        -0.722723*log(self.age)+
                        -0.237689E-01*self.BAOtherSpecies+
                        +1.93218
                    )
            elif SIdm<260:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.167127E-01*self.BA+
                        +0.794738*log(self.BA)+
                        -0.923244E-04*self.stems+
                        +0.279717*log(self.stems)+
                        -0.790588*log(self.age)+
                        -0.187801E-01*self.BAOtherSpecies+
                        +1.67230
                    )

                else:
                    dependent_vars = (
                        -0.167448E-01*self.BA+
                        +0.835811*log(self.BA)+
                        -0.995431E-04*self.stems+
                        +0.258612*log(self.stems)+
                        -0.931549*log(self.age)+
                        -0.167010E-01*self.BAOtherSpecies+
                        +2.34225 
                    )

            elif SIdm<300:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.221875E-01*self.BA+
                        +0.832287*log(self.BA)+
                        -0.110872E-03*self.stems+
                        +0.271386*log(self.stems)+
                        -0.735989*log(self.age)+
                        -0.196143E-01*self.BAOtherSpecies+
                        +1.50310
                    )
                else:
                    dependent_vars = (
                        -0.203970E-01*self.BA+
                        +0.836890*log(self.BA)+
                        -0.755155E-04*self.stems+
                        +0.248563*log(self.stems)+
                        -0.716504*log(self.age)+
                        -0.151436E-01*self.BAOtherSpecies+
                        +1.50719
                    )
                
            else:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.243263E-01*self.BA+
                        +0.902730*log(self.BA)+
                        -0.706319E-04*self.stems+
                        +0.198283*log(self.stems)+
                        -0.713230*log(self.age)+
                        -0.135840E-01*self.BAOtherSpecies+
                        +1.71136
                    )
                else:
                    dependent_vars = (
                        -0.218319E-01*self.BA+
                        +0.855200*log(self.BA)+
                        -0.176554E-03*self.stems+
                        +0.269091*log(self.stems)+
                        -0.765104*log(self.age)+
                        -0.180257E-01*self.BAOtherSpecies+
                        +1.62508
                    )
            
            self.BAI5 = exp(dependent_vars + independent_vars + 0.0737)
           
class EkoPine(EkoStandPart):
    def __init__(self,ba,stems,age):
        super().__init__(ba,stems,age)
    
    def getMortality(self,increment=5):

        if self.stand.Site.region == 'North' or self.stand.Site.region=='Central':
            if self.stems>2700:
                stems2=2700
            else:
                stems2=self.stems
            
            crowding = (0.3143E-01+-0.6877E-02*self.BA+0.2056E-03*self.BA**2+0.2684E-04*stems2+-0.5092E-08*stems2**2)*increment/100
            other=0.35
        else:
            if self.stems>4000:
                stems2= 4000
            else:
                stems2=self.stems
            
            crowding = (-0.6766E-01+-0.1283E-02*self.BA+0.7748E-04*self.BA**2+0.1441E-03*stems2+-0.1839E-07*stems2**2)*increment/100
            other=0.38

        if crowding > 1:
            crowding = 1
        elif crowding < 0:
            crowding = 0
        
        return crowding, 0.9*self.QMD, other, self.QMD
        

    def getVolume(self,BA=None,QMD=None,age=None,stems=None,HK=None):
        if self.stand is None:
            raise ValueError('Volume calculator cannot be called before EkoStandPart object is connected to an EkoStand object together with an EkoStandSite object!')
        
        SIdm = self.stand.Site.H100_Pine * 10
        
        if self.stand.Site.region == 'North':
            b1 = -0.06
            b2 =  -2.3

            F4age = (1 - exp(b1*age))
            F4basal_area = (1- exp(b2*BA))

            lnVolume = (
                +1.24296*log(BA)+
                -0.472530*F4basal_area+
                +1.05864*F4age+
                -0.170140*log(stems)+
                +0.247550*log(SIdm)+
                +0.213800E-01*self.stand.Site.thinned+
                +0.295300E-01*self.stand.Site.thinned_5y+
                +0.510332E-02*HK+
                +1.08339
            )

            return  exp( lnVolume + 0.0275)


        elif self.stand.Site.region == 'Central':
            b1 =  -0.06
            b2 =  -2.2
            F4age = (1 - exp(b1*age))
            F4basal_area = (1- exp(b2*BA))
            lnVolume = (
                +0.778157E-02*BA+
                +1.14159*log(BA)+
                +0.927460*F4age+
                -0.166730*log(stems)+
                +0.304900*log(SIdm)+
                +0.270200E-01*self.stand.Site.thinned+
                +0.292836E-02*HK+
                +0.910330
            )

            return  exp(lnVolume + 0.0273)
        
        else:
            b1 = -0.075
            b2 = -2.2

            F4age = (1 - exp(b1*age))
            F4basal_area = (1- exp(b2*BA))

            lnVolume = (
                +1.21272*log(BA)+
                -0.299900*F4basal_area+
                +1.01970*F4age+
                -0.172300*log(stems)+
                +0.369930*log(SIdm)+
                +1.65136*log(self.stand.Site.latitude)+
                +0.349200E-01*log(self.stand.Site.altitude)+
                -0.197100E-01*self.stand.Site.HerbsGrassesNoFieldLayer+
                +0.229100E-01*self.stand.Site.thinned+
                +0.526017E-02*HK+
                -6.46337
            )

            return  exp(lnVolume + 0.0260)
        
    def getBAI5(self,mortality=True):
        if self.stand is None:
            raise ValueError('Basal Area increment calculator cannot be called before EkoStandPart object is connected to an EkoStand object together with an EkoStandSite object!')
        
        SIdm = self.stand.Site.H100_Pine * 10
        if mortality:
            ba_quotient_chronic_mortality = self.getChronicMortality()
        else:
            ba_quotient_chronic_mortality = 0
        
        if self.stand.Site.region == 'North':

            independent_vars = (
                -0.598419*ba_quotient_chronic_mortality+
                -0.486198*self.ba_quotient_acute_mortality+
                -0.952624E-02*self.HK+
                +0.674527E-01*self.stand.Site.thinned_5y+
                +0.100135*self.stand.Site.vegcode+
                -0.104076*self.stand.Site.WetSoil+
                -0.329437E-01*log(self.stand.Site.altitude)+
                +0.526479E-01*self.stand.Site.TAX77+
                +0.164446
            )

            if SIdm<160:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.342051E-01*self.BA+
                        +0.757840*log(self.BA)+
                        -0.161442E-03*self.stems+
                        +0.367048*log(self.stems)+
                        +0.313386E-02*self.age+
                        -0.842335*log(self.age)+
                        -0.157312E-01*self.BAOtherSpecies
                    )
                else:
                    dependent_vars = (
                        -0.222808E-01*self.BA+
                        +0.707173*log(self.BA)+
                        -0.407064E-03*self.stems+
                        +0.386522*log(self.stems)+
                        +0.309020E-02*self.age+
                        -0.840856*log(self.age)+
                        -0.168721E-01*self.BAOtherSpecies
                    )
            elif SIdm<200:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.264194E-01*self.BA+
                        +0.759517*log(self.BA)+
                        -0.172838E-03*self.stems+
                        +0.354319*log(self.stems)+
                        +0.282339E-02*self.age+
                        -0.830969*log(self.age)+
                        -0.920265E-02*self.BAOtherSpecies
                    )
                else:
                    dependent_vars = (
                        -0.215557E-01*self.BA+
                        +0.678298*log(self.BA)+
                        -0.223194E-03*self.stems+
                        +0.345910*log(self.stems)+
                        +0.230893E-02*self.age+
                        -0.759426*log(self.age)+
                        -0.129081E-01*self.BAOtherSpecies
                    )

            else:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.242773E-01*self.BA+
                        +0.743286*log(self.BA)+
                        -0.127080E-03*self.stems+
                        +0.328240*log(self.stems)+
                        +0.203892E-02*self.age+
                        -0.756105*log(self.age)+
                        -0.136312E-01*self.BAOtherSpecies
                    )
                else : 
                    dependent_vars = (
                        -0.100435E-01*self.BA+
                        +0.659451*log(self.BA)+
                        -0.181913E-03*self.stems+
                        +0.369130*log(self.stems)+
                        +0.227817E-02*self.age+
                        -0.793134*log(self.age)+
                        -0.817145E-02*self.BAOtherSpecies
                    )

                self.BAI5 = exp(dependent_vars + independent_vars + 0.0645)



        elif self.stand.Site.region == 'Central':
            independent_vars = (
                -0.757422*ba_quotient_chronic_mortality+
                -0.819721*self.ba_quotient_acute_mortality+
                -0.156937E-01*self.HK+
                +0.657419E-01*self.stand.Site.fertilised+
                +0.208293E-02*SIdm+
                +0.393424E-01*self.stand.Site.vegcode+
                -0.787040E-01*self.stand.Site.DrySoil+
                +0.952773E-01*self.stand.Site.TAX77+
                -0.466279
            )

            
            if SIdm<180:
                if not self.stand.Site.thinned:
                
                    dependent_vars = (
                        -0.247769E-01*self.BA+
                        +0.739123*log(self.BA)+
                        -0.724080E-04*self.stems+
                        +0.307962*log(self.stems)+
                        +0.213813E-02*self.age+
                        -0.730167*log(self.age)+
                        -0.304936E-02*self.BAOtherSpecies
                    )
                else:
                    dependent_vars = (
                        -0.454216E-01*self.BA+
                        +0.967594*log(self.BA)+
                        +0.134748E-03*self.stems+
                        +0.106405*log(self.stems)+
                        +0.322181E-02*self.age+
                        -0.559074*log(self.age)+
                        -0.146382E-01*self.BAOtherSpecies
                    )
            
            elif SIdm<220:
                if not self.stand.Site.thinned:
                    
                    dependent_vars = (
                        -0.204976E-01*self.BA+
                        +0.710569*log(self.BA)+
                        -0.331436E-04*self.stems+
                        +0.318007*log(self.stems)+
                        +0.186999E-02*self.age+
                        -0.732359*log(self.age)+
                        -0.488064E-02*self.BAOtherSpecies 
                    )

                else:
                    dependent_vars = (
                        +0.144234E-01*self.BA+
                        +0.304194*log(self.BA)+
                        -0.111460E-02*self.stems+
                        +0.628499*log(self.stems)+
                        +0.545633E-02*self.age+
                        -0.977317*log(self.age)+
                        -0.126636E-01*self.BAOtherSpecies
                    )
        
            else:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.242132E-01*self.BA+
                        +0.746931*log(self.BA)+
                        -0.120517E-03*self.stems+
                        +0.327216*log(self.stems)+
                        +0.254795E-02*self.age+
                        -0.758639*log(self.age)+
                        -0.978754E-02*self.BAOtherSpecies
                    )
                else:
                    dependent_vars = (
                        -0.126617E-01*self.BA+
                        +0.599420*log(self.BA)+
                        -0.405408E-03*self.stems+
                        +0.472836*log(self.stems)+
                        +0.455547E-02*self.age+
                        -0.895734*log(self.age)+
                        -0.106365E-01*self.BAOtherSpecies

                    )

            self.BAI5 = exp(dependent_vars + independent_vars + 0.0507)

        else:
            
            independent_vars = (
                -1.04202*ba_quotient_chronic_mortality+
                -0.637943*self.ba_quotient_acute_mortality+
                -1.75160*self.QMD+
                -0.592599E-02*self.HK+ ## Assuming HKD is a typo and should be HK
                +0.637421E-01*self.stand.Site.thinned_5y+
                +0.462966E-01*self.stand.Site.fertilised+
                +0.522489E-01*self.stand.Site.vegcode+
                -0.702839E-01*self.stand.Site.DrySoil+
                -0.111568E-01*self.stand.Site.latitude+
                -0.466973E-01*self.stand.Site.TAX77
            )

            if SIdm<160:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.497800E-01*self.BA+
                        +1.19990*log(self.BA)+
                        +0.114548E-04*self.stems+
                        +0.164713*log(self.stems)+
                        -0.884162E-03*self.age+
                        -0.564604*log(self.age)+
                        -0.153879E-01*self.BAOtherSpecies+
                        +0.579562
                    )
                else:
                    dependent_vars = (
                        -0.302305E-01*self.BA+
                        +0.938947*log(self.BA)+
                        +0.563241E-03*self.stems+
                        +0.148914*log(self.stems)+
                        +0.419586E-02*self.age+
                        -1.15586*log(self.age)+
                        -0.138465E-01*self.BAOtherSpecies+
                        +2.72773
                    )
            elif SIdm<200:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.123212E-01*self.BA+
                        +0.864851*log(self.BA)+
                        -0.497769E-04*self.stems+
                        +0.200066*log(self.stems)+
                        +0.211976E-02*self.age+
                        -0.821163*log(self.age)+
                        -0.941390E-02*self.BAOtherSpecies+
                        +1.59527
                    )

                else:
                    dependent_vars = (
                        -0.216126E-02*self.BA+
                        +0.938131*log(self.BA)+
                        -0.169034E-03*self.stems+
                        +0.621225E-01*log(self.stems)+
                        +0.305833E-02*self.age+
                        -1.18279*log(self.age)+
                        -0.439063E-03*self.BAOtherSpecies+
                        +3.39954   
                    )

            elif SIdm<240:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.107718E-01*self.BA+
                        +0.796896*log(self.BA)+
                        -0.975686E-04*self.stems+
                        +0.230066*log(self.stems)+
                        -0.577520E-03*self.age+
                        -0.570857*log(self.age)+
                        -0.155230E-01*self.BAOtherSpecies+
                        +0.784527
                    )
                else:
                    dependent_vars = (
                        -0.632941E-02*self.BA+
                        +0.767710*log(self.BA)+
                        -0.173551E-03*self.stems+
                        +0.173044*log(self.stems)+
                        +0.163026E-02*self.age+
                        -0.945376*log(self.age)+
                        -0.133437E-01*self.BAOtherSpecies+
                        +2.49514
                    )
                
            else:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.738511E-02*self.BA+
                        +0.809028*log(self.BA)+
                        -0.207393E-03*self.stems+
                        +0.199179*log(self.stems)+
                        +0.259619E-03*self.age+
                        -0.663161*log(self.age)+
                        -0.142082E-01*self.BAOtherSpecies+
                        +1.27892
                    )
                else:
                    dependent_vars = (
                        -0.207497E-01*self.BA+
                        +1.00931*log(self.BA)+
                        -0.653755E-05*self.stems+
                        +0.851371E-01*log(self.stems)+
                        -0.307386E-02*self.age+
                        -0.635182*log(self.age)+
                        -0.110970E-01*self.BAOtherSpecies+
                        +1.57124
                    )
            
            self.BAI5 = exp(dependent_vars + independent_vars + 0.0636)

class EkoBirch(EkoStandPart):
    def __init__(self,ba,stems,age):
        super().__init__(ba,stems,age)
    
    def getMortality(self,increment=5):

        if self.stand.Site.region == 'North' or self.stand.Site.region=='Central':
            crowding =  (-0.2513E-01+0.5489E-02*self.BA)*increment/100 
            other=0.78               
        else:
            crowding = 0.04*increment/100
            other=0.46

        if crowding > 1:
            crowding = 1
        elif crowding < 0:
            crowding = 0
        
        return crowding, 0.9*self.QMD, other, self.QMD
    
    def getVolume(self,BA=None,QMD=None,age=None,stems=None,HK=None):
        if self.stand is None:
            raise ValueError('Volume calculator cannot be called before EkoStandPart object is connected to an EkoStand object together with an EkoStandSite object!')
        
        SIdm = self.stand.Site.H100_Spruce * 10
        
        if self.stand.Site.region in ('North','Central'):
            b1 =  -0.035
            b2 =  -2.05
            F4age = (1 - exp(b1*age))
            F4basal_area = (1- exp(b2*BA))
            lnVolume = (
                +1.26244*log(BA)+
                -0.459580*F4basal_area+
                +0.540420*F4age+
                -0.176040*log(stems)+
                +0.201360*log(SIdm)+
                -1.68251*log(self.stand.Site.latitude)+
                -0.404000E-01*log(self.stand.Site.altitude)+
                +0.757200E-01*self.stand.Site.self.stand.Site.fertilised+
                +0.301200E-01*self.stand.Site.thinned+
                +0.401844E-02*HK+
                +8.44862
            )
                
            return  exp(lnVolume + 0.0755)

        else:
            
            b1 =  -0.07
            b2 =  -2.1
            F4age = (1 - exp(b1*age))
            F4basal_area = (1- exp(b2*BA))
            lnVolume = (
                -0.786906E-02*BA+
                +1.35254*log(BA)+
                -1.30862*QMD+
                -0.524630*F4basal_area+
                +1.01779*F4age+
                -0.254630*log(stems)+
                +0.204880*log(SIdm)+
                +2.75025*log(self.stand.Site.latitude)+
                +0.774000E-01*self.stand.Site.self.stand.Site.fertilised+
                +0.434800E-01*self.stand.Site.thinned+
                +0.250449E-02*HK+
                -9.38127
            )
                
            return  exp(lnVolume + 0.0595)
        
    def getBAI5(self,mortality=True):
        if self.stand is None:
            raise ValueError('Basal Area increment calculator cannot be called before EkoStandPart object is connected to an EkoStand object together with an EkoStandSite object!')
        
        SIdm = self.stand.Site.H100_Spruce * 10
        if mortality:
            ba_quotient_chronic_mortality = self.getChronicMortality()
        else:
            ba_quotient_chronic_mortality = 0

        if self.stand.Site.region in ('North','Central'):

            independent_vars = (
                -0.474848*ba_quotient_chronic_mortality+
                -0.207333*self.ba_quotient_acute_mortality+
                -0.202362E-02*self.HK+
                +0.914442E-01*self.stand.Site.thinned_5y
                +0.176843*self.stand.Site.fertilised+
                +0.256714*self.stand.Site.vegcode+
                -0.488706E-01*self.stand.Site.WetSoil+
                -0.139928E-01*self.stand.Site.latitude+
                -0.462992*self.stand.Site.altitude+
                +0.189383*self.stand.Site.TAX77
            )

            if SIdm<140:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        +0.281210E-02*self.BA+
                        +0.718062*log(self.BA)+
                        -0.264120E-03*self.stems+
                        +0.360947*log(self.stems)+
                        -0.513560*log(self.age)+
                        -0.146581E-01*self.BAOtherSpecies+
                        -0.768510
                    )
                else:
                    dependent_vars = (
                        +0.856585E-01*self.BA+
                        +0.488507*log(self.BA)+
                        -0.549010E-03*self.stems+
                        +0.467588*log(self.stems)+
                        -0.618645*log(self.age)+
                        -0.477226E-02*self.BAOtherSpecies+
                        -0.768510
                    )
            elif SIdm<180:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        +0.831133E-02*self.BA+
                        +0.660201*log(self.BA)+
                        -0.161770E-03*self.stems+
                        +0.361272*log(self.stems)+
                        -0.609806*log(self.age)+
                        -0.133204E-01*self.BAOtherSpecies+
                        -0.355882
                    )
                else:
                    dependent_vars = (
                        +0.665931E-02*self.BA+
                        +0.700295*log(self.BA)+
                        -0.221485E-03*self.stems+
                        +0.316196*log(self.stems)+
                        -0.489888*log(self.age)+
                        -0.246752E-01*self.BAOtherSpecies+
                        -0.355882
                    )

            elif SIdm<220:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.371203E-02*self.BA+
                        +0.835899*log(self.BA)+
                        -0.141238E-03*self.stems+
                        +0.221611*log(self.stems)+
                        -0.732659*log(self.age)+
                        -0.131446E-01*self.BAOtherSpecies+
                        +0.891049
                    )
                else : 
                    dependent_vars = (
                        -0.134251E-02*self.BA+
                        +0.838751*log(self.BA)+
                        -0.237653E-03*self.stems+
                        +0.192259*log(self.stems)+
                        -0.707746*log(self.age)+
                        -0.499067E-02*self.BAOtherSpecies+
                        +0.891049
                    )
            else:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.281602E-01*self.BA+
                        +0.800357*log(self.BA)+
                        +0.673284E-04*self.stems+
                        +0.205233*log(self.stems)+
                        -0.631139*log(self.age)+
                        -0.176494E-01*self.BAOtherSpecies+
                        +0.731245

                    )
                else:
                    dependent_vars = (
                        -0.177526E-01*self.BA+
                        +0.814686*log(self.BA)+
                        +0.781625E-04*self.stems+
                        +0.183532*log(self.stems)+
                        -0.593656*log(self.age)+
                        -0.211444E-01*self.BAOtherSpecies+
                        +0.731245

                    )

                self.BAI5 = exp(dependent_vars + independent_vars + 0.1642)


        else:
            
            independent_vars = (
                        -0.617367*ba_quotient_chronic_mortality+
                        -0.350920*self.ba_quotient_acute_mortality+
                        -0.134245E-02*self.HK+
                        +0.277904*self.stand.Site.fertilised+
                        +0.154562*self.stand.Site.vegcode+
                        +0.554711E-01*self.stand.Site.TAX77
            )

            if SIdm<220:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.850224E-02*self.BA+
                        +0.931518*log(self.BA)+
                        -0.874696E-04*self.stems+
                        +0.124964*log(self.stems)+
                        -0.890226E-02*self.age+
                        -0.498825*log(self.age)+
                        -0.493910E-02*self.BAOtherSpecies+
                        -0.135041
                    )
                else:
                    dependent_vars = (
                        +0.144427*self.BA+
                        +0.332109*log(self.BA)+
                        -0.457988E-03*self.stems+
                        +0.474159*log(self.stems)+
                        +0.922378E-02*self.age+
                        -1.50315*log(self.age)+
                        -0.116043E-01*self.BAOtherSpecies+
                        +1.19213
                    )
            elif SIdm<260:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        +0.129783E-01*self.BA+
                        +0.688150*log(self.BA)+
                        -0.158067E-03*self.stems+
                        +0.304149*log(self.stems)+
                        +0.411176E-02*self.age+
                        -0.864501*log(self.age)+
                        -0.533730E-02*self.BAOtherSpecies+
                        -0.135041
                    )

                else:
                    dependent_vars = (
                        -0.235447E-01*self.BA+
                        +0.962877*log(self.BA)+
                        +0.103737E-03*self.stems+
                        +0.186790*log(self.stems)+
                        -0.127109E-02*self.age+
                        -1.02854*log(self.age)+
                        -0.849201E-02*self.BAOtherSpecies+
                        +1.19213
                    )

            elif SIdm<300:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.110984E-01*self.BA+
                        +0.748193*log(self.BA)+
                        -0.434390E-04*self.stems+
                        +0.270476*log(self.stems)+
                        +0.823613E-03*self.age+
                        -0.718419*log(self.age)+
                        -0.174522E-01*self.BAOtherSpecies+
                        -0.135041
                    )
                else:
                    dependent_vars = (
                        -0.438786E-03*self.BA+
                        +0.818427*log(self.BA)+
                        -0.304146E-03*self.stems+
                        +0.241055*log(self.stems)+
                        +0.106700E-01*self.age+
                        -1.16385*log(self.age)+
                        -0.1978220E-01*self.BAOtherSpecies+
                        +1.19213
                    )
                
            else:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.204315E-01*self.BA+
                        +0.792798*log(self.BA)+
                        -0.179026E-03*self.stems+
                        +0.316913*log(self.stems)+
                        +0.262117E-02*self.age+
                        -0.791796*log(self.age)+
                        -0.146037E-01*self.BAOtherSpecies+
                        -0.135041

                    )
                else:
                    dependent_vars = (
                        +0.255898E-02*self.BA+
                        +0.730671*log(self.BA)+
                        +0.256307E-04*self.stems+
                        +0.256131*log(self.stems)+
                        +0.126785E-01*self.age+
                        -1.24005*log(self.age)+
                        -0.341768E-02*self.BAOtherSpecies+
                        +1.19213
                    )
            
            self.BAI5 = exp(dependent_vars + independent_vars + 0.1590)

class EkoBroadleaf(EkoStandPart):
    def __init__(self,ba,stems,age):
        super().__init__(ba,stems,age)

    def getMortality(self,increment=5):

        if self.stand.Site.region == 'North' or self.stand.Site.region == 'Central':
            crowding = (-0.7277E-02+-0.2456E-02*self.BA+0.1923E-03*self.BA**2)*increment/100
            other=0.5
        else:
            crowding = 0.04*increment/100
            other=0.46
        
        if crowding > 1:
            crowding = 1
        elif crowding < 0:
            crowding = 0
        
        return crowding, 0.9*self.QMD, other, self.QMD
        
    
    
    def getVolume(self,BA=None,QMD=None,age=None,stems=None,HK=None):
        if self.stand is None:
            raise ValueError('Volume calculator cannot be called before EkoStandPart object is connected to an EkoStand object together with an EkoStandSite object!')
        
        SIdm = self.stand.Site.H100_Spruce * 10
        
        if self.stand.Site.region in ('North','Central'):
            b1 =  -0.04
            b2 =  -2.3
            F4age = (1 - exp(b1*age))
            F4basal_area = (1- exp(b2*BA))
            lnVolume = (
                +1.26649*log(BA)+
                -0.580030*F4basal_area+
                +0.486310*F4age+
                -0.172050*log(stems)+
                +0.174930*log(SIdm)+
                -1.51968*log(self.stand.Site.latitude)+
                -0.368300E-01*log(self.stand.Site.altitude)+
                +0.547400E-01*self.stand.Site.thinned+
                +0.417126E-02*HK+
                +7.79034
            )

            return  exp(lnVolume + 0.0853)

        else:
            b1 =  -0.075
            b2 =  -2.1
            F4age = (1 - exp(b1*age))
            F4basal_area = (1- exp(b2*BA))
            lnVolume = (
                -0.148700E-01*BA+
                +1.29359*log(BA)+
                -0.784820*F4basal_area+
                +1.18741*F4age+
                -0.135830*log(stems)+
                +0.219890*log(SIdm)+
                +2.02656*log(self.stand.Site.latitude)+
                +0.242500E-01*self.stand.Site.thinned+
                +0.859600E-01*self.stand.StandBA+
                +0.509488E-03*HK+
                +7.50102
            )

            return  exp(lnVolume + 0.0671)
        
    def getBAI5(self,ba_quotient_chronic_mortality=0,ba_quotient_acute_mortality=0):
        if self.stand is None:
            raise ValueError('Basal Area increment calculator cannot be called before EkoStandPart object is connected to an EkoStand object together with an EkoStandSite object!')
        
        SIdm = self.stand.Site.H100_Spruce * 10

        if self.stand.Site.region in ('North','Central'):

            independent_vars = (
                -0.345933*ba_quotient_chronic_mortality+
                -0.138015*self.stand.Site.vegcode+
                -0.650878E-01*self.stand.Site.Bilberry_or_Cowberry+
                -0.175149E-01*self.stand.Site.latitude+
                -0.570035E-03*self.stand.Site.altitude+
                +0.151318*self.stand.Site.TAX77
            )

            if SIdm<160:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        +0.865166E-01*self.BA+
                        +0.755603*log(self.BA)+
                        -0.806548E-03*self.stems+
                        +0.275974*log(self.stems)+
                        -0.540881E-02*self.age+
                        -0.117056*log(self.age)+
                        -0.187866E-01*self.BAOtherSpecies+
                        -1.18519
                    )
                else:
                    dependent_vars = (
                        +0.865166E-01*self.BA+
                        +0.755603*log(self.BA)+
                        -0.806548E-03*self.stems+
                        +0.275974*log(self.stems)+
                        -0.540881E-02*self.age+
                        -0.117056*log(self.age)+
                        -0.187866E-01*self.BAOtherSpecies+
                        -0.952398
                    )
            elif SIdm<200:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        -0.129773E-01*self.BA+
                        +0.989525*log(self.BA)+
                        -0.715363E-04*self.stems+
                        +0.490676E-01*log(self.stems)+
                        +0.218728E-02*self.age+
                        -0.944317*log(self.age)+
                        -0.143834E-01*self.BAOtherSpecies+
                        +2.78296
                    )
                else:
                    dependent_vars = (
                        -0.129773E-01*self.BA+
                        +0.989525*log(self.BA)+
                        -0.715363E-04*self.stems+
                        +0.490676E-01*log(self.stems)+
                        +0.218728E-02*self.age+
                        -0.944317*log(self.age)+
                        -0.143834E-01*self.BAOtherSpecies+
                        +2.87671
                    )

            elif SIdm<240:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        +0.517826E-01*self.BA+
                        +0.768565*log(self.BA)+
                        -0.381320E-03*self.stems+
                        +0.201267*log(self.stems)+
                        +0.131078E-02*self.age+
                        -0.831523*log(self.age)+
                        -0.122796E-01*self.BAOtherSpecies+
                        +1.65650
                    )
                else : 
                    dependent_vars = (
                        +0.517826E-01*self.BA+
                        +0.768565*log(self.BA)+
                        -0.381320E-03*self.stems+
                        +0.201267*log(self.stems)+
                        +0.131078E-02*self.age+
                        -0.831523*log(self.age)+
                        -0.122796E-01*self.BAOtherSpecies+
                        +1.59209
                    )
            else:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        +0.243920E-02*self.BA+
                        +0.857832*log(self.BA)+
                        -0.949555E-04*self.stems+
                        +0.192173*log(self.stems)+
                        -0.292753E-02*self.age+
                        -0.570009*log(self.age)+
                        -0.240816E-01*self.BAOtherSpecies+
                        +0.916942

                    )
                else:
                    dependent_vars = (
                        +0.243920E-02*self.BA+
                        +0.857832*log(self.BA)+
                        -0.949555E-04*self.stems+
                        +0.192173*log(self.stems)+
                        -0.292753E-02*self.age+
                        -0.570009*log(self.age)+
                        -0.240816E-01*self.BAOtherSpecies+
                        +1.17865

                    )

                self.BAI5 = exp(dependent_vars + independent_vars + 0.1648)


        else:
            
            independent_vars = (
                        -1.20049*ba_quotient_chronic_mortality+
                        -0.367064*ba_quotient_acute_mortality+
                        +0.125048*self.stand.Site.thinned_5y+
                        +0.246684*self.stand.Site.fertilised+
                        +0.141955*self.stand.Site.vegcode+
                        +0.354866E-01*self.stand.Site.latitude+
                        -0.361988E-03*self.stand.Site.altitude
                        )

            if SIdm<240:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        +0.857153*log(self.BA)+
                        -0.541853E-04*self.stems+
                        +0.152684*log(self.stems)+
                        -0.803085E-02*self.age+
                        -0.570230*log(self.age)+
                        -0.100518*log(self.BAOtherSpecies)+ #assuming KG is GK typo.
                        -1.93895
                    )
                else:
                    dependent_vars = (
                        +0.857153*log(self.BA)+
                        -0.541853E-04*self.stems+
                        +0.152684*log(self.stems)+
                        -0.803085E-02*self.age+
                        -0.570230*log(self.age)+
                        -0.100518*log(self.BAOtherSpecies)+ #assuming KG is GK typo.
                        -2.01960
                    )
            elif SIdm<280:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        +0.794405*log(self.BA)+
                        -0.247009*self.stems+
                        +0.202344*log(self.stems)+
                        -0.250423*self.age+
                        -0.669629*log(self.age)+
                        -0.101205*log(self.BAOtherSpecies)+ #assuming KG is GK typo.
                        -1.93895
                    )

                else:
                    dependent_vars = (
                        +0.794405*log(self.BA)+
                        -0.247009*self.stems+
                        +0.202344*log(self.stems)+
                        -0.250423*self.age+
                        -0.669629*log(self.age)+
                        -0.101205*log(self.BAOtherSpecies)+ #assuming KG is GK typo.
                        -2.01960
                    )

            elif SIdm<320:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        +0.782374*log(self.BA)+
                        -0.125111E-03*self.stems+
                        +0.239626*log(self.stems)+
                        -0.787146E-03*self.age+
                        -0.733575*log(self.age)+
                        -0.823802E-01*log(self.BAOtherSpecies)+ #assuming KG is GK typo.
                        -1.93895
                    )
                else:
                    dependent_vars = (
                        +0.782374*log(self.BA)+
                        -0.125111E-03*self.stems+
                        +0.239626*log(self.stems)+
                        -0.787146E-03*self.age+
                        -0.733575*log(self.age)+
                        -0.823802E-01*log(self.BAOtherSpecies)+ #assuming KG is GK typo.
                        -2.01960
                    )
                
            else:
                if not self.stand.Site.thinned:
                    dependent_vars = (
                        +0.771398*log(self.BA)+
                        +0.427071E-04*self.stems+
                        +0.167037*log(self.stems)+
                        -0.190695E-02*self.age+
                        -0.587696*log(self.age)+
                        -0.113489*log(self.BAOtherSpecies)+ #assuming KG is GK typo.
                        -1.93895

                    )
                else:
                    dependent_vars = (
                        +0.771398*log(self.BA)+
                        +0.427071E-04*self.stems+
                        +0.167037*log(self.stems)+
                        -0.190695E-02*self.age+
                        -0.587696*log(self.age)+
                        -0.113489*log(self.BAOtherSpecies)+ #assuming KG is GK typo.
                        -2.01960
                    )
            
            self.BAI5 = exp(dependent_vars + independent_vars + 0.1734)
         
class EkoBeech(EkoStandPart):
    def __init__(self,ba,stems,age):
        super().__init__(ba,stems,age)

    def getMortality(self,increment=5):

        if self.stand.Site.region == 'North' or self.stand.Site.region == 'Central':
            crowding = (-0.7277E-02+-0.2456E-02*self.BA+0.1923E-03*self.BA**2)*increment/100
            other=0.5
        else:
            crowding = 0.04*increment/100
            other=0.46
        
        if crowding > 1:
            crowding = 1
        elif crowding < 0:
            crowding = 0
        
        return crowding, 0.9*self.QMD, other, self.QMD
    
    def getVolume(self,BA=None,QMD=None,age=None,stems=None,HK=None):
        if self.stand is None:
            raise ValueError('Volume calculator cannot be called before EkoStandPart object is connected to an EkoStand object together with an EkoStandSite object!')
        
        SIdm = self.stand.Site.H100_Spruce * 10
        b1 =  -0.02
        b2 =  -2.3
        F4age = (1 - exp(b1*age))
        F4basal_area = (1- exp(b2*BA))
        lnVolume = (
            -0.111600E-01*BA+
            +1.30527*log(BA)+
            -0.676190*F4basal_area+
            +0.490740*F4age+
            -0.151930*log(stems)+
            -0.572600E-01*log(SIdm)+
            +0.628000E-01*self.stand.Site.thinned+
            +0.203927E-02*HK+
            +2.85509
        )

        return  exp(lnVolume + 0.0392)
    
    def getBAI5(self,ba_quotient_chronic_mortality=0,ba_quotient_acute_mortality=0):
        if self.stand is None:
            raise ValueError('Basal Area increment calculator cannot be called before EkoStandPart object is connected to an EkoStand object together with an EkoStandSite object!')
        
        SIdm = self.stand.Site.H100_Spruce * 10
        

        independent_vars = (
            -0.862301*ba_quotient_acute_mortality+
            +0.162579E-02*SIdm+
            +0.538943
            )
        
        if SIdm<310:
            if not self.stand.Site.thinned:
                dependent_vars = (
                    +0.948126*log(self.BA)+
                    +0.563620E-01*log(self.stems)+
                    -0.751665*log(self.age)+
                    -0.163302E-01*self.BAOtherSpecies
                )
            else:
                dependent_vars = (
                    +0.948126*log(self.BA)+
                    +0.563620E-01*log(self.stems)+
                    -0.751665*log(self.age)+
                    -0.163302E-01*self.BAOtherSpecies+
                    +0.887110E-01

                )
        else:
            if not self.stand.Site.thinned:
                dependent_vars = (
                    +0.821914*log(self.BA)+
                    +0.102770*log(self.stems)+
                    -0.753735*log(self.age)+
                    -0.163641E-01*self.BAOtherSpecies
                )
            else:
                dependent_vars = (
                    +0.821914*log(self.BA)+
                    +0.102770*log(self.stems)+
                    -0.753735*log(self.age)+
                    -0.163641E-01*self.BAOtherSpecies+
                    +0.887110E-01
                )

        self.BAI5 = exp(dependent_vars + independent_vars + 0.1379)

class EkoOak(EkoStandPart):
    def __init__(self,ba,stems,age):
        super().__init__(ba,stems,age)

    def getMortality(self,increment=5):

        if self.stand.Site.region == 'North' or self.stand.Site.region == 'Central':
            crowding = (-0.7277E-02+-0.2456E-02*self.BA+0.1923E-03*self.BA**2)*increment/100
            other=0.5
        else:
            crowding = 0.04*increment/100
            other=0.46
        
        if crowding > 1:
            crowding = 1
        elif crowding < 0:
            crowding = 0
        
        return crowding, 0.9*self.QMD, other, self.QMD
    
    def getVolume(self,BA=None,QMD=None,age=None,stems=None,HK=None):
        if self.stand is None:
            raise ValueError('Volume calculator cannot be called before EkoStandPart object is connected to an EkoStand object together with an EkoStandSite object!')
        
        SIdm = self.stand.Site.H100_Spruce * 10
        b1 =  -0.055
        b2 =  -2.3
        F4age = (1 - exp(b1*age))
        F4basal_area = (1- exp(b2*BA))
        
        lnVolume = (
            -0.106300E-01*BA+
            +1.27353*log(BA)+
            -0.463790*F4basal_area+
            +0.801580*F4age+
            -0.157080*log(stems)+
            +0.159030*log(SIdm)+
            +0.503200E-01*self.stand.Site.thinned+
            +0.188030E-02*HK+
            +1.40608
        )

        return exp( lnVolume + 0.0756)
    
    def getBAI5(self,ba_quotient_chronic_mortality,ba_quotient_acute_mortality):
        if self.stand is None:
            raise ValueError('Basal Area increment calculator cannot be called before EkoStandPart object is connected to an EkoStand object together with an EkoStandSite object!')
        
        SIdm = self.stand.Site.H100_Spruce * 10

        independent_vars = (
            -0.389169*ba_quotient_acute_mortality+
            -0.609667
            )
        
        if SIdm<280:
            if not self.stand.Site.thinned:
                dependent_vars = (
                    +0.896599*log(self.BA)+
                    +0.199354*log(self.stems)+
                    -0.842665*log(self.age)+
                    -0.146432E-01*self.BAOtherSpecies
                )
            else:
                dependent_vars = (
                    +0.896599*log(self.BA)+
                    +0.199354*log(self.stems)+
                    -0.842665*log(self.age)+
                    -0.146432E-01*self.BAOtherSpecies

                )
        elif SIdm<320:
            if not self.stand.Site.thinned:
                dependent_vars = (
                    +0.847420*log(self.BA)+
                    +0.144495*log(self.stems)+
                    -0.727278*log(self.age)+
                    -0.222990E-01*self.BAOtherSpecies
                )
            else:
                dependent_vars = (
                    +0.847420*log(self.BA)+
                    +0.144495*log(self.stems)+
                    -0.727278*log(self.age)+
                    -0.222990E-01*self.BAOtherSpecies

                )
        else:
            if not self.stand.Site.thinned:
                dependent_vars = (
                    +0.851362*log(self.BA)+
                    +0.128100*log(self.stems)+
                    -0.667346*log(self.age)+
                    -0.199705E-01*self.BAOtherSpecies
                )
            else:
                dependent_vars = (
                    +0.851362*log(self.BA)+
                    +0.128100*log(self.stems)+
                    -0.667346*log(self.age)+
                    -0.199705E-01*self.BAOtherSpecies
                )

        self.BAI5 = exp(dependent_vars + independent_vars + 0.1618)

                    
Stand1 = EkoStand([EkoSpruce(ba=5,stems=3500,age=10)],EkoStandSite(57,100,13,3,28))
Stand1.grow5()
Stand1.grow5()