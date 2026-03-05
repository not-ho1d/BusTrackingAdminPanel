from django.core.management.base import BaseCommand
from django.core.cache import cache
from AdminPanel.models import Bus,WorkerUpdates,Routes,RouteCoords,BusLocation
import time
import json
import math
import threading
from datetime import datetime

from datetime import datetime

def get_speed_per_sec(coords, start_time, end_time):
    start = datetime.strptime(start_time, "%H:%M")
    end = datetime.strptime(end_time, "%H:%M")

    total_seconds = (end - start).total_seconds()
    total_indices = len(coords) - 1

    return total_indices / total_seconds

def addOne(num):
    num=int(num)
    if(num<9):
        return f'0{num+1}'
    else:
        return num+1

def getTimeTable(bus_name,time):
    b = Bus.objects.get(bus_name=bus_name)
    wu = WorkerUpdates.objects.get(bus_name=bus_name)
    wu.route_name = b.route_name
    wu.loaded_timetable = b.timetable[time]
    print("route: ",wu.route_name,"\n",wu.loaded_timetable)
    wu.save()

class Time:
    def __init__(self):
        self.hrs = "06"
        self.min = "57"
        self.sec = "00"
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
        clock = Time()
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
            while True:
                prev_time = time
                time = f'{clock.hrs}:{clock.min}'
                if(time in tt_data and (prev_time!=time)):
                    for bus in tt_data[time]:
                        try:
                            wu = WorkerUpdates.objects.get(bus_name = bus)
                            if(wu.returning):
                                wu.returning = False
                                print(f'{bus} is taking off : {time}')
                                if bus not in buses_on_run:
                                    buses_on_run.append(bus)
                            else:
                                wu.returning = True
                                print(f'{bus} is returning : {time}')
                                if bus not in buses_on_run:
                                    buses_on_run.append(bus)
                            wu.save()
                            getTimeTable(bus,time)
                        except WorkerUpdates.DoesNotExist:
                            print(f'{bus} is taking off : {time}')
                            if bus not in buses_on_run:
                                    buses_on_run.append(bus)
                            wu = WorkerUpdates(
                                bus_name = bus,
                                returning = False
                            )  
                            wu.save()
                            getTimeTable(bus,time)
                for bus in buses_on_run:
                    #print(bus)
                    bus = Bus.objects.get(bus_name = bus)
                    #print(bus.route_name)
                    rc = Routes.objects.get(route_name = bus.route_name)
                    wu = WorkerUpdates.objects.get(bus_name = bus.bus_name)
                    tt_keys = list(wu.loaded_timetable.keys())
                    for i,k in enumerate(tt_keys):
                        if(i<len(tt_keys)-1):
                            #print(len(tt_keys),wu.loaded_timetable[k],wu.loaded_timetable[tt_keys[i+1]])
                            if(wu.loaded_timetable[k]<time<wu.loaded_timetable[tt_keys[i+1]]):
                                #print("inb: ",wu.loaded_timetable[k],wu.loaded_timetable[tt_keys[i+1]])
                                #print("rc",rc.stop_to_stop_coords[i]["coords"][0])
                                try:
                                    bl = BusLocation.objects.get(bus_name = bus.bus_name)
                                    bl.speed+=speed
                                    bl.current_stop = wu.loaded_timetable[k]
                                    bl.next_stop = wu.loaded_timetable[tt_keys[i+1]]
                                    if(math.floor(speed)<len(rc.stop_to_stop_coords[i]["coords"])-1):
                                        bl.live_location = rc.stop_to_stop_coords[i]["coords"][math.floor(bl.speed)]
                                    else:
                                        print("length finished")
                                    
                                    bl.save()
                                    print("live_location",bl.live_location)
                                
                                except BusLocation.DoesNotExist:
                                    bl = BusLocation(
                                        bus_name = bus.bus_name,
                                        route_name = bus.route_name,
                                        current_stop = wu.loaded_timetable[k],
                                        next_stop = wu.loaded_timetable[tt_keys[i+1]],
                                        live_location=rc.stop_to_stop_coords[i]["coords"][0]
                                    )
                                    speed = get_speed_per_sec(coords=rc.stop_to_stop_coords[i]["coords"],start_time=wu.loaded_timetable[k],end_time=wu.loaded_timetable[tt_keys[i+1]])
                                    bl.speed = speed
                                    bl.save()
                                    print("saved")
                                    

                

        except KeyboardInterrupt:
            clock.stop()
        except Exception as e:
            clock.stop()
            print(e)