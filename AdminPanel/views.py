from django.shortcuts import render
from django.http import JsonResponse,HttpResponse
from django.views.decorators.csrf import csrf_exempt
from AdminPanel.models import Routes,Bus,Stops,WorkerUpdates,BusLocation,Driver,AssignedBuses
from django.core.cache import cache
from django.db.models import Q
from django.core.management import call_command
import traceback
import json
import copy
from datetime import datetime, timedelta

update_queue = []
delete_queue = []
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
        


#-----------------Views----------------------        
def busdetails(request):

    results = []
    added_buses = set()

    # first add buses from queue
    for qd in reversed(update_queue):

        if type(qd) == Bus:

            # skip duplicate queue buses
            if qd.bus_name in added_buses:
                continue

            added_buses.add(qd.bus_name)

            results.append({
                "bus_name": qd.bus_name,
                "route_name": qd.route_name,
                "state": "on queue"
            })

    # then add buses from Bus table that are not already added
    for bus in Bus.objects.all():

        if bus.bus_name in added_buses:
            continue

        location = BusLocation.objects.filter(
            bus_name=bus.bus_name
        ).first()

        if location:
            state = location.state
        else:
            state = "inactive"

        results.append({
            "bus_name": bus.bus_name,
            "route_name": bus.route_name,
            "state": state
        })

    if request.method == "POST":

        data = json.loads(request.body)

        if data["action"] == "search":

            filtered = []

            for bus in results:

                if data["bus_name"].lower() in bus["bus_name"].lower():
                    filtered.append(bus)

            return JsonResponse({
                "results": filtered
            })

        return JsonResponse({
            "results": results
        })

    return render(request, "busdetails.html", {"buses": results})

def AddRoutes(request):
    context = {}
    routes = Routes.objects.all()
    RouteQueue = False

    delete_queue_routes = []
    added_routes = set()

    for qd in reversed(delete_queue):
        if type(qd) == Routes:
            if qd.route_name in added_routes:
                continue
            added_routes.add(qd.route_name)
            delete_queue_routes.append(qd.route_name)

    for qd in reversed(update_queue):
        if(type(qd) == Routes):
            RouteQueue = True
    if routes or RouteQueue:
        allRoutes = []
        allRouteNames = []
        for r in routes:
            routeData = {}
            routeData["route_name"]=r.route_name
            allRouteNames.append(r.route_name)
            routeData["route_data"]=json.dumps(r.get_routeData())
            allRoutes.append(routeData)

        for qd in reversed(update_queue):
            if(type(qd) == Routes):
                print(qd.route_name,allRouteNames)
                if(qd.route_name not in allRouteNames):
                    print("nahhh")
                    routeData = {}
                    routeData["route_name"]=qd.route_name
                    routeData["route_data"]=json.dumps(qd.get_routeData())
                    allRouteNames.append(qd.route_name)
                    allRoutes.append(routeData)
        allRouteNames = []
        context["routes"] = allRoutes
        context["deleted_routes"] = delete_queue_routes

    
    if request.method == "POST":
        data = json.loads(request.body)
        action = data["action"]
        routeName = data["route_name"]

        if action == "add":
            wayPoints = data["way_points"]
            routeCoords = data["route_coords"]
            stringWayPoints = json.dumps(wayPoints)
            routeSearchRes = Routes.objects.filter(route_name=routeName).first()
            if routeSearchRes:
                r = Routes.objects.get(route_name = routeName)
                r.route_data = stringWayPoints
                r.route_coords = routeCoords
                update_queue.append(r)
                #r.save()
            else:
                r = Routes(
                    route_name = routeName,
                    route_data = stringWayPoints,
                    route_coords = routeCoords
                )
                #r.save()
                update_queue.append(r)
        elif action == "undo":
            print(routeName)
            for qd in reversed(delete_queue):
                print("qd: ",qd.route_name)
                if type(qd) == Routes:
                    if qd.route_name == routeName:
                        delete_queue.remove(qd)
        else:
            try:

                r = Routes.objects.get(route_name=routeName)

                for stops in r.stopsData:
                    print(stops["name"])

                    s = Stops.objects.filter(stop_name=stops["name"])

                    for rs in s:
                        if routeName in rs.parent_routes:
                            rs.parent_routes.remove(routeName)
                            update_queue.append(rs)

                    update_queue.append(r)

                buses = Bus.objects.filter(route_name=r.route_name)

                for bus in buses:
                    delete_queue.append(bus)

                delete_queue.append(r)

            except Routes.DoesNotExist:

                update_queue[:] = [
                    qd for qd in update_queue
                    if not (
                        (type(qd) == Routes and qd.route_name == routeName)
                        or
                        (type(qd) == Bus and qd.route_name == routeName)
                    )
                ]

                
                    
    return render(request,"add_routes.html",context=context)

