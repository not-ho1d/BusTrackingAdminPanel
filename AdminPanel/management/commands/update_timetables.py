from AdminPanel.models import Bus
from django.core.management.base import BaseCommand
import statistics
import random
import copy

def to_minutes(t):
    h, m = map(int, t.split(":"))
    return h * 60 + m

def to_time(m):
    return f"{m//60:02d}:{m%60:02d}"

def get_median_timetable(timetables):
    merged = {}

    if not timetables:
        return merged

    base = timetables[0]

    for trip, stops in base.items():
        merged[trip] = {}

        for stop in stops:
            times = []

            for table in timetables:
                try:
                    times.append(to_minutes(table[trip][stop]))
                except KeyError:
                    continue

            # Only calculate if enough responses
            if len(times) >= 5:
                mean = sum(times) / len(times)
                times = [t for t in times if abs(t - mean) <= 10]

                if times:
                    median_time = int(statistics.median(times))
                    merged[trip][stop] = to_time(median_time)

    return merged

def to_minutes(t):
    h, m = map(int, t.split(":"))
    return h * 60 + m

def to_time(m):
    return f"{m//60:02d}:{m%60:02d}"


def generate_random_feedback(base_timetable, n=5):
    feedback_list = []

    for _ in range(n):
        new_table = copy.deepcopy(base_timetable)

        for trip in new_table:
            for stop in new_table[trip]:
                original_time = new_table[trip][stop]
                minutes = to_minutes(original_time)

                # random delay between -5 to +5 minutes
                delay = random.randint(-5, 5)

                new_minutes = minutes + delay
                new_table[trip][stop] = to_time(new_minutes)

        feedback_list.append(new_table)

    return feedback_list
def fix_timetable_order(timetable):
    for trip in timetable:
        stops = list(timetable[trip].keys())

        prev_time = None

        for stop in stops:
            current = to_minutes(timetable[trip][stop])

            if prev_time is not None and current < prev_time:
                # fix by pushing forward
                current = prev_time + 1

            timetable[trip][stop] = to_time(current)
            prev_time = current

    return timetable
class Command(BaseCommand):
    def handle(self,*args, **kwargs):
        buses  = Bus.objects.all()
        for b in buses:
            base = b.timetable
            feedback_tables = b.feedback_timetables
            if(len(feedback_tables)>3):
                median_table = get_median_timetable([base] + feedback_tables)

                median_table = fix_timetable_order(median_table)
                b.timetable = median_table
                b.feedback_timetables = []
                b.save()
                print(b.timetable)
