from django.core.management.base import BaseCommand
from django.core.cache import cache
from AdminPanel.models import Bus,WorkerUpdates,Routes,RouteCoords,BusLocation
import time
import json
import math
import threading
import traceback
from datetime import datetime

def get_speed_per_sec(coords, start_time, end_time):
    start = datetime.strptime(start_time, "%H:%M")
    end = datetime.strptime(end_time, "%H:%M")

    total_seconds = (end - start).total_seconds()
    total_indices = len(coords) - 1

    #print("ind: ",total_indices,"st: ",start_time,"ed: ",end_time, "ret speed: ",total_indices/total_seconds)
    return total_indices / total_seconds

last_reload_time=None
def dbReload(time):
    global last_reload_time
    if(last_reload_time == None or last_reload_time != time):
        print("yup")
        last_reload_time = time
        from AdminPanel.apps import process_queues
        process_queues()
        return "success"
    return last_reload_time

def addOne(num):
    num=int(num)
    if(num<9):
        return f'0{num+1}'
    else:
        return num+1

def reverse_route(route_data):
    reversed_route = []

    for segment in reversed(route_data):
        new_segment = {
            "name": segment["name"],
            "coords": list(reversed(segment["coords"]))
        }
        reversed_route.append(new_segment)

    return reversed_route

def getTimeTable(bus_name,time):
    b = Bus.objects.get(bus_name=bus_name)
    wu = WorkerUpdates.objects.get(bus_name=bus_name)
    wu.route_name = b.route_name
    wu.loaded_timetable = b.timetable[time]
    bl = BusLocation.objects.get(bus_name = bus_name)
    stop_change_time_indicator = wu.loaded_timetable[bl.next_stop]
    bl.stop_change_time_indicator = stop_change_time_indicator
    bl.save()

    print("route: ",wu.route_name,"\n",wu.loaded_timetable)
    wu.save()

def get_next_stop_time(bus_name,time):
    b = Bus.objects.get(bus_name=bus_name)
    wu = WorkerUpdates.objects.get(bus_name=bus_name)
    wu.route_name = b.route_name
    wu.loaded_timetable = b.timetable[time]
    bl = BusLocation.objects.get(bus_name = bus_name)
    stop_change_time_indicator = wu.loaded_timetable[bl.next_stop]
    bl.stop_change_time_indicator = stop_change_time_indicator
    return bl.stop_change_time_indicator

def returnTimeTable(bus_name,time):
    b = Bus.objects.get(bus_name=bus_name)
    return b.timetable[time]


class Time:
    def __init__(self,h,m,s):
        self.hrs = h #"06"
        self.min = m#"45"
        self.sec = s#"30"
        self.running = False
    def start(self,clockUpdateTime):
        print("clock started")
        self.running=True
        self.thread = threading.Thread(target=self._run,args=(clockUpdateTime,))
        self.thread.start()
    def _run(self,clockUpdateTime):
        while self.running:
            self.sec= addOne(self.sec)
            if(int(self.sec)>59):
                self.sec="00"
                self.min=addOne(self.min)
                #print(f'{self.hrs} : {self.min}')

                #print("cached")
                if(int(self.min)>59):
                    self.min="00"
                    self.hrs=addOne(self.hrs)
                    if(int(self.hrs)>24):
                        self.hrs="01"
                with open("AdminPanel/global_dat.json","w") as file:
                    file.write(json.dumps({"time":f'{self.hrs}:{self.min}'}))
            #print(self.hrs,":",self.min,":",self.sec)
            time.sleep(clockUpdateTime)
    def stop(self):
        self.running = False

