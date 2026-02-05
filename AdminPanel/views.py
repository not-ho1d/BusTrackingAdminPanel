from django.shortcuts import render
from django.http import JsonResponse
import json

# Create your views here.
def AdminPanel(request):
    if request.method == "POST":
        data = json.loads(request.body)
        wayPoints = data["way_points"]
        routeName = data["route_name"]
        print(routeName)
    return render(request,"admin_panel.html")
