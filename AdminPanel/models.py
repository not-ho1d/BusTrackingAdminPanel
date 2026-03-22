from django.db import models
import json
# Create your models here.
class Routes(models.Model):
    route_id = models.AutoField(primary_key=True)
    route_name = models.CharField(max_length=100)
    route_data = models.CharField(default=list)
    stopsData = models.JSONField(default=list)
    route_coords = models.JSONField(default=list,null=True)
    stop_to_stop_coords = models.JSONField(default=list,null=True)
    stop_to_stop_coords_rev = models.JSONField(default=None,null=True)
    def get_routeData(self):
        return json.loads(self.route_data)

class RouteCoords(models.Model):
    route_name = models.CharField(primary_key=True)
    data = models.JSONField(default=list)

class Bus(models.Model):
    bus_name = models.CharField(max_length=100,primary_key=True)
    route_name = models.CharField(max_length=100)
    from_stop = models.CharField(max_length=100)
    to_stop = models.CharField(max_length=100)
    take_offs = models.JSONField(default=list)
    returns = models.JSONField(default=list)
    feedback_timetables = models.JSONField(default=list)
    live_location = models.JSONField(default=list,null=True)
    driver_is_sharing_location = models.BooleanField(default=False,null = True)
    timetable = models.JSONField(default=dict)

    def take_offs_len(self):
        for ind,i in enumerate(self.take_offs):
            if(i==""):
                return ind



class BusLocation(models.Model):
    bus_name = models.CharField(max_length=100,primary_key=True)
    route_name = models.CharField(max_length=100)
    current_stop = models.JSONField(default=list)
    next_stop = models.JSONField(default=list)
    live_location = models.JSONField(default=list)
    speed = models.FloatField(null=True)
    state = models.CharField(max_length=50,null=True,default="takeoff")
    stop_index = models.IntegerField(null=True)
    prev_stop_index = models.IntegerField(null=True)
    stop_change_time_indicator = models.CharField(max_length=50,null=True,default=0)
    route_coords = models.JSONField(default=list,null=True)
    rev_coord_start_offset = models.IntegerField(null=True,default=0)
    rev_coord_end_offset = models.IntegerField(null=True,default=0)
    processed_coord = models.JSONField(default=list,null=True)

    def __str__(self):
        return (
            f"bus_name: {self.bus_name}\n"
            f"route_name: {self.route_name}\n"
            f"current_stop: {self.current_stop}\n"
            f"next_stop: {self.next_stop}\n"
            f"live_location: {self.live_location}\n"
            f"speed: {self.speed}\n"
            f"state: {self.state}\n"
            f"stop_index: {self.stop_index}\n"
            f"prev_stop_index: {self.prev_stop_index}\n"
            f"stop_change_time_indicator: {self.stop_change_time_indicator}\n"
            f"route_coords: {self.route_coords}\n"
            f"rev_coord_start_offset: {self.rev_coord_start_offset}\n"
            f"rev_coord_end_offset: {self.rev_coord_end_offset}\n"
            f"processed_coord: {self.processed_coord}"
        )

    def update_location(self,time):
        try:
            ltt = WorkerUpdates.objects.get(bus_name=self.bus_name)
            ltt = ltt.loaded_timetable
            for key in ltt.keys():
                if(time == ltt.get(key)):
                    print(key, " " ,ltt.get(key))
        except WorkerUpdates.DoesNotExist:
            pass
class Stops(models.Model):
    stop_name = models.CharField(max_length=100)
    parent_routes = models.JSONField(default=list)

class WorkerUpdates(models.Model):
    bus_name = models.CharField(max_length=100)
    route_name = models.CharField(max_length=100,null=True)
    returning = models.BooleanField(default=False)
    loaded_timetable = models.JSONField(default=list)
    live_location = models.CharField(max_length=200,null=True)


class Driver(models.Model):
    name = models.CharField(max_length=100)
    phone_no = models.CharField(max_length=100)
    place = models.CharField(max_length=100)
    passkey = models.CharField(max_length=100)

class AssignedBuses(models.Model):
    phone_no = models.CharField(max_length=100)
    bus_name = models.CharField(max_length=100)