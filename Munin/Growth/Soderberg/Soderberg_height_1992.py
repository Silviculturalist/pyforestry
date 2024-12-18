import math

class Soderberg1992Height:
    
    @staticmethod
    def southern_sweden_beech(DBH_cm, total_age, BA_Spruce_m2, BA_m2, latitude, altitude, divided_plot=0, county=None):
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        south_eastern_county = 1 if county in ["Stockholm", "Södermanland", "Uppsala", "Östergötland", "Kalmar", "Västmanland"] else 0
        region5 = 1 if county in ["Blekinge", "Kristianstad", "Malmöhus", "Västra Götaland", "Halland", "Gotland"] else 0
        
        return math.exp(
            -0.14407E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.72319E-2 * total_age +
            -0.27244E-4 * (total_age ** 2) +
            -0.57810E-5 * latitude * altitude +
            0.18040E0 * BA_quotient_Spruce +
            0.18800E0 * south_eastern_county +
            -0.18416E0 * region5 +
            -0.17410E0 * divided_plot +
            0.52974E1 +
            0.01296
        ) / 10

    @staticmethod
    def southern_sweden_pine(SI100_Pine, distance_to_coast_km, DBH_cm, DBH_largest_tree_on_plot_cm, total_age,
                               BA_Pine_m2, BA_Spruce_m2, BA_Birch_m2, BA_m2, latitude, altitude, divided_plot=0, county=None):
        BA_quotient_Pine = BA_Pine_m2 / BA_m2
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        BA_quotient_Birch = BA_Birch_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        close_to_coast = 1 if distance_to_coast_km < 50 else 0
        south_eastern_county = 1 if county in ["Stockholm", "Södermanland", "Uppsala", "Östergötland", "Kalmar", "Västmanland"] else 0
        
        return math.exp(
            -0.30345E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.88427E4 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.68724E-2 * total_age +
            -0.38585E-4 * (total_age ** 2) +
            0.16646E-2 * SI100_Pine * 10 +
            -0.47335E-2 * altitude +
            0.82679E-4 * latitude * altitude +
            0.91429E-1 * diameter_quotient +
            -0.28115E0 * (diameter_quotient ** 2) +
            0.20570E0 * BA_quotient_Pine +
            0.29485E0 * BA_quotient_Spruce +
            0.13909E0 * BA_quotient_Birch +
            0.36444E-1 * south_eastern_county +
            -0.60312E-1 * divided_plot +
            -0.19855E0 * close_to_coast +
            0.52706E1 +
            0.01264
        ) / 10

    @staticmethod
    def southern_sweden_birch(SI100_Pine, DBH_cm, DBH_largest_tree_on_plot_cm, total_age, BA_Pine_m2, BA_Spruce_m2, BA_Birch_m2,
                               BA_m2, latitude, altitude, divided_plot=0, county=None):
        BA_quotient_Pine = BA_Pine_m2 / BA_m2
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        BA_quotient_Birch = BA_Birch_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        south_eastern_county = 1 if county in ["Stockholm", "Södermanland", "Uppsala", "Östergötland", "Kalmar", "Västmanland"] else 0
        
        return math.exp(
            -0.22552E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.39171E4 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.17264E-2 * total_age +
            -0.11572E-4 * (total_age ** 2) +
            0.89953E-3 * SI100_Pine * 10 +
            -0.90184E-2 * altitude +
            0.15804E-3 * latitude * altitude +
            -0.32296E0 * diameter_quotient +
            -0.44799E-1 * BA_quotient_Pine +
            0.11728E0 * BA_quotient_Spruce +
            0.10104E0 * BA_quotient_Birch +
            0.42911E-1 * south_eastern_county +
            -0.68048E-1 * divided_plot +
            0.57820E1 +
            0.01901
        )

    @staticmethod
    def southern_sweden_broadleaves(SI100_Pine, DBH_cm, DBH_largest_tree_on_plot_cm, total_age, BA_Pine_m2,
                                     BA_Spruce_m2, BA_Birch_m2, BA_m2, latitude, altitude, divided_plot=0):
        BA_quotient_Pine = BA_Pine_m2 / BA_m2
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        BA_quotient_Birch = BA_Birch_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        
        return math.exp(
            -0.22078E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.53920E4 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.53701E-2 * total_age +
            -0.41932E-4 * (total_age ** 2) +
            0.53968E-3 * SI100_Pine * 10 +
            -0.10758E-1 * altitude +
            0.18781E-3 * latitude * altitude +
            -0.17045E0 * diameter_quotient +
            -0.17291E0 * BA_quotient_Pine +
            0.10783E0 * BA_quotient_Spruce +
            -0.55868E-1 * BA_quotient_Birch +
            -0.51870E-1 * divided_plot +
            0.56569E1 +
            ((0.195 ** 2) / 2)
        ) / 10

    @staticmethod
    def southern_sweden_oak(SI100_Pine, DBH_cm, DBH_largest_tree_on_plot_cm, total_age, BA_Spruce_m2, BA_m2, latitude, altitude, divided_plot=0,
                             county=None):
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        south_eastern_county = 1 if county in ["Stockholm", "Södermanland", "Uppsala", "Östergötland", "Kalmar", "Västmanland"] else 0
        region5 = 1 if county in ["Blekinge", "Kristianstad", "Malmöhus", "Västra Götaland", "Halland", "Gotland"] else 0
        
        return math.exp(
            -0.25811E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.63100E4 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.13039E-2 * SI100_Pine * 10 +
            -0.41543E-5 * latitude * altitude +
            -0.32505E0 * diameter_quotient +
            0.59855E-1 * BA_quotient_Spruce +
            0.17355E0 * south_eastern_county +
            -0.47987E-1 * region5 +
            -0.69304E-1 * divided_plot +
            0.57884E1 +
            0.01584
        ) / 10

    @staticmethod
    def northern_sweden_pine(SI100_Pine, distance_to_coast_km, DBH_cm, DBH_largest_tree_on_plot_cm, total_age,
                               BA_Pine_m2, BA_m2, latitude, altitude, divided_plot=0):
        BA_quotient_Pine = BA_Pine_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        close_to_coast = 1 if distance_to_coast_km < 50 else 0
        
        return math.exp(
            -0.28390E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.64168E4 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.63874E-2 * total_age +
            -0.30707E-4 * (total_age ** 2) +
            0.12774E-2 * SI100_Pine * 10 +
            -0.15597E-1 * latitude +
            -0.48527E-5 * latitude * altitude +
            -0.44962E0 * diameter_quotient +
            0.70355E-1 * (diameter_quotient ** 2) +
            0.87350E-1 * (BA_quotient_Pine) +
            -0.56157E-1 * divided_plot +
            -0.72392E-1 * close_to_coast +
            0.68125E1 +
            0.01155
        ) / 10

    @staticmethod
    def northern_central_sweden_birch(SI100_Pine, DBH_cm, DBH_largest_tree_on_plot_cm, total_age, BA_Pine_m2,
                                       BA_Spruce_m2, BA_m2, latitude, altitude, divided_plot=0):
        BA_quotient_Pine = BA_Pine_m2 / BA_m2
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        
        return math.exp(
            -0.26607E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.71415E4 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.32789E-2 * total_age +
            -0.22514E-4 * (total_age ** 2) +
            0.85255E-3 * SI100_Pine * 10 +
            -0.18462E-1 * latitude +
            -0.72180E-5 * latitude * altitude +
            -0.39250E0 * diameter_quotient +
            0.76500E-1 * (diameter_quotient ** 2) +
            -0.74398E-1 * BA_quotient_Pine +
            -0.22539E-1 * BA_quotient_Spruce +
            -0.35918E-1 * divided_plot +
            0.72446E1 +
            0.01248
        ) / 10

    @staticmethod
    def northern_central_sweden_spruce(SI100_Pine, distance_to_coast_km, DBH_cm, DBH_largest_tree_on_plot_cm,
                                        total_age, BA_Pine_m2, BA_Spruce_m2, BA_m2, latitude, altitude, divided_plot=0):
        BA_quotient_Pine = BA_Pine_m2 / BA_m2
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        close_to_coast = 1 if distance_to_coast_km < 50 else 0
        
        return math.exp(
            -0.28663E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.47831E4 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.31669E-2 * total_age +
            -0.16854E-4 * (total_age ** 2) +
            0.10855E-2 * SI100_Pine * 10 +
            -0.99681E-2 * latitude +
            0.51262E-3 * altitude +
            -0.12449E-4 * latitude * altitude +
            -0.19831E0 * diameter_quotient +
            0.60923E-1 * BA_quotient_Pine +
            0.90784E-1 * BA_quotient_Spruce +
            -0.30688E-1 * divided_plot +
            -0.62548E-1 * close_to_coast +
            0.65200E1 +
            0.01095
        ) / 10

    @staticmethod
    def northern_sweden_birch(SI100_Pine, DBH_cm, DBH_largest_tree_on_plot_cm, total_age, BA_Pine_m2, BA_Spruce_m2,
                               BA_m2, latitude, altitude, divided_plot=0):
        BA_quotient_Pine = BA_Pine_m2 / BA_m2
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        
        return math.exp(
            -0.26607E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.71415E4 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.32789E-2 * total_age +
            -0.22514E-4 * (total_age ** 2) +
            0.85255E-3 * SI100_Pine * 10 +
            -0.18462E-1 * latitude +
            -0.72180E-5 * latitude * altitude +
            -0.39250E0 * diameter_quotient +
            0.76500E-1 * (diameter_quotient ** 2) +
            -0.74398E-1 * BA_quotient_Pine +
            -0.22539E-1 * BA_quotient_Spruce +
            -0.35918E-1 * divided_plot +
            0.72446E1 +
            0.01248
        ) / 10

    @staticmethod
    def northern_central_sweden_broadleaves(SI100_Pine, distance_to_coast_km, DBH_cm, total_age, BA_Spruce_m2, BA_m2,
                                             latitude, divided_plot=0):
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        close_to_coast = 1 if distance_to_coast_km < 50 else 0
        
        return math.exp(
            -0.14546E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.53659E-2 * total_age +
            -0.29042E-4 * (total_age ** 2) +
            0.17639E-2 * SI100_Pine * 10 +
            -0.34200E-1 * latitude +
            0.75841E-1 * BA_quotient_Spruce +
            -0.82953E-1 * divided_plot +
            0.15566E0 * close_to_coast +
            0.70706E1 +
            ((0.191 ** 2) / 2)
        )

    @staticmethod
    def northern_sweden_spruce(SI100_Pine, distance_to_coast_km, DBH_cm, DBH_largest_tree_on_plot_cm, total_age,
                                BA_Pine_m2, BA_Spruce_m2, BA_Birch_m2, BA_m2, latitude, altitude, divided_plot=0):
        BA_quotient_Pine = BA_Pine_m2 / BA_m2
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        BA_quotient_Birch = BA_Birch_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        close_to_coast = 1 if distance_to_coast_km < 50 else 0
        
        return math.exp(
            -0.27421E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.38013E4 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.31094E-2 * total_age +
            -0.20764E-4 * (total_age ** 2) +
            0.10161E-2 * SI100_Pine * 10 +
            0.15166E-2 * altitude +
            -0.25385E-4 * latitude * altitude +
            -0.23760E0 * diameter_quotient +
            0.10172E0 * BA_quotient_Pine +
            0.24012E0 * BA_quotient_Spruce +
            0.68141E-1 * BA_quotient_Birch +
            -0.47848E-1 * divided_plot +
            -0.69386E-1 * close_to_coast +
            0.57495E1 +
            0.01051
        ) / 10
