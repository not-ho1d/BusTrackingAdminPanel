from django.shortcuts import render
from django.http import JsonResponse
from AdminPanel.models import Routes,Bus
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
                    "bus_stops":r.route_data,
                    "stops":r.stopsData
                })
            except Routes.DoesNotExist:
                return JsonResponse({
                    "search_success":False
                })
        elif data["action"] == "save_tfps":
            try:
                r = Routes.objects.get(route_name = data["route_name"])
                r.stopsData = data["stops"]
                r.save()
            except Routes.DoesNotExist:
                print("no route")                
    print(context)

    return render(request,"edit_stops.html",context=context)

def AddBuses(request):
    ctx={}
    if request.method == "POST":
        data = json.loads(request.body)
        if data["action"] == "route_verification":
            try:
                r = Routes.objects.get(route_name = data["route_name"])
                return JsonResponse({
                    "search_success":True,
                    "stops":r.stopsData
                })
            except Routes.DoesNotExist:
                return JsonResponse({
                    "search_success":False
                })
        elif data["action"] == "save_bus":
            busData = json.loads(data["bus_data"])
            takeOffs = [busData["to1"],busData["to2"],busData["to3"],busData["to4"],busData["to5"],busData["to6"]]
            returns = [busData["rt1"],busData["rt2"],busData["rt3"],busData["rt4"],busData["rt5"],busData["rt6"]]
            try:
                bObj = Bus.objects.get(bus_name = busData["bus_name"])
                if(bObj == busData["bus_name"]):
                    bObj.delete()
            except:
                pass
            b=Bus(
                bus_name = busData["bus_name"],
                route_name = busData["route_name"],
                from_stop = busData["from"],
                to_stop = busData["to"],
                take_offs = takeOffs,
                returns = returns
            )
            b.save()
        elif data["action"] == "search_bus":
            try:
                b=Bus.objects.get(bus_name = data["bus_name"])
                return JsonResponse({
                    "search_success":True,
                    "from":b.from_stop,
                    "to":b.to_stop,
                    "route_name":b.route_name,
                    "takeoffs":b.take_offs,
                    "returns":b.returns
                })
            except Bus.DoesNotExist:
                return JsonResponse({
                    "search_success":False
                })
        elif data["action"] == "delete_bus":
            try:
                b = Bus.objects.get(bus_name = data["bus_name"])
                b.delete()
                return JsonResponse({
                    "delete_success":True
                })
            except:
                return JsonResponse({
                    "delete_success":False
                })
    return render(request,"add_buses.html",context=ctx)