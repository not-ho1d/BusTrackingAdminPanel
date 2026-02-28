from django.db import models
import json
# Create your models here.
class Routes(models.Model):
    route_id = models.AutoField(primary_key=True)
    route_name = models.CharField(max_length=100)
    route_data = models.CharField(default=list)
    stopsData = models.JSONField(default=list)
    route_coords = models.JSONField(default=list,null=True)
    def get_routeData(self):
        return json.loads(self.route_data)


class Bus(models.Model):
    bus_name = models.CharField(max_length=100,primary_key=True)
    route_name = models.CharField(max_length=100)
    from_stop = models.CharField(max_length=100)
    to_stop = models.CharField(max_length=100)
    take_offs = models.JSONField(default=list)
    returns = models.JSONField(default=list)
    timetable = models.JSONField(default=dict)

    def take_offs_len(self):
        for ind,i in enumerate(self.take_offs):
            if(i==""):
                return ind

class Stops(models.Model):
    stop_name = models.CharField(max_length=100)
    parent_routes = models.JSONField(default=list)

class WorkerUpdates(models.Model):
    bus_name = models.CharField(max_length=100)
    route_name = models.CharField(max_length=100,null=True)
    returning = models.BooleanField(default=False)
    loaded_timetable = models.JSONField(default=list)
    live_location = models.CharField(max_length=200,null=True)
    