def EditStops(request):
    context = {}
    if request.method == "POST":
        data = json.loads(request.body)
        if data["action"] == "search_route":
            for qd in reversed(update_queue):
                if(type(qd) == Routes):
                    if(qd.route_name == data["route_name"]):
                        return JsonResponse({
                            "search_success":True,
                            "bus_stops":qd.route_data,
                            "stops":qd.stopsData
                        })
                    
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
                    #s.save()
                    update_queue.append(s)
                    print(s.stop_name," : ",s.parent_routes)
                except Stops.DoesNotExist:
                    s = Stops(
                        stop_name = stop_name,
                        parent_routes = [data["route_name"]]
                    )
                    #s.save()
                    update_queue.append(s)
                    print("parent routes : ",s.stop_name," : ",s.parent_routes)
                    
            try:
                r = Routes.objects.get(route_name = data["route_name"])
                r.stopsData = data["stops"]
                #r.save()
                print("route_found")
                update_queue.append(r)
            except Routes.DoesNotExist:
                print("no route found")
                for qd in reversed(update_queue):
                    print(qd)
                    if(type(qd) == Routes):
                        print("here",qd)
                        if(qd.route_name == data["route_name"]):
                            qd.stopsData = data["stops"]
                            print("success")
                     

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
                for qd in reversed(update_queue):
                    if(type(qd) == Routes):
                        if(qd.route_name == data["route_name"]):
                            return JsonResponse({
                                "search_success":True,
                                "stops":qd.stopsData
                            })
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
                    #bObj.delete()
                    delete_queue.append(bObj)
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
            try:
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
                #b.save()
                update_queue.append(b)
            except Routes.DoesNotExist:
                for qd in reversed(update_queue):
                    if(type(qd) == Routes):
                        if(qd.route_name == busData["route_name"]):
                            r=qd
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
                            #b.save()
                            update_queue.append(b)
                
        elif data["action"] == "search_bus":
            for qd in reversed(update_queue):
                if(type(qd) == Bus):
                    if(qd.bus_name == data["bus_name"]):
                        return JsonResponse({
                        "search_success":True,
                        "from":qd.from_stop,
                        "to":qd.to_stop,
                        "route_name":qd.route_name,
                        "takeoffs":qd.take_offs,
                        "returns":qd.returns
                    })
            try:
                b=Bus.objects.get(bus_name = data["bus_name"])
                print({
                    "search_success":True,
                    "from":b.from_stop,
                    "to":b.to_stop,
                    "route_name":b.route_name,
                    "takeoffs":b.take_offs,
                    "returns":b.returns
                })
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
                #b.delete()
                delete_queue.append(b)
                return JsonResponse({
                    "delete_success":True
                })
            except:
                return JsonResponse({
                    "delete_success":False
                })
    return render(request,"add_buses.html",context=ctx)


