from django.shortcuts import render
from django.http import JsonResponse
from .models import Routes
import json
# Create your views here.
def AddRoutes(request):
    context = {}
    routes = Routes.objects.all()
    if routes:
        allRoutes = []
        for r in routes:
            routeData = {}
            routeData["route_name"]=r.route_name
            routeData["route_data"]=json.dumps(r.get_routeData())
            allRoutes.append(routeData)

        context["routes"] = allRoutes

    if request.method == "POST":
        data = json.loads(request.body)
        action = data["action"]
        routeName = data["route_name"]

        if action == "add":
            wayPoints = data["way_points"]

            stringWayPoints = json.dumps(wayPoints)
            routeSearchRes = Routes.objects.filter(route_name=routeName).first()
            if routeSearchRes:
                r = Routes.objects.get(route_name = routeName)
                r.route_data = stringWayPoints
                r.save()
            else:
                r = Routes(
                    route_name = routeName,
                    route_data = stringWayPoints
                )
                r.save()
        else:
            r= Routes.objects.get(route_name=routeName)
            r.delete()
    return render(request,"add_routes.html",context=context)

def EditStops(request):
    context = {}
    if request.method == "POST":
        data = json.loads(request.body)
        if data["action"] == "search_route":
            try:
                r = Routes.objects.get(route_name = data["route_name"])
                return JsonResponse({
                    "search_success":True,
                    "bus_stops":r.route_data
                })
            except Routes.DoesNotExist:
                return JsonResponse({
                    "search_success":False
                })
        elif data["action"] == "save_stop_data":
            try:
                stopData = data["stop_data"]
                print(stopData[0])
            except:
                pass                
    print(context)

    return render(request,"edit_stops.html",context=context)
