from django.urls import path,include
from . import views
urlpatterns = [
    path("",views.AddRoutes,name = ""),
    path("add_routes/",views.AddRoutes,name="add_routes"),
    path("edit_stops/",views.EditStops,name="edit_stops"),
    path("add_buses/",views.AddBuses,name="add_buses"),
    path("Api/",views.Api,name="Api"),
    path("add_drivers/",views.add_drivers,name="add_drivers"),
    path("view_drivers/", views.view_drivers_page, name="view_drivers"),
    path("view_drivers/data/", views.view_drivers_data, name="view_drivers_data"),
    path("assign_driver/", views.assign_driver, name="assign_driver"),
]
