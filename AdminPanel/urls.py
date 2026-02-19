from django.urls import path,include
from . import views
urlpatterns = [
    path("add_routes/",views.AddRoutes,name="add_routes"),
    path("edit_stops/",views.EditStops,name="edit_stops"),
    path("add_buses/",views.AddBuses,name="add_buses")

]