@csrf_exempt
def add_drivers(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            action = data.get("action")

            # Save driver
            if action == "save_driver":
                name = data.get("name")
                phone_no = data.get("mobile_no")
                place = data.get("place")
                passkey = data.get("passkey")
                d = Driver(
                    name = name,
                    phone_no = phone_no,
                    place = place,
                    passkey = passkey,
                )
                d.save()
                return JsonResponse({"success": True, "created": created})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return render(request,"add_drivers.html")


def to_minutes(t):
    h, m = map(int, t.split(":"))
    return h * 60 + m

def find_trip_by_time(timetable, target_time):
    for trip, stops in timetable.items():
        if target_time in stops.values():
            return trip
    return None

def find_stop_by_time(timetable, trip, target_time):
    for stop, time in timetable[trip].items():
        if time == target_time:
            return stop
    return None

def to_time(m):
    return f"{m//60:02d}:{m%60:02d}"

def fix_timetable_order(timetable, min_gap=1):
    for trip in timetable:
        trip_start = to_minutes(trip)

        # sort stops by their time (this is the key fix)
        sorted_stops = sorted(
            timetable[trip].items(),
            key=lambda x: to_minutes(x[1])
        )

        prev_time = trip_start - min_gap
        new_trip = {}

        for stop, time in sorted_stops:
            current = to_minutes(time)

            # cannot go before trip start
            if current < trip_start:
                current = trip_start

            # strictly increasing
            if current <= prev_time:
                current = prev_time + min_gap

            new_trip[stop] = to_time(current)
            prev_time = current

        timetable[trip] = new_trip

    return timetable

def safe_update_time(timetable, trip, stop, new_minutes):
    stops = list(timetable[trip].keys())
    idx = stops.index(stop)

    trip_start = to_minutes(trip)

    # previous stop
    if idx > 0:
        prev_time = to_minutes(timetable[trip][stops[idx - 1]])
    else:
        prev_time = trip_start

    # next stop
    if idx < len(stops) - 1:
        next_time = to_minutes(timetable[trip][stops[idx + 1]])
    else:
        next_time = None

    # enforce boundaries
    if new_minutes <= prev_time:
        new_minutes = prev_time + 1

    if next_time and new_minutes >= next_time:
        new_minutes = next_time - 1

    return new_minutes



@csrf_exempt
def Api(request):
    if request.method == "POST":
        data = json.loads(request.body)
        #print(data)
        if data["action"] == "find_bus_search":
            #req = {"time":"10:40","from":"vellamunda","to":"niravilpuzha"}
            routes = Stops.objects.filter(stop_name__in=[data["from"],data["to"]]).values("stop_name","parent_routes").distinct()
            stand1routes = routes[0]["parent_routes"]
            stand2routes = routes[1]["parent_routes"]
            shared_routes = list(set(stand1routes) & set(stand2routes))
            buses_in_route = []
            if shared_routes:
                r =Routes.objects.get(route_name = shared_routes[0])
                returning = False
                for stop in r.stopsData:
                    if(stop["name"] == data["from"]):
                        print("from first")
                        returning = False
                        break
                    elif(stop["name"] == data["to"]):
                        print("to first")
                        returning = True
                        break
                time = getTime()
                print(f'---current time: {time}')
                for route in shared_routes:
                    buses_list = Bus.objects.filter(route_name = route)
                    for bus in buses_list:
                        #print(bus.timetable)
                        if returning:
                            return_indexes = bus.returns
                            for ind in return_indexes:
                                if ind != '':
                                    bus_keys = list(bus.timetable[ind].keys())
                                    from_stand_index = bus_keys.index(data["from"])
                                    bus_time= bus.timetable[ind][data["from"]]
                                    if bus_time > time:
                                        buses_in_route.append({"bus_route":route,"bus_name":bus.bus_name,"bus_time":bus_time,"returning":True})
                                        print(bus.bus_name)
                        else:
                            takeoff_indexes = bus.take_offs
                            #print("to",takeoff_indexes)
                            for ind in takeoff_indexes:
                                if ind != '':
                                    bus_keys = list(bus.timetable[ind].keys())
                                    #print("buskeys: ",bus_keys)
                                    from_stand_index = bus_keys.index(data["from"])
                                    bus_time = bus.timetable[ind][data["from"]]
                                    if bus_time > time:
                                        buses_in_route.append({"bus_route":route,"bus_name":bus.bus_name,"bus_time":bus_time,"returning":False})
                                        print(bus.bus_name)
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
            
        if data["action"] == "get_route_coords":
            if request.method == "POST":
                b = Bus.objects.get(bus_name = data["bus_name"])
                r = Routes.objects.get(route_name = b.route_name)
                print(r.route_coords[0])
                return JsonResponse({
                    "route_poly":r.route_coords
                })
        if(data["action"] == "find_bus_location"):
            try:
                bus = BusLocation.objects.get(bus_name = data["bus_name"])
                b = Bus.objects.get(bus_name = data["bus_name"])
                if(b.driver_is_sharing_location):
                    print("live loc")
                    return JsonResponse({
                        "live_location":True,
                        "data":b.live_location
                    })
                else:
                    print("route_coords: ",bus.live_location)
                    print("pred")
                    return JsonResponse({
                        "live_location":True,
                        "data":bus.live_location
                    })
            except BusLocation.DoesNotExist:
                try:
                    b = Bus.objects.get(bus_name = data["bus_name"])
                    if(b.driver_is_sharing_location):
                        print("live locc")
                        return JsonResponse({
                            "live_location":True,
                            "data":b.live_location
                        })
                    else:
                        bus = Bus.objects.get(bus_name = data["bus_name"])
                        route = Routes.objects.get(route_name = bus.route_name)
                        print("route_coords: ",route.route_coords[0])
                        return JsonResponse({
                            "live_location":True,
                            "data":route.route_coords[0],
                        })
                except:
                    bus = Bus.objects.get(bus_name = data["bus_name"])
                    route = Routes.objects.get(route_name = bus.route_name)
                    print("route_coords: ",route.route_coords[0])
                    return JsonResponse({
                        "live_location":True,
                        "data":route.route_coords[0],
                    })
        if(data["action"] == "db_reload"):
            print(update_queue)
            print(delete_queue)
            for q in update_queue[:]:
                q.save()
                update_queue.remove(q)

            for q in delete_queue[:]:
                q.delete()
                delete_queue.remove(q)
            call_command("location_updater")
            call_command("update_timetables")
        if data["action"] == "get_all_routes":
            stops = Stops.objects.all()
            stop_names = [s.stop_name for s in stops]
            print(stop_names)
            return JsonResponse({"stops": stop_names})
        if(data["action"]=="driver_login"):
            phone = data["phone"]
            passkey = data["passkey"]
            try:
                d = Driver.objects.get(phone_no=phone)
                if(d.passkey == passkey):
                    return JsonResponse({
                    "login_success":True
                })
                else:
                    return JsonResponse({
                    "login_success":False,
                    "reason":"incorrect passkey! contact admins for a new one"
                })
            except Driver.DoesNotExist:
                return JsonResponse({
                    "login_success":False,
                    "reason":"phone number doesnt match any account"
                })
        if(data["action"]=="get_driver_data"):
            phone = data["phone"]
            try:
                d = Driver.objects.get(phone_no=phone)
                abWhole = AssignedBuses.objects.filter(phone_no = phone)
                bus_list = []
                for ab in abWhole:
                    b = Bus.objects.get(bus_name = ab.bus_name)    
                    bus_list.append({"bus_name" : ab.bus_name,"route_name": b.route_name})
                return JsonResponse({
                    "driver_data_success":True,
                    "driver_data":bus_list
                })
            except Driver.DoesNotExist:
                return JsonResponse({
                    "driver_data_success":False,
                })
        if data["action"] == "search_bus":
            for qd in reversed(update_queue):
                if(type(qd) == Bus):
                    if(qd.bus_name == data["bus_name"]):
                        return JsonResponse({
                        "search_success":True,
                        "from":qd.from_stop,
                        "to":qd.to_stop,
                        "route_name":qd.route_name,
                        "takeoffs":qd.take_offs,
                        "returns":qd.returns
                    })
            try:
                b=Bus.objects.get(bus_name = data["bus_name"])
                print({
                    "search_success":True,
                    "from":b.from_stop,
                    "to":b.to_stop,
                    "route_name":b.route_name,
                    "takeoffs":b.take_offs,
                    "returns":b.returns
                })
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
        if data["action"] == "update_bus_timings":
            busData = json.loads(data["bus_data"])
            takeOffs = [busData["to1"],busData["to2"],busData["to3"],busData["to4"],busData["to5"],busData["to6"]]
            returns = [busData["rt1"],busData["rt2"],busData["rt3"],busData["rt4"],busData["rt5"],busData["rt6"]]
            try:
                bObj = Bus.objects.get(bus_name = busData["bus_name"])
                if(bObj == busData["bus_name"]):
                    #bObj.delete()
                    delete_queue.append(bObj)
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
            #b.save()
            update_queue.append(b)
        if data["action"] == "get_driver_location":
            try:
                c_bus = Bus.objects.get(bus_name = data["bus_name"])
                loc = {"lat":data["latitude"],"lng":data["longitude"]}
                if(c_bus.driver_is_sharing_location):
                    c_bus.live_location = loc
                c_bus.save()
                print(c_bus.live_location)
            except:
                traceback.print_exc()
                pass
        if data["action"] == "driver_tracking_state":
            try:
                c_bus = Bus.objects.get(bus_name = data["bus_name"])
                c_bus.driver_is_sharing_location = data["is_tracking"]
                c_bus.save()
                print(c_bus.driver_is_sharing_location)
            except:
                traceback.print_exc()
                pass
        if data["action"] == "live_or_not":
            b = Bus.objects.get(bus_name=data["bus_name"])
            return JsonResponse({
                "is_live": b.driver_is_sharing_location
            })
        if data["action"] == "add_new_timetable":
            b = Bus.objects.get(bus_name=data["bus_name"])
            timetable = copy.deepcopy(b.timetable)

            target_time = data["time_bracket"]

            trip = find_trip_by_time(timetable, target_time)

            if not trip:
                print("Time not found in any trip")
                return

            stop = find_stop_by_time(timetable, trip, target_time)

            if not stop:
                print("Stop not found")
                return

            current_val = timetable[trip][stop]
            current_minutes = to_minutes(current_val)

            early = int(data["early"])
            late = int(data["late"])

            if early > 0:
                new_minutes = current_minutes - early
            elif late > 0:
                new_minutes = current_minutes + late
            else:
                new_minutes = current_minutes

            new_minutes = safe_update_time(timetable, trip, stop, new_minutes)

            timetable[trip][stop] = to_time(new_minutes)


            b.feedback_timetables.append(timetable)
            print(len(b.feedback_timetables))
            b.save()

            print("Trip:", trip)
            print("Stop:", stop)
            print("New Time:", timetable[trip][stop])
            print(timetable)
    return render(request,"api_debug.html",context={"time":"10:5"})


def view_drivers_page(request):
    return render(request, "view_drivers.html")

def view_drivers_data(request):
    search = request.GET.get("search", "").strip()
    if search:
        drivers = Driver.objects.filter(
            name__icontains=search
        ) | Driver.objects.filter(
            phone_no__icontains=search
        )
    else:
        drivers = Driver.objects.all()
    # Alphabetical order by name
    drivers = drivers.order_by("name")
    drivers_list = list(drivers.values("name","phone_no","place"))
    return JsonResponse({"drivers": drivers_list})

def view_drivers_page(request):
    return render(request, "view_drivers.html")

@csrf_exempt
def assign_driver(request):
    driver = None
    success = False

    phone_no = request.GET.get("phone_no")
    if phone_no:
        drivers = Driver.objects.filter(phone_no=phone_no)
        if drivers.exists():
            driver = drivers.first()

    # Handle AJAX POST for passkey, assign bus, or delete bus
    if request.method == "POST" and driver:
        # Update passkey
        new_passkey = request.POST.get("passkey")
        if new_passkey:
            print("new pass key ",new_passkey)
            driver.passkey = new_passkey
            driver.save()
            success = True

        # Assign new bus
        bus_name = request.POST.get("bus_name")
        if bus_name:
            AssignedBuses.objects.create(phone_no=driver.phone_no, bus_name=bus_name)
            success = True

        # Delete bus
        delete_bus_name = request.POST.get("delete_bus_name")
        if delete_bus_name:
            AssignedBuses.objects.filter(phone_no=driver.phone_no, bus_name=delete_bus_name).delete()
            success = True

    # Fetch assigned buses for this driver
    assigned_buses = AssignedBuses.objects.filter(phone_no=driver.phone_no) if driver else []

    return render(request, "assign_driver.html", {
        "driver": driver,
        "success": success,
        "assigned_buses": assigned_buses
    })