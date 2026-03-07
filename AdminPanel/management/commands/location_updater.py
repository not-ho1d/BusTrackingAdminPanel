from django.core.management.base import BaseCommand
from django.core.cache import cache
from AdminPanel.models import Bus,WorkerUpdates,Routes
import time
import math

def is_within_50m(coord_lat, coord_lng, end_lat, end_lng):
    coord_lat = float(coord_lat)
    coord_lng = float(coord_lng)
    end_lat = float(end_lat)
    end_lng = float(end_lng)

    R = 6371000  # Earth radius in meters

    lat1 = math.radians(coord_lat)
    lat2 = math.radians(end_lat)
    dlat = math.radians(end_lat - coord_lat)
    dlng = math.radians(end_lng - coord_lng)

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    distance = R * c

    return distance <= 15

class Command(BaseCommand):
    def handle(self,*args, **kwargs):
        routes = Routes.objects.all()
        for route in routes:
            coords = route.route_coords
            stop_coords = route.stopsData
            print(len(stop_coords))
            routing_coords = []
            stop_to_stop_final_coords = []
            for i,coord in enumerate(stop_coords):
                if i < len(stop_coords)-1:
                    coord_data = {
                        "name":f'{coord['name']}-{stop_coords[i+1]['name']}',
                        "start_lat":str(coord['lat'])[:7],
                        "start_lng":str(coord['lng'])[:7],
                        "end_lat":str(stop_coords[i+1]['lat'])[:7],
                        "end_lng":str(stop_coords[i+1]['lng'])[:7]
                    }
                    routing_coords.append(coord_data)
            for data in routing_coords:
                print("data",data)
                res = []
                for coord in coords:
                    result = is_within_50m(coord['lat'], coord['lng'], data['end_lat'], data['end_lng'])

                    res.append({
                        "lat": coord['lat'],
                        "lng": coord['lng']
                    })

                    if result:
                        stop_to_stop_route = {"name":data["name"],"coords":res}

                        if(len(stop_to_stop_route["coords"])>1):
                            stop_to_stop_final_coords.append(stop_to_stop_route)

                        res=[]
            route.stop_to_stop_coords = list(stop_to_stop_final_coords)
            route.save()

        r = Routes.objects.get(route_name = "mananthavady-niravilpuzha")
        print(r.stop_to_stop_coords)
        