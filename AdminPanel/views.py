from django.shortcuts import render
from django.http import JsonResponse,HttpResponse
from django.views.decorators.csrf import csrf_exempt
from AdminPanel.models import Routes,Bus,Stops,WorkerUpdates
from django.core.cache import cache
from django.db.models import Q
import json
from datetime import datetime, timedelta
#utils
def add_minutes(time_str, mins):
    t = datetime.strptime(time_str, "%H:%M")
    new_time = t + timedelta(minutes=mins)
    return new_time.strftime("%H:%M")
def timesubtraction(time_str, mins):
    t = datetime.strptime(time_str, "%H:%M")
    new_time = t - timedelta(minutes=mins)
    return new_time.strftime("%H:%M")

def timeaddition(time_str, minutes):
    t = datetime.strptime(time_str, "%H:%M") 
    new_time = t + timedelta(minutes=int(minutes))
    return new_time.strftime("%H:%M")
def getTime():
    with open("AdminPanel/global_dat.json","r") as file:
        try:
            time = json.loads(file.read())
            #print(time)
            return time["time"]
        except Exception as e:
            print(e)
            return "00:00"
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
            for stops in r.stopsData:
                s =Stops.objects.get(stop_name = stops["name"])
                if routeName in s.parent_routes:
                    s.parent_routes.remove(routeName)
                s.save()
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
            for stop in data["stops"]:
                stop_name = stop["name"]
                try:
                    s = Stops.objects.get(stop_name = stop_name)
                    if data["route_name"] not in s.parent_routes:
                        s.parent_routes.append(data["route_name"])
                    s.save()
                    print(s.stop_name," : ",s.parent_routes)
                except Stops.DoesNotExist:
                    s = Stops(
                        stop_name = stop_name,
                        parent_routes = [data["route_name"]]
                    )
                    s.save()
                    print(s.stop_name," : ",s.parent_routes)
                    
            try:
                r = Routes.objects.get(route_name = data["route_name"])
                r.stopsData = data["stops"]
                r.save()
            except Routes.DoesNotExist:
                print("no route")                

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
                returns = returns,
            )
            #timetable making
            r = Routes.objects.get(route_name=busData["route_name"])
            stop_data = r.stopsData
            no_of_takeoffs = b.take_offs_len()
            timetable = {}
            for x,y in zip(takeOffs[:no_of_takeoffs],returns[:no_of_takeoffs]):
                stx = x
                init_ind = stx
                takeoff_tt = {}
                return_tt = {}
                for ind,sd in enumerate(stop_data):
                    if(ind<len(stop_data)):
                        if(ind==0):
                            stx=x
                        else:
                            stx=timeaddition(stx,stop_data[ind]["tfps"])
                        #print("stx: ",stx," tfps :",stop_data[ind+1]["tfps"])
                        takeoff_tt[sd["name"]]=stx
                sty = y
                stop_data_rev= list(reversed(stop_data))
                for ind,sd in enumerate(stop_data_rev):
                    if ind==0:
                        return_tt[sd["name"]]=sty
                    else:
                        sty=timeaddition(sty,stop_data_rev[ind-1]["tfps"])
                        return_tt[sd["name"]]=sty
                timetable[x] = takeoff_tt
                timetable[y] = return_tt
                #print(takeoff_tt)
                #print(return_tt)
            print(timetable)
            b.timetable = timetable
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

@csrf_exempt
def Api(request):
    if request.method == "POST":
        data = json.loads(request.body)
        if data["action"] == "find_bus_search":
            req = {"time":"10:40","from":"vellamunda","to":"nvlpzha"}
            routes = Stops.objects.filter(stop_name__in=[req["from"],req["to"]]).values("stop_name","parent_routes").distinct()
            stand1routes = routes[0]["parent_routes"]
            stand2routes = routes[1]["parent_routes"]
            shared_routes = list(set(stand1routes) & set(stand2routes))
            buses_in_route = []
            if shared_routes:
                r =Routes.objects.get(route_name = shared_routes[0])
                returning = False
                for stop in r.stopsData:
                    if(stop["name"] == req["from"]):
                        #print("from first")
                        returning = False
                        break
                    elif(stop["name"] == req["to"]):
                        #print("to first")
                        returning = True
                        break
                time = getTime()
                print(f'---current time: {time}')
                for route in shared_routes:
                    buses_list = WorkerUpdates.objects.filter(route_name = route)
                    for bus in buses_list:
                        bus_data = Bus.objects.filter(bus_name = bus.bus_name).first()
                        #print(bus_data.timetable)
                        if returning:
                            return_indexes = bus_data.returns
                            #print(return_indexes)
                            for ind in return_indexes:
                                if ind != '':
                                    bus_keys = list(bus_data.timetable[ind].keys())
                                    from_stand_index = bus_keys.index(req["from"])
                                    buses_in_route.append({"bus_route":route,"bus_name":bus.bus_name,"bus_time":bus_data.timetable[ind][req["from"]]})
                        else:
                            takeoff_indexes = bus_data.take_offs
                            for ind in takeoff_indexes:
                                if ind != '':
                                    bus_keys = list(bus_data.timetable[ind].keys())
                                    from_stand_index = bus_keys.index(req["from"])
                                    buses_in_route.append({"bus_route":route,"bus_name":bus.bus_name,"bus_time":bus_data.timetable[ind][req["from"]]})
                
                print("sent:  ",{
                    "search_success":True,
                    "data":buses_in_route
                })
                return JsonResponse({
                    "search_success":True,
                    "data":buses_in_route
                })
            else:
                return JsonResponse({
                    "search_success":False
                })
    return render(request,"api_debug.html",context={"time":"10:5"})