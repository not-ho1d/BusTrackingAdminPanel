from django.core.management.base import BaseCommand
from django.core.cache import cache
from AdminPanel.models import Bus,WorkerUpdates
import time
import threading

def addOne(num):
    num=int(num)
    if(num<9):
        return f'0{num+1}'
    else:
        return num+1

def getTimeTable(bus_name,time):
    b = Bus.objects.get(bus_name=bus_name)
    wu = WorkerUpdates.objects.get(bus_name=bus_name)
    wu.loaded_timetable = b.timetable[time]
    print(wu.loaded_timetable)
    wu.save()

class Time:
    def __init__(self):
        self.hrs = "08"
        self.min = "10"
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
                #cache.set("time",f'{self.hrs}:{self.min}:{self.sec}')
                #print("cached")
                if(int(self.min)>59):
                    self.min="00"
                    self.hrs=addOne(self.hrs)
                    if(int(self.hrs)>24):
                        self.hrs="01"
            #print(self.hrs,":",self.min,":",self.sec)
            time.sleep(clockUpdateTime)
    def stop(self):
        self.running = False

class Command(BaseCommand):
    def handle(self,*args, **kwargs):
        clockUpdateTime = 0.00001
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
        wu = WorkerUpdates.objects.all()
        wu.delete()
        
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
                            else:
                                wu.returning = True
                                print(f'{bus} is returning : {time}')
                            wu.save()
                            getTimeTable(bus,time)
                        except WorkerUpdates.DoesNotExist:
                            print(f'{bus} is taking off : {time}')
                            wu = WorkerUpdates(
                                bus_name = bus,
                                returning = False
                            )  
                            wu.save()
                            getTimeTable(bus,time)

        except KeyboardInterrupt:
            clock.stop()
        except Exception as e:
            clock.stop()
            print(e)