class Command(BaseCommand):
    def handle(self,*args, **kwargs):
        with open("AdminPanel/conf.json","r") as file:
            conf = json.loads(file.read())
        clockUpdateTime = conf["clock_update_time"]
        dbReloadTime = conf["db_reload_time"]
        h, m, s = conf["speed"].split(":")
        clock = Time(h,m,s)
        clock.start(clockUpdateTime=clockUpdateTime)
        buses = Bus.objects.all()
        tt_data = {}
        for bus in buses:
            keys = bus.timetable.keys()
            for key in keys:
                if key in tt_data:
                    tt_data[key].append(bus.bus_name)
                else:
                    tt_data[key] = [bus.bus_name]
                #tt_data[f'{key}_route'] = bus.route_name
        wu = WorkerUpdates.objects.all()
        wu.delete()
        buses_on_run = []

        all_bl = BusLocation.objects.all()
        all_bl.delete()

        try:
            time=f'{clock.hrs}:{clock.min}'
            sec=clock.sec
            while True:

                prev_sec = sec
                sec=clock.sec
                prev_time = time
                time = f'{clock.hrs}:{clock.min}'
                if((sec!=prev_sec) and time == dbReloadTime):
                    if(dbReload(time) == "success"):
                        last_reload_time = None
                        #print(last_reload_time)
                if(time in tt_data and (prev_time!=time)):
                    for bus in tt_data[time]:
                        try:
                            wu = WorkerUpdates.objects.get(bus_name = bus)
                            if(wu.returning):
                                wu.returning = False
                                print(f'{bus} is taking off : {time}')
                                bl = BusLocation.objects.get(bus_name = bus)
                                curr_tt = returnTimeTable(bus,time)
                                curr_stop = list(curr_tt.keys())[0]
                                next_stop = list(curr_tt.keys())[1]
                                bl.current_stop = curr_stop
                                bl.next_stop = next_stop
                                bl.state = "takeoff"
                                bl.stop_index = 0
                                bl.prev_stop_index = -1
                                bl.speed = 0
                                bl.save()

                                
                            else:
                                wu.returning = True
                                print(f'{bus} is returning : {time}')
                                bl = BusLocation.objects.get(bus_name = bus)
                                curr_tt = returnTimeTable(bus,time)
                                curr_stop = list(curr_tt.keys())[0]
                                next_stop = list(curr_tt.keys())[1]
                                bl.current_stop = curr_stop
                                bl.next_stop = next_stop
                                bl.state = "return"
                                bl.stop_index = 0
                                bl.prev_stop_index = 0
                                bl.rev_coord_end_offset = 0
                                bl.rev_coord_start_offset = 0
                                bl.speed = 0
                                bl.stop_change_time_indicator = 0
                                bl.save()
                            wu.save()
                            getTimeTable(bus,time)
                        except WorkerUpdates.DoesNotExist:
                            print(f'{bus} is taking off : {time}')
                            try:
                                bl = BusLocation.objects.get(bus_name = bus)
                                curr_tt = returnTimeTable(bus,time)
                                curr_stop = list(curr_tt.keys())[0]
                                next_stop = list(curr_tt.keys())[1]
                                bl.current_stop = curr_stop
                                bl.next_stop = next_stop
                                bl.state = "takeoff"
                                bl.stop_index = 0
                                bl.prev_stop_index = -1
                                bl.speed = 0
                                bl.save()
                            except BusLocation.DoesNotExist:
                                curr_tt = returnTimeTable(bus,time)
                                curr_stop = list(curr_tt.keys())[0]
                                next_stop = list(curr_tt.keys())[1]
                                bus_obj = Bus.objects.get(bus_name = bus)
                                bl = BusLocation(
                                    bus_name = bus,
                                    route_name = bus_obj.route_name,
                                    current_stop = curr_stop,
                                    next_stop = next_stop,
                                    state = "takeoff",
                                    speed = 0,
                                    stop_index = 0
                                    )
                                bl.save()
                            wu = WorkerUpdates(
                                bus_name = bus,
                                returning = False
                            )  
                            wu.save()
                            getTimeTable(bus,time)
                                    
                            
                bl_table = BusLocation.objects.all()
                for bl_data in bl_table:
                    
                    if bl_data.state == "takeoff":
                        if(sec!=prev_sec):
                           
                            curr_bus = Bus.objects.get(bus_name = bl_data.bus_name)
                            curr_bus_route = Routes.objects.get(route_name = curr_bus.route_name)
                            curr_bus_route_coords = curr_bus_route.stop_to_stop_coords
                            
                            #print(time,bl_data.stop_change_time_indicator)
                            if(time >= bl_data.stop_change_time_indicator):
                                print(bl_data.stop_index)
                                bl_data.prev_stop_index = bl_data.stop_index
                                bl_data.stop_index+=1
                                wu_cpy = WorkerUpdates.objects.get(bus_name = bl_data.bus_name) 
                                bl_data.current_stop = bl_data.next_stop
                                try:
                                    next_stop= list(wu_cpy.loaded_timetable.keys())[bl_data.stop_index+1]
                                except IndexError:
                                    bl_data.state = "inactive"
                                    print(bl_data.bus_name, " is inactive")
                                    bl_data.save()
                                    continue
                                bl_data.next_stop = next_stop
                                bl_data.stop_change_time_indicator = wu_cpy.loaded_timetable[next_stop]
                                print("current bus: ",bl_data.bus_name,"current_stop: ",bl_data.current_stop, "new next_stop",bl_data.stop_change_time_indicator)
                                print(wu_cpy.loaded_timetable)
                                bl_data.speed = 0
                                #bl_data.save()
                                
                            try:
                                wu_check = WorkerUpdates.objects.get(bus_name = curr_bus.bus_name)
                                if wu_check:
                                    if bl_data.prev_stop_index == None:
                                        bl_data.prev_stop_index = -1
                                    
                                    
                                    
                                    loaded_tt = wu_check.loaded_timetable
                                    start_time = loaded_tt[bl_data.current_stop]
                                    end_time = loaded_tt[bl_data.next_stop]
                                    #if bl_data.bus_name == "testbus":
                                    #print("this ---", curr_bus_route_coords,"\n",bl_data.stop_index)     
                                    bl_data.route_coords = curr_bus_route_coords[bl_data.stop_index]
                                    bl_data.route_coords = bl_data.route_coords["coords"]
                                    if bl_data.prev_stop_index > -1:
                                        prev_route_coords = curr_bus_route_coords[bl_data.prev_stop_index]["coords"]
                                        prev_route_coords_len = len(prev_route_coords)
                                        bl_data.route_coords = bl_data.route_coords[prev_route_coords_len:]
                                        #print("here",prev_route_coords_len,len(route_coords),bl_data.speed)
                                    #print(len(route_coords["coords"][bl_data.prev_stop_index:]))
                                    speed = get_speed_per_sec(bl_data.route_coords,start_time,end_time)
                                    #print(speed,start_time,end_time)
                                    bl_data.speed+=speed
                                    print(f'{bl_data.bus_name}:{time}:{sec}'," : ",speed," : ",bl_data.route_coords[math.floor(bl_data.speed)],f'({int(bl_data.speed)}/{len(bl_data.route_coords)})')
                                    bl_data.live_location = bl_data.route_coords[math.floor(bl_data.speed)]
                                    bl_data.save()
                            except Exception as e:
                                traceback.print_exc()
                    
                    
                    
                    
                    elif bl_data.state == "return":
                        if(sec!=prev_sec):
                            
                            curr_bus = Bus.objects.get(bus_name = bl_data.bus_name)
                            wu_check = WorkerUpdates.objects.get(bus_name = curr_bus.bus_name)
                            curr_bus_route = Routes.objects.get(route_name = curr_bus.route_name)
                            curr_bus_route_coords = curr_bus_route.stop_to_stop_coords
                            curr_bus_route_coords = reverse_route(curr_bus_route_coords)
                            #print(bl_data.current_stop,bl_data.next_stop,wu_check.loaded_timetable)
                            start_time = wu_check.loaded_timetable[bl_data.current_stop]
                            end_time = wu_check.loaded_timetable[bl_data.next_stop]
                            try:
                                bl_data.route_coords = curr_bus_route_coords[bl_data.stop_index]["coords"]
                                len_of_next_stop = len(curr_bus_route_coords[bl_data.stop_index+1]["coords"])
                                len_of_complete_coord = len(curr_bus_route_coords[bl_data.stop_index]["coords"])
                                len_of_current_stop = len_of_complete_coord-len_of_next_stop
                                bl_data.rev_coord_end_offset = bl_data.rev_coord_start_offset+len_of_current_stop
                                #bl_data.rev_coord_end_offset=len_of_current_stop
                                #print(bl_data.rev_coord_start_offset,bl_data.rev_coord_end_offset,len_of_current_stop,len(bl_data.route_coords))
                                bl_data.processed_coord = bl_data.route_coords[:len_of_current_stop]
                                #print("here",len(bl_data.processed_coord))
                                bl_data.save()
                                #print("f",len(bl_data.route_coords[bl_data.rev_coord_start_offset:bl_data.rev_coord_end_offset]))
                            except IndexError:
                                bl_data.route_coords = curr_bus_route_coords[0]["coords"]
                                len_of_complete_coord = len(bl_data.route_coords)
                                print("here")
                                bl_data.processed_coord = bl_data.route_coords[:len_of_current_stop]
                                bl_data.save()
                            #print(bl_data.processed_coord)
                            try:
                                bl_data.speed += get_speed_per_sec(bl_data.processed_coord,start_time,end_time)
                                bl_data.live_location = bl_data.processed_coord[math.floor(bl_data.speed)]
                                #print(bl_data.rev_coord_start_offset,bl_data.rev_coord_end_offset)
                                print(f'{bl_data.bus_name}:{time}:{sec}'," : ",get_speed_per_sec(bl_data.processed_coord,start_time,end_time)," : ",bl_data.processed_coord[math.floor(bl_data.speed)],f'({int(bl_data.speed)}/{len(bl_data.processed_coord)})\n')
                                bl_data.save()
                            except IndexError:
                                print("err")
                                #traceback.print_exc()
                            if(time >= bl_data.stop_change_time_indicator):
                                bl_data.prev_stop_index+=1
                                bl_data.stop_index+=1
                                bl_data.speed = 0
                                bl_data.rev_coord_start_offset = bl_data.rev_coord_end_offset
                                bl_data.current_stop = bl_data.next_stop
                                try:
                                    bl_data.next_stop = list(wu_check.loaded_timetable.keys())[bl_data.stop_index+1]
                                    stop_key = list(wu_check.loaded_timetable.keys())[bl_data.prev_stop_index+1]
                                    bl_data.stop_change_time_indicator = wu_check.loaded_timetable[stop_key]
                                    bl_data.save()
                                except IndexError:
                                    bl_data.state="inactive"
                                    print(bl_data.bus_name," is inactive")
                                    bl_data.save()
                                    continue
                                #print(bl_data.rev_coord_start_offset,bl_data.rev_coord_end_offset)
                               # print(curr_bus.bus_name)
                                #print(curr_bus_route_coords)

                

        except KeyboardInterrupt:
            clock.stop()
        except Exception as e:
            clock.stop()
            traceback.print_exc()