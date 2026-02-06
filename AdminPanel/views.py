from django.shortcuts import render
from django.http import JsonResponse
from AdminPanel.models import Routes
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


    print(context)
    return render(request,"admin_panel.html",context=context)